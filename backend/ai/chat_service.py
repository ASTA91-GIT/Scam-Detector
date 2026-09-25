"""
CaseAI Chat Service Orchestrator
Coordinates case context, memory management, provider resolution,
streaming SSE responses, and special investigation actions.
"""
from typing import Generator, Dict, Any
from backend.ai.case_context import get_case_context, retrieve_relevant_evidence
from backend.ai.memory import CaseMemoryManager
from backend.ai.prompts import build_case_system_prompt
from backend.ai.provider_factory import get_provider, get_ai_status

ACTION_PROMPTS = {
    "explain": "Explain this case in simple, accessible language. What is this job, what are the primary concerns, and what should a non-technical candidate understand?",
    "investigate": "Conduct a detailed forensic consistency check on this case. Analyze the company, recruiter email, website, and job requirements for logical inconsistencies, domain mismatches, or suspicious timing patterns.",
    "checklist": "Generate an actionable, step-by-step verification checklist tailored to this specific employer and job offer. What 5 to 7 concrete things should I verify before proceeding?",
    "recruiter_questions": "Generate 4 to 5 strategic, professional questions I can ask this recruiter to test their legitimacy without sounding confrontational. Include what specific answers to watch out for.",
    "summary": "Generate an executive Case Investigation Summary for this case. Include Company, Role, Risk Score, Primary Threat Signals, and Final Forensic Verdict."
}

class CaseAIChatService:
    """High-level service orchestrating CaseAI interactions"""

    @classmethod
    def get_case_context_data(cls, case_id: str, user_id: str) -> Dict[str, Any]:
        """Fetch sanitized case context and verify permissions"""
        return get_case_context(case_id, user_id)

    @classmethod
    def get_history(cls, case_id: str, user_id: str) -> Dict[str, Any]:
        """Fetch conversation messages for a case"""
        # Validate case ownership
        get_case_context(case_id, user_id)
        messages = CaseMemoryManager.get_messages(case_id, user_id)
        memory = CaseMemoryManager.get_or_create_memory(case_id, user_id)
        return {
            "case_id": case_id,
            "messages": messages,
            "summary": memory.get("summary", ""),
            "count": len(messages)
        }

    @classmethod
    def clear_history(cls, case_id: str, user_id: str) -> Dict[str, Any]:
        """Clear conversation history for a case"""
        get_case_context(case_id, user_id)
        deleted_count = CaseMemoryManager.clear_messages(case_id, user_id)
        return {
            "success": True,
            "case_id": case_id,
            "deleted_count": deleted_count,
            "message": "Case conversation history reset."
        }

    @classmethod
    def stream_chat(
        cls,
        case_id: str,
        user_id: str,
        user_message: str
    ) -> Generator[str, None, None]:
        """
        Processes user message and yields response chunks.
        Saves user query and complete assistant response into MongoDB.
        """
        if not user_message or not user_message.strip():
            yield "Error: Empty message received."
            return

        user_message = user_message.strip()

        # 1. Fetch & authorize case context
        case_context = get_case_context(case_id, user_id)

        # 2. Save user message to persistent DB
        CaseMemoryManager.save_message(case_id, user_id, "user", user_message)

        # 3. Retrieve relevant evidence fragments (RAG)
        retrieved_evidence = retrieve_relevant_evidence(user_message, case_context)

        # 4. Build case-grounded system prompt
        system_prompt = build_case_system_prompt(case_context, retrieved_evidence)

        # 5. Get compressed history for the model
        compressed_history = CaseMemoryManager.prepare_compressed_history(case_id, user_id, case_context)

        # 6. Resolve active AI Provider
        provider, provider_name = get_provider()

        full_assistant_reply = []

        try:
            for chunk in provider.stream(compressed_history, system_prompt=system_prompt):
                full_assistant_reply.append(chunk)
                yield chunk
        except Exception as e:
            err_msg = f"\n[CaseAI Notice: Stream interrupted ({str(e)}). Switching to local forensic response.]\n"
            yield err_msg
            full_assistant_reply.append(err_msg)

        # 7. Persist complete assistant response in MongoDB
        final_text = "".join(full_assistant_reply).strip()
        if final_text:
            CaseMemoryManager.save_message(case_id, user_id, "assistant", final_text)

    @classmethod
    def chat_sync(
        cls,
        case_id: str,
        user_id: str,
        user_message: str
    ) -> Dict[str, Any]:
        """Synchronous chat endpoint"""
        chunks = []
        for chunk in cls.stream_chat(case_id, user_id, user_message):
            chunks.append(chunk)
        reply = "".join(chunks)
        provider, provider_name = get_provider()
        return {
            "case_id": case_id,
            "reply": reply,
            "provider": provider_name
        }

    @classmethod
    def execute_special_action(
        cls,
        case_id: str,
        user_id: str,
        action_name: str
    ) -> Generator[str, None, None]:
        """Dispatches predefined one-click investigation actions"""
        prompt = ACTION_PROMPTS.get(action_name)
        if not prompt:
            yield f"Error: Unknown action '{action_name}'. Available: {list(ACTION_PROMPTS.keys())}"
            return

        for chunk in cls.stream_chat(case_id, user_id, prompt):
            yield chunk

    @classmethod
    def export_chat(
        cls,
        case_id: str,
        user_id: str,
        export_format: str = "txt"
    ) -> Dict[str, Any]:
        """Export case conversation as structured text or JSON"""
        case_context = get_case_context(case_id, user_id)
        messages = CaseMemoryManager.get_messages(case_id, user_id)

        if export_format == "json":
            return {
                "metadata": {
                    "case_id": case_id,
                    "company": case_context.get("company", {}).get("name"),
                    "job_title": case_context.get("job", {}).get("title"),
                    "risk_assessment": f"{case_context.get('risk_level')} ({case_context.get('risk_score')}/100)",
                    "exported_at": str(case_context.get("created_at")),
                    "disclaimer": "CaseAI provides AI-assisted analysis based on available case information. It may make mistakes and does not independently establish whether an offer is fraudulent."
                },
                "messages": messages
            }

        # Text transcript
        lines = [
            "=" * 60,
            "SENTINELSCAN AI — CASE INVESTIGATION TRANSCRIPT",
            "=" * 60,
            f"Case ID: {case_id}",
            f"Target Employer: {case_context.get('company', {}).get('name')}",
            f"Position: {case_context.get('job', {}).get('title')}",
            f"Risk Rating: {case_context.get('risk_level')} (Risk Score: {case_context.get('risk_score')}/100)",
            "=" * 60,
            ""
        ]

        for m in messages:
            sender = "ANALYSIS USER" if m["role"] == "user" else "CASEAI ASSISTANT"
            lines.append(f"[{m.get('created_at', '')}] {sender}:")
            lines.append(m.get("content", ""))
            lines.append("-" * 40)

        lines.extend([
            "",
            "=" * 60,
            "DISCLAIMER: CaseAI provides AI-assisted analysis based on available case information.",
            "It does not independently establish whether an offer is fraudulent.",
            "=" * 60
        ])

        return {
            "format": "txt",
            "content": "\n".join(lines),
            "filename": f"CaseAI_Investigation_{case_id[:8]}.txt"
        }
