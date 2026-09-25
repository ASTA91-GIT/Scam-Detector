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
    Validates ownership to enforce strict user authorization.
    """
    if not case_id or case_id == "global":
        return {
            "case_id": "global",
            "is_global": True,
            "company": {"name": "No Specific Company", "website": "", "email": "", "phone": ""},
            "job": {"title": "General Security Query", "location": ""},
            "risk_score": 0,
            "risk_level": "N/A",
            "trust_score": 100,
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

    trust_score = analysis.get("trust_score", 50)
    risk_score = 100 - trust_score
    risk_level = analysis.get("risk_level", "Suspicious")
    company_name = analysis.get("company_name", "Not Specified")
    job_title = analysis.get("job_title", "Job Offer")
    company_email = analysis.get("company_email", "") or ""
    company_website = analysis.get("company_website", "") or ""
    company_phone = analysis.get("company_phone", "") or ""
    job_location = analysis.get("job_location", "") or ""

    structured_flags = analysis.get("structured_red_flags", [])
    if not structured_flags:
        # Fallback to plain red_flags list if legacy record
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
        f"Assessed Risk Level: {risk_level} ({risk_score}/100 Risk Score, {trust_score}/100 Trust Score)",
    ]
    if company_email:
        facts.append(f"Recruiter Email: {company_email}")
    if company_website:
        facts.append(f"Company Website: {company_website}")
    if company_phone:
        facts.append(f"Recruiter Phone: {company_phone}")
    if job_location:
        facts.append(f"Job Location: {job_location}")

    for flag in structured_flags:
        facts.append(f"Detected Flag [{flag.get('severity', 'MEDIUM')}]: {flag.get('title')} — {flag.get('description', '')}")

    raw_text = analysis.get("text", "") or ""
    # Cap document text at 3000 chars to avoid buffer bloat while keeping full substance
    doc_snippet = raw_text[:3000]

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
        "risk_level": risk_level,
        "trust_score": trust_score,
        "red_flags": structured_flags,
        "breakdown": analysis.get("risk_breakdown", {}),
        "document_text": doc_snippet,
        "important_facts": facts,
        "created_at": analysis.get("created_at")
    }


def retrieve_relevant_evidence(query: str, case_context: Dict[str, Any]) -> List[str]:
    """
    RAG Retrieval: Extracts top relevant text snippets or red flags
    matching the user's specific question.
    """
    if case_context.get("is_global"):
        return []

    query_terms = set(query.lower().split())
    evidence_hits = []

    # 1. Search structured red flags
    for flag in case_context.get("red_flags", []):
        flag_text = f"{flag.get('title', '')} {flag.get('description', '')} {flag.get('evidence', '')}".lower()
        if any(term in flag_text for term in query_terms if len(term) > 3):
            evidence_hits.append(f"[{flag.get('severity')}] {flag.get('title')}: {flag.get('evidence') or flag.get('description')}")

    # 2. Search document paragraphs
    doc_text = case_context.get("document_text", "")
    paragraphs = [p.strip() for p in doc_text.split("\n") if len(p.strip()) > 20]
    for p in paragraphs:
        p_lower = p.lower()
        matches = sum(1 for term in query_terms if term in p_lower and len(term) > 3)
        if matches >= 2 or any(k in p_lower for k in ["fee", "payment", "bank", "telegram", "whatsapp", "deposit"]):
            evidence_hits.append(f"Document excerpt: \"{p[:200]}...\"")
            if len(evidence_hits) >= 4:
                break

    return evidence_hits[:5]
