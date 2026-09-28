"""
Case Context Builder & RAG Retrieval
Structures MongoDB analysis records into sanitized, case-aware context
for CaseAI, including relevant evidence retrieval.
"""
from typing import Dict, Any, List
from bson import ObjectId
from backend.database import get_analyses_collection

def get_case_context(case_id: str, user_id: str) -> Dict[str, Any]:
    """
    Retrieves and structures the analysis document from MongoDB.
    Validates ownership to enforce strict per-user authorization.
    Injects forensic reasoning, evidence quotes, confidence, and document assessment.
    """
    if not case_id or case_id == "global":
        return {
            "case_id": "global",
            "is_global": True,
            "company": {"name": "No Specific Company", "website": "", "email": "", "phone": ""},
            "job": {"title": "General Security Query", "location": ""},
            "risk_score": 0,
            "confidence": 100,
            "classification": "LOW_RISK",
            "risk_level": "Safe",
            "trust_score": 100,
            "summary": "Operating in general inquiry mode without an active case file.",
            "reasoning": [],
            "positive_signals": [],
            "uncertainties": [],
            "document_assessment": {},
            "recommendations": ["Conduct standard company verification before submitting documents."],
            "red_flags": [],
            "breakdown": {},
            "document_text": "",
            "important_facts": ["Global Assistant Mode: User is querying general recruitment safety."]
        }

    try:
        obj_id = ObjectId(case_id)
    except Exception:
        raise ValueError("Invalid Case ID format.")

    analyses_col = get_analyses_collection()
    analysis = analyses_col.find_one({"_id": obj_id, "user_id": user_id})
    if not analysis:
        raise PermissionError("Case not found or access unauthorized.")

    risk_score = analysis.get("risk_score", 100 - analysis.get("trust_score", 50))
    trust_score = analysis.get("trust_score", max(0, 100 - risk_score))
    confidence = analysis.get("confidence", 85)
    classification = analysis.get("classification", analysis.get("risk_level", "MEDIUM_RISK"))
    risk_level = analysis.get("risk_level", "Suspicious")
    company_name = analysis.get("company_name", "Not Specified")
    job_title = analysis.get("job_title", "Job Offer")
    company_email = analysis.get("company_email", "") or ""
    company_website = analysis.get("company_website", "") or ""
    company_phone = analysis.get("company_phone", "") or ""
    job_location = analysis.get("job_location", "") or ""

    summary = analysis.get("summary") or analysis.get("ai_explanation") or ""
    reasoning = analysis.get("reasoning", [])
    positive_signals = analysis.get("positive_signals", [])
    uncertainties = analysis.get("uncertainties", [])
    document_assessment = analysis.get("document_assessment", {})
    recommendations = analysis.get("recommendations", [])

    structured_flags = analysis.get("structured_red_flags", [])
    if not structured_flags and reasoning:
        for r in reasoning:
            structured_flags.append({
                "title": r.get("finding", "Risk Factor"),
                "severity": r.get("severity", "HIGH"),
                "explanation": r.get("explanation", ""),
                "evidence": r.get("evidence", ""),
                "recommendation": f"Verify independently (Impact: +{r.get('impact_on_score', 0)})"
            })
    elif not structured_flags and analysis.get("red_flags"):
        for f in analysis.get("red_flags", []):
            structured_flags.append({
                "severity": "HIGH" if "fee" in f.lower() or "payment" in f.lower() else "MEDIUM",
                "title": f,
                "description": f,
                "evidence": f,
                "recommendation": "Independently verify before taking action."
            })

    # Build concise important facts list for long-term memory
    facts = [
        f"Company Name: {company_name}",
        f"Job Title: {job_title}",
        f"Assessed Risk Score: {risk_score}/100 (Confidence: {confidence}/100, Classification: {classification})",
        f"Trust Score: {trust_score}/100"
    ]
    if company_email:
        facts.append(f"Recruiter Email: {company_email}")
    if company_website:
        facts.append(f"Company Website: {company_website}")
    if company_phone:
        facts.append(f"Recruiter Phone: {company_phone}")
    if job_location:
        facts.append(f"Job Location: {job_location}")

    for r in reasoning:
        facts.append(f"Forensic Finding [{r.get('severity', 'HIGH')}]: {r.get('finding')} — Evidence: \"{r.get('evidence', '')}\" — {r.get('explanation', '')}")

    raw_text = analysis.get("extracted_text") or analysis.get("text", "") or ""
    doc_snippet = raw_text[:4000]

    return {
        "case_id": str(analysis["_id"]),
        "is_global": False,
        "company": {
            "name": company_name,
            "website": company_website,
            "email": company_email,
            "phone": company_phone
        },
        "job": {
            "title": job_title,
            "location": job_location
        },
        "risk_score": risk_score,
        "confidence": confidence,
        "classification": classification,
        "risk_level": risk_level,
        "trust_score": trust_score,
        "summary": summary,
        "reasoning": reasoning,
        "positive_signals": positive_signals,
        "uncertainties": uncertainties,
        "document_assessment": document_assessment,
        "recommendations": recommendations,
        "red_flags": structured_flags,
        "breakdown": analysis.get("risk_breakdown", {}),
        "document_text": doc_snippet,
        "important_facts": facts,
        "created_at": analysis.get("created_at")
    }


def retrieve_relevant_evidence(query: str, case_context: Dict[str, Any]) -> List[str]:
    """
    RAG Retrieval: Extracts top relevant text snippets, findings, or red flags
    matching the user's specific question.
    """
    if case_context.get("is_global"):
        return []

    query_terms = set(query.lower().split())
    evidence_hits = []

    # 1. Search reasoning findings and evidence quotes
    for r in case_context.get("reasoning", []):
        r_text = f"{r.get('finding', '')} {r.get('explanation', '')} {r.get('evidence', '')}".lower()
        if any(term in r_text for term in query_terms if len(term) > 3) or "why" in query.lower() or "score" in query.lower():
            evidence_hits.append(f"Finding: [{r.get('severity')}] {r.get('finding')} | Evidence: \"{r.get('evidence')}\" | Explanation: {r.get('explanation')}")

    # 2. Search structured red flags
    for flag in case_context.get("red_flags", []):
        flag_text = f"{flag.get('title', '')} {flag.get('description', '')} {flag.get('evidence', '')}".lower()
        if any(term in flag_text for term in query_terms if len(term) > 3):
            evidence_hits.append(f"[{flag.get('severity')}] {flag.get('title')}: \"{flag.get('evidence') or flag.get('description')}\"")

    # 3. Search document paragraphs for cited keywords
    doc_text = case_context.get("document_text", "")
    paragraphs = [p.strip() for p in doc_text.split("\n") if len(p.strip()) > 20]
    for p in paragraphs:
        p_lower = p.lower()
        matches = sum(1 for term in query_terms if term in p_lower and len(term) > 3)
        if matches >= 2 or any(k in p_lower for k in ["fee", "payment", "bank", "telegram", "whatsapp", "deposit", "crypto", "urgent"]):
            evidence_hits.append(f"Document quote: \"{p[:250]}\"")
            if len(evidence_hits) >= 5:
                break

    return evidence_hits[:6]
