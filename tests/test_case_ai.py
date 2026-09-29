"""
CaseAI Integration Test Suite
Validates provider resolution, context building, memory management,
streaming, security/authorization, and export functionality.
"""
from bson import ObjectId
from datetime import datetime
from backend.database import init_db, get_analyses_collection, get_users_collection, get_case_chat_messages_collection
from backend.ai.case_context import get_case_context
from backend.ai.memory import CaseMemoryManager
from backend.ai.chat_service import CaseAIChatService
from backend.ai.provider_factory import get_ai_status

def run_tests():
    print("=" * 60)
    print("RUNNING CASEAI TEST SUITE")
    print("=" * 60)
    init_db()

    # 1. AI Status
    status = get_ai_status()
    assert "active_provider" in status, "Missing active_provider in status"
    print(f"[OK] AI Status Check: active={status['active_provider']}")

    # 2. Setup mock users and case in MongoDB
    users_col = get_users_collection()
    analyses_col = get_analyses_collection()

    test_user_a = "test_user_caseai_a"
    test_user_b = "test_user_caseai_b"

    # Insert mock case
    mock_case = {
        "user_id": test_user_a,
        "company_name": "Apex Global Logistics",
        "job_title": "Remote Data Entry Specialist",
        "company_email": "careers-apex@gmail.com",
        "company_website": "https://apex-careers.biz",
        "company_phone": "+1-800-555-0199",
        "job_location": "Remote (US)",
        "trust_score": 25,
        "risk_level": "High Risk",
        "risk_breakdown": {
            "payment": 10,
            "identity": 30,
            "urgency": 20,
            "grammar": 45,
            "contact": 15,
            "company": 30
        },
        "structured_red_flags": [
            {
                "severity": "CRITICAL",
                "title": "Advance Equipment Fee Demanded",
                "description": "Candidate must remit $250 via Zelle for home office setup hardware.",
                "evidence": "Please transfer $250 registration and security fee for dispatch of MacBook Pro.",
                "recommendation": "Do not send any funds via Zelle or wire transfer."
            },
            {
                "severity": "HIGH",
                "title": "Recruiter Domain Mismatch",
                "description": "Recruiter communicated using free public webmail (@gmail.com).",
                "evidence": "Contact recruiter at careers-apex@gmail.com",
                "recommendation": "Verify recruiter on official company website."
            }
        ],
        "red_flags": [
            "Advance Equipment Fee Demanded",
            "Recruiter Domain Mismatch"
        ],
        "recommendations": [
            "Never transfer funds for equipment.",
            "Verify company through official directory."
        ],
        "text": "Apex Global Logistics is hiring a Remote Data Entry Specialist. Pay is $45/hour. Please transfer $250 registration and security fee for dispatch of MacBook Pro to our official Zelle account.",
        "created_at": datetime.utcnow()
    }

    insert_res = analyses_col.insert_one(mock_case)
    case_id = str(insert_res.inserted_id)
    print(f"[OK] Mock case created: ID={case_id}")

    try:
        # 3. Test Context Builder
        context = get_case_context(case_id, test_user_a)
        assert context["company"]["name"] == "Apex Global Logistics"
        assert context["risk_score"] == 75  # 100 - 25
        assert len(context["red_flags"]) == 2
        print(f"[OK] Case Context generated accurately (Risk Score: {context['risk_score']})")

        # 4. Test Security: User B should be forbidden from accessing User A's case
        try:
            get_case_context(case_id, test_user_b)
            assert False, "Security failure: User B was able to access User A's case!"
        except PermissionError:
            print("[OK] Security Enforcement: Unauthorized user blocked from case context.")

        # 5. Test Case Memory & Message Persistence
        CaseMemoryManager.clear_messages(case_id, test_user_a)
        CaseMemoryManager.save_message(case_id, test_user_a, "user", "Why is this job considered risky?")
        CaseMemoryManager.save_message(case_id, test_user_a, "assistant", "This offer is risky because of the $250 advance fee demanded.")

        history = CaseMemoryManager.get_messages(case_id, test_user_a)
        assert len(history) == 2
        print(f"[OK] Case Memory: Retrieved {len(history)} persistent messages from MongoDB.")

        # 6. Test Streaming Chat Execution
        chunks = []
        for chunk in CaseAIChatService.stream_chat(case_id, test_user_a, "Explain the recruiter email mismatch"):
            chunks.append(chunk)

        full_reply = "".join(chunks)
        assert len(full_reply) > 50
        print(f"[OK] Streaming Chat executed successfully ({len(chunks)} chunks, {len(full_reply)} chars).")

        # Verify assistant response was saved to DB
        updated_history = CaseMemoryManager.get_messages(case_id, test_user_a)
        assert len(updated_history) == 4, f"Expected 4 messages in DB, got {len(updated_history)}"
        print("[OK] User query and assistant response persisted automatically to MongoDB.")

        # 7. Test Special AI Actions
        action_chunks = []
        for chunk in CaseAIChatService.execute_special_action(case_id, test_user_a, "checklist"):
            action_chunks.append(chunk)
        checklist_res = "".join(action_chunks)
        assert len(checklist_res) > 50
        print(f"[OK] Special Action 'checklist' executed successfully.")

        # 8. Test Export Transcript (TXT & JSON)
        txt_export = CaseAIChatService.export_chat(case_id, test_user_a, "txt")
        assert "Apex Global Logistics" in txt_export["content"]
        assert "DISCLAIMER" in txt_export["content"]
        print("[OK] Transcript Export (TXT) generated.")

        json_export = CaseAIChatService.export_chat(case_id, test_user_a, "json")
        assert json_export["metadata"]["company"] == "Apex Global Logistics"
        print("[OK] Transcript Export (JSON) structured correctly.")

        # 9. Test Clear History
        clear_res = CaseAIChatService.clear_history(case_id, test_user_a)
        assert clear_res["deleted_count"] >= 4
        assert len(CaseMemoryManager.get_messages(case_id, test_user_a)) == 0
        print("[OK] Clear conversation history completed.")

        print("=" * 60)
        print("ALL CASEAI INTEGRATION TESTS PASSED (9/9)!")
        print("=" * 60)

    finally:
        # Cleanup mock records
        analyses_col.delete_one({"_id": ObjectId(case_id)})
        get_case_chat_messages_collection().delete_many({"case_id": case_id})
        print("[OK] Test case and artifacts cleaned up cleanly.")

if __name__ == "__main__":
    run_tests()
