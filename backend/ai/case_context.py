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

    # Extract Company Intelligence dossier
    comp_intel = analysis.get("company_intelligence") or {}
    intel_company = comp_intel.get("company") or {}
    intel_domain = comp_intel.get("domain") or {}
    intel_website = comp_intel.get("website") or {}
    intel_email = comp_intel.get("email") or {}
    intel_lookalike = comp_intel.get("lookalike") or comp_intel.get("impersonation") or {}
    intel_comparison = comp_intel.get("comparison") or {}

    # Compile explicit unverified details
    unverified_items = list(uncertainties)
    if not intel_company.get("verified_presence"):
        unverified_items.append("Independent corporate legal registry records for the claimed company could not be confirmed.")
    if not intel_domain.get("creation_date"):
        unverified_items.append("Domain registration creation date and registrar history remain unverified.")
    if intel_email.get("is_free_provider"):
        unverified_items.append("Recruiter individual identity and official corporate authorization cannot be verified via public webmail.")
    elif intel_email.get("match_type") == "MISMATCH":
        unverified_items.append("Recruiter email affiliation with the official corporate domain remains unverified.")

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

    # Inject Company Intelligence Facts
    if intel_domain.get("domain") and intel_domain.get("domain") != "Domain not identified":
        facts.append(f"Official Company Domain: {intel_domain.get('domain')}")
        if intel_domain.get("age_formatted") and intel_domain.get("age_formatted") != "Information unavailable":
            created_str = intel_domain.get("creation_date") or "N/A"
            reg_str = intel_domain.get("registrar") or "N/A"
            lookup_st = intel_domain.get("lookup_status") or "SUCCESS"
            facts.append(f"Domain Registration Date & Age: Created {created_str} ({intel_domain.get('age_formatted')}), Registrar: {reg_str}, Lookup Status: {lookup_st}")
        if intel_domain.get("dns_mx_status") and intel_domain.get("dns_mx_status") != "Information unavailable":
            facts.append(f"DNS / MX Status: {intel_domain.get('dns_mx_status')}")
        if intel_website.get("reachable"):
            facts.append(f"Official Website Status: Reachable (HTTP {intel_website.get('status_code')}, HTTPS: {intel_website.get('https')}, URL: {intel_website.get('final_url')})")

    if intel_email.get("match_type") or intel_email.get("comparison_result"):
        match_state = intel_email.get("comparison_result") or intel_email.get("match_type")
        facts.append(f"Email-Domain Verification Result: {match_state} — {intel_email.get('explanation')}")

    if intel_lookalike.get("detected"):
        facts.append(f"Potential Impersonation Evidence: {intel_lookalike.get('similarity_evidence') or intel_lookalike.get('explanation')} (Target: {intel_lookalike.get('target_domain')})")
    else:
        facts.append("Potential Impersonation Evidence: No lookalike domains, homoglyphs, or brand typosquatting detected for this domain.")

    if intel_company.get("description") and intel_company.get("description") != "Information unavailable":
        facts.append(f"Discovered Company Profile: {intel_company.get('description')[:250]} (Industry: {intel_company.get('industry')}, Founded: {intel_company.get('founded_year') or 'N/A'})")
    elif intel_company.get("identified"):
        facts.append("Discovered Company Profile: Company identified in document, but independent public registry records were unavailable.")

    if unverified_items:
        facts.append("Unverified Details: " + " | ".join(unverified_items[:4]))

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
        "company_intelligence": comp_intel,
        "risk_score": risk_score,
        "confidence": confidence,
        "classification": classification,
        "risk_level": risk_level,
        "trust_score": trust_score,
        "summary": summary,
        "reasoning": reasoning,
        "positive_signals": positive_signals,
        "uncertainties": uncertainties,
        "unverified_details": unverified_items,
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

    q_lower = query.lower()
    query_terms = set(q_lower.split())
    evidence_hits = []

    # 1. Search company intelligence telemetry
    comp_intel = case_context.get("company_intelligence", {})
    intel_comp = comp_intel.get("company", {})
    intel_dom = comp_intel.get("domain", {})
    intel_email = comp_intel.get("email", {})
    intel_web = comp_intel.get("website", {})
    intel_look = comp_intel.get("lookalike", {})

    # Q: When was domain registered / domain age / whois / rdap
    if any(k in q_lower for k in ["register", "creation", "domain age", "when", "whois", "rdap", "registrar"]):
        if intel_dom.get("domain"):
            evidence_hits.append(
                f"Domain Registration: '{intel_dom.get('domain')}' was created on {intel_dom.get('creation_date') or 'Unavailable'} "
                f"(Age: {intel_dom.get('age_formatted', 'Unavailable')}, Registrar: {intel_dom.get('registrar', 'Unavailable')}, Lookup Status: {intel_dom.get('lookup_status', 'SUCCESS')})."
            )

    # Q: Recruiter email match / domain match
    if any(k in q_lower for k in ["match", "email", "recruiter", "domain match", "gmail"]):
        evidence_hits.append(
            f"Recruiter Email Verification: Recruiter '{intel_email.get('email', 'Not disclosed')}' vs Official Domain '{intel_dom.get('domain', 'Unavailable')}' "
            f"Result: {intel_email.get('comparison_result') or intel_email.get('match_type', 'INSUFFICIENT_DATA')}. "
            f"Explanation: {intel_email.get('explanation', '')}"
        )

    # Q: Information found about company
    if any(k in q_lower for k in ["information", "company", "about", "found", "profile", "industry", "founded", "what do we know"]):
        if intel_comp.get("name"):
            evidence_hits.append(
                f"Company Profile: '{intel_comp.get('name')}' — Description: {intel_comp.get('description', 'Information unavailable')[:250]} | "
                f"Industry: {intel_comp.get('industry', 'Information unavailable')} | Location: {intel_comp.get('location', 'Information unavailable')} | "
                f"Founded: {intel_comp.get('founded_year') or 'Information unavailable'} | Website: {intel_comp.get('website', 'Information unavailable')}"
            )
        if intel_web.get("reachable"):
            evidence_hits.append(f"Official Website Probe: Reachable (HTTP {intel_web.get('status_code')}, HTTPS: {intel_web.get('https')}, URL: {intel_web.get('final_url')})")

    # Q: Impersonation / lookalike / spoofing
    if any(k in q_lower for k in ["impersonat", "lookalike", "spoof", "typosquat", "fake brand"]):
        if intel_look.get("detected"):
            evidence_hits.append(f"Impersonation Evidence: DETECTED — {intel_look.get('similarity_evidence') or intel_look.get('explanation')} (Target Brand: {intel_look.get('matched_brand')})")
        else:
            evidence_hits.append("Impersonation Evidence: No lookalike domain anomalies, character substitutions, or typosquatting patterns detected for this domain.")

    # Q: Unverified details / what remains unverified
    if any(k in q_lower for k in ["unverified", "unknown", "missing", "uncertain", "not verified"]):
        unv = case_context.get("unverified_details") or case_context.get("uncertainties") or []
        if unv:
            evidence_hits.append("Unverified Details: " + " | ".join(unv[:4]))
        else:
            evidence_hits.append("Unverified Details: Specific individual recruiter authorization and legal contract registration could not be verified.")

    # Q: Why was document classified as risky / score
    if any(k in q_lower for k in ["why", "risky", "risk", "score", "suspicious", "danger", "classified"]):
        for r in case_context.get("reasoning", []):
            evidence_hits.append(f"Risk Finding [{r.get('severity')}]: {r.get('finding')} | Evidence: \"{r.get('evidence')}\" | Explanation: {r.get('explanation')}")

    # 2. General search on reasoning findings and evidence quotes
    for r in case_context.get("reasoning", []):
        r_text = f"{r.get('finding', '')} {r.get('explanation', '')} {r.get('evidence', '')}".lower()
        if any(term in r_text for term in query_terms if len(term) > 3):
            hit = f"Finding: [{r.get('severity')}] {r.get('finding')} | Evidence: \"{r.get('evidence')}\" | Explanation: {r.get('explanation')}"
            if hit not in evidence_hits:
                evidence_hits.append(hit)

    # 3. Search document paragraphs for cited keywords
    doc_text = case_context.get("document_text", "")
    paragraphs = [p.strip() for p in doc_text.split("\n") if len(p.strip()) > 20]
    for p in paragraphs:
        p_lower = p.lower()
        matches = sum(1 for term in query_terms if term in p_lower and len(term) > 3)
        if matches >= 2 or any(k in p_lower for k in ["fee", "payment", "bank", "telegram", "whatsapp", "deposit", "crypto", "urgent"]):
            quote_hit = f"Document quote: \"{p[:250]}\""
            if quote_hit not in evidence_hits:
                evidence_hits.append(quote_hit)
            if len(evidence_hits) >= 8:
                break

    return evidence_hits[:8]
