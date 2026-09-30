"""
Company & Forensic Entity Extraction Engine
Extracts rich structured entities from documents and metadata:
- company_name (with null if unidentifiable, never fake names)
- company_aliases
- job_title
- department
- recruiter_name
- recruiter_email
- recruiter_phone
- company_address
- company_website
- company_domain
- salary
- location
- application_url
- social_links

Each entity strictly adheres to:
{
    "value": ...,
    "confidence": 0.0 - 1.0,
    "source": "document" | "metadata" | "inferred",
    "evidence": "verbatim citation"
}
"""

import re
from typing import Dict, Any, List, Optional, Tuple
from urllib.parse import urlparse

from backend.company_intelligence.schemas import create_entity_field
from backend.company_intelligence.email import FREE_EMAIL_PROVIDERS, normalize_domain

# Common corporate suffixes
CORPORATE_SUFFIXES = (
    r'\b(?:Inc\.?|Incorporated|LLC|L\.L\.C\.|Corp\.?|Corporation|Ltd\.?|Limited|'
    r'Pvt\.?\s*Ltd\.?|Private\s+Limited|LLP|GmbH|B\.V\.|S\.A\.|Technologies|'
    r'Solutions|Software|Enterprises|Holdings|Group|Systems|Networks|Labs|Services|Consulting)\b'
)


def clean_ocr_text(text: str) -> str:
    """Fixes broken OCR words across newlines and hyphenation."""
    if not text:
        return ""
    # Merge hyphenated line breaks (e.g. "Techno-\nlogies" -> "Technologies")
    cleaned = re.sub(r'(\w+)-\s*\n\s*(\w+)', r'\1\2', text)
    # Normalize multiple whitespace characters
    cleaned = re.sub(r'[ \t]+', ' ', cleaned)
    return cleaned


def extract_domain_from_url(url: str) -> Optional[str]:
    """Extracts base registered hostname from URL."""
    if not url:
        return None
    u = url.strip()
    if not u.startswith(("http://", "https://")):
        u = f"https://{u}"
    try:
        parsed = urlparse(u)
        host = (parsed.hostname or "").lower()
        if host.startswith("www."):
            host = host[4:]
        return host if "." in host else None
    except Exception:
        return None


def extract_company_candidates(text: str,
                               metadata: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Extracts potential company candidates from multiple signals:
    - User metadata
    - Header lines (first 5 lines)
    - Formal corporate patterns with suffixes
    - "Offer letter" / "Employment offer" / "Issued by" phrases
    - Signatures ("Sincerely", "For and on behalf of", "Authorized HR")
    - Email domain heuristic
    """
    candidates: List[Dict[str, Any]] = []
    meta = metadata or {}
    cleaned = clean_ocr_text(text or "")
    lines = [l.strip() for l in cleaned.splitlines() if l.strip()]

    # Signal 1: Metadata input if valid
    meta_comp = (meta.get("company_name") or "").strip()
    if meta_comp and meta_comp.lower() not in ("unspecified organization", "not specified", "unknown", "none", "company not identified"):
        candidates.append({
            "name": meta_comp,
            "confidence": 0.95,
            "source": "metadata",
            "evidence": f"Candidate metadata: '{meta_comp}'",
            "reason": "Explicit user input"
        })

    # Signal 2: Explicit prefix patterns (e.g. "Company: Acme Corp", "Employer: Acme Corp")
    prefix_pattern = re.compile(
        r'(?:company|organization|employer|organization name|issued by|institution|entity):\s*([^\n\r,;.]{3,60})',
        re.IGNORECASE
    )
    for m in prefix_pattern.finditer(cleaned):
        name = m.group(1).strip()
        if len(name) >= 3 and not name.lower().startswith("not specified"):
            candidates.append({
                "name": name,
                "confidence": 0.90,
                "source": "document",
                "evidence": m.group(0).strip(),
                "reason": "Direct document entity label"
            })

    # Signal 3: Header / Letterhead OCR (first 5 lines)
    for i, line in enumerate(lines[:5]):
        low = line.lower()
        if any(w in low for w in ["opportunity", "work from home", "earn", "daily", "urgent", "congratulations", "apply now", "offer", "letter", "employment", "confidential", "date", "dear", "candidate", "page", "invoice", "contract", "notice", "alert", "welcome"]):
            continue
        # Corporate suffix in header line
        if re.search(CORPORATE_SUFFIXES, line, re.I) and len(line) <= 60:
            candidates.append({
                "name": line,
                "confidence": 0.88,
                "source": "document",
                "evidence": f"Header line {i+1}: '{line}'",
                "reason": "Header letterhead corporate entity"
            })
        elif len(line) >= 3 and len(line) <= 45 and line.isupper() and not any(c in line for c in ["@", "$", "€", "₹", "!", "?", "HTTP"]):
            candidates.append({
                "name": line.title(),
                "confidence": 0.70,
                "source": "document",
                "evidence": f"Uppercase header: '{line}'",
                "reason": "Header organizational title"
            })

    # Signal 4: "Offer of Employment with [Company]" or "Join [Company]" or "Welcome to [Company]"
    offer_with_pattern = re.compile(
        r'(?:offer(?:\s+of\s+employment)?\s+(?:with|at|from)|welcome\s+to|pleased\s+to\s+offer\s+you\s+(?:an?\s+)?(?:position|role|employment)\s+at)\s+([A-Z][A-Za-z0-9\s&.,-]{2,50}?(?:' + CORPORATE_SUFFIXES + r'|[A-Z][a-z]+))',
        re.IGNORECASE
    )
    for m in offer_with_pattern.finditer(cleaned):
        cand_name = m.group(1).strip()
        # Clean trailing punctuation
        cand_name = re.sub(r'[,;.]$', '', cand_name).strip()
        if len(cand_name) >= 3:
            candidates.append({
                "name": cand_name,
                "confidence": 0.89,
                "source": "document",
                "evidence": m.group(0).strip(),
                "reason": "Formal offer statement phrasing"
            })

    # Signal 5: Signature block ("For and on behalf of [Company]", "Authorized Signatory - [Company]")
    sig_pattern = re.compile(
        r'(?:for\s+and\s+on\s+behalf\s+of|on\s+behalf\s+of|authorized\s+signatory\s*[,-]?\s*)\s*([A-Z][A-Za-z0-9\s&.,-]{2,50}?(?:' + CORPORATE_SUFFIXES + r'|[A-Z][a-z]+))',
        re.IGNORECASE
    )
    for m in sig_pattern.finditer(cleaned):
        cand_name = re.sub(r'[,;.]$', '', m.group(1).strip()).strip()
        if len(cand_name) >= 3:
            candidates.append({
                "name": cand_name,
                "confidence": 0.85,
                "source": "document",
                "evidence": m.group(0).strip(),
                "reason": "Authorized signature block statement"
            })

    # Signal 6: General corporate regex anywhere in text
    corp_regex = re.compile(
        r'\b([A-Z][A-Za-z0-9\s&.,-]{1,40}?' + CORPORATE_SUFFIXES + r')',
        re.MULTILINE
    )
    for m in corp_regex.finditer(cleaned):
        cand_name = m.group(1).strip()
        # Exclude common false positives
        if not re.search(r'\b(?:Dear|Sincerely|Regards|Thank|Hello|Hi)\b', cand_name):
            candidates.append({
                "name": cand_name,
                "confidence": 0.82,
                "source": "document",
                "evidence": m.group(0).strip(),
                "reason": "Standard legal entity corporate nomenclature"
            })

    # Signal 7: Email address domain heuristic (if no candidate yet or corporate email)
    email_match = re.search(r'\b[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b', cleaned)
    if email_match:
        dom = email_match.group(1).lower()
        if dom not in FREE_EMAIL_PROVIDERS:
            # derive company name from domain label (e.g. exampletechnologies.com -> Example Technologies)
            label = dom.split('.')[0]
            # split camelCase or hyphens
            derived_name = re.sub(r'[-_]', ' ', label).title()
            candidates.append({
                "name": derived_name,
                "confidence": 0.65,
                "source": "inferred",
                "evidence": f"Recruiter email: {email_match.group(0)}",
                "reason": "Derived from corporate email domain"
            })

    return candidates


def resolve_company(candidates: List[Dict[str, Any]]) -> Tuple[Optional[str], float, str, str, List[Dict[str, Any]]]:
    """
    Resolves the most likely company from candidate signals.
    Returns:
    (resolved_name, confidence, source, evidence, possible_matches)
    """
    if not candidates:
        return None, 0.0, "document", "", []

    # Deduplicate candidates by normalized name
    seen = {}
    unique_candidates = []
    for c in candidates:
        norm = re.sub(r'[^a-zA-Z0-9]', '', c["name"].lower())
        if not norm or len(norm) < 3:
            continue
        if norm not in seen:
            seen[norm] = c
            unique_candidates.append(c)
        else:
            # Keep higher confidence
            if c["confidence"] > seen[norm]["confidence"]:
                unique_candidates.remove(seen[norm])
                seen[norm] = c
                unique_candidates.append(c)

    # Sort descending by confidence
    unique_candidates.sort(key=lambda x: x["confidence"], reverse=True)

    if not unique_candidates:
        return None, 0.0, "document", "", []

    best = unique_candidates[0]

    # Check for multiple strong matches
    possible_matches = []
    if len(unique_candidates) > 1:
        for c in unique_candidates[:4]:
            possible_matches.append({
                "company_name": c["name"],
                "confidence": c["confidence"],
                "match_reason": c.get("reason", "Detected candidate entity")
            })

    # If confidence is below threshold, return None
    if best["confidence"] < 0.60:
        return None, 0.0, "document", "", possible_matches

    return best["name"], best["confidence"], best["source"], best.get("evidence", ""), possible_matches


def discover_official_domain(text: str,
                             company_name: Optional[str] = None,
                             recruiter_email: Optional[str] = None,
                             metadata: Optional[Dict[str, Any]] = None) -> Tuple[Optional[str], str, float]:
    """
    Discovers the company's official domain according to priority:
    1. Explicit website in metadata or document
    2. Recruiter corporate email domain
    3. URL inside document
    4. Derived from company name
    Returns: (domain, source, confidence)
    """
    meta = metadata or {}
    cleaned = clean_ocr_text(text or "")

    # Priority 1: Metadata website
    meta_web = (meta.get("company_website") or "").strip()
    if meta_web:
        dom = extract_domain_from_url(meta_web)
        if dom and dom not in FREE_EMAIL_PROVIDERS:
            return dom, "metadata_website", 0.95

    # Priority 2: Explicit website URL inside document
    web_match = re.search(r'\b(?:https?:\/\/)?(?:www\.)?([a-zA-Z0-9][a-zA-Z0-9-]{1,61}[a-zA-Z0-9]\.(?:com|org|net|in|co|io|ai|biz|info|tech|dev|app|global|agency))\b', cleaned, re.I)
    if web_match:
        dom = web_match.group(1).lower()
        if dom not in FREE_EMAIL_PROVIDERS:
            return dom, "document_website", 0.90

    # Priority 3: Recruiter corporate email domain
    email_cand = recruiter_email or meta.get("company_email")
    if not email_cand:
        e_match = re.search(r'\b[A-Za-z0-9._%+-]+@([A-Za-z0-9.-]+\.[A-Z|a-z]{2,})\b', cleaned)
        if e_match:
            email_cand = e_match.group(0)

    if email_cand and "@" in email_cand:
        email_dom = email_cand.split("@")[-1].lower().strip()
        if email_dom not in FREE_EMAIL_PROVIDERS:
            return email_dom, "email_domain", 0.85

    # Priority 4: Fallback heuristic from company name if confident
    if company_name and len(company_name) > 3:
        clean_slug = re.sub(r'[^a-zA-Z0-9]', '', company_name).lower()
        if len(clean_slug) >= 4 and len(clean_slug) <= 25:
            return f"{clean_slug}.com", "inferred_name", 0.50

    return None, "unavailable", 0.0


def extract_company_entities(text: str,
                             metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Primary extraction entry point. Produces the complete standardized entity bundle:
    company_name, company_aliases, job_title, department, recruiter_name,
    recruiter_email, recruiter_phone, company_address, company_website,
    company_domain, salary, location, application_url, social_links.
    """
    meta = metadata or {}
    cleaned = clean_ocr_text(text or "")

    # 1. Company Name Identification
    candidates = extract_company_candidates(cleaned, meta)
    resolved_comp, comp_conf, comp_src, comp_ev, possible_matches = resolve_company(candidates)

    # 2. Recruiter Email
    email_val = (meta.get("company_email") or "").strip()
    email_src = "metadata" if email_val else "document"
    email_ev = ""
    if not email_val:
        m = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', cleaned)
        if m:
            email_val = m.group(0)
            email_ev = m.group(0)

    # 3. Domain Discovery
    domain, dom_src, dom_conf = discover_official_domain(
        cleaned,
        company_name=resolved_comp,
        recruiter_email=email_val,
        metadata=meta
    )

    # 4. Job Title
    role_val = (meta.get("job_title") or "").strip()
    role_src = "metadata" if role_val else "document"
    role_ev = ""
    role_conf = 0.95 if role_val else 0.80
    if not role_val:
        rm = re.search(r'(?:job title|position|role|designation|appointment as):\s*([^\n\r,;.]{3,50})|(?:position|role)\s+of\s+([A-Z][a-zA-Z\s]{3,50})', cleaned, re.I)
        if rm:
            raw_role = (rm.group(1) or rm.group(2)).strip()
            role_val = re.sub(r'\s+(?:at|in|with)\s+.*$', '', raw_role, flags=re.I).strip()
            role_ev = rm.group(0)
            role_conf = 0.88
        else:
            role_val = "Job Offer"
            role_conf = 0.50

    # 5. Department
    dept_val = None
    dept_ev = ""
    dm = re.search(r'(?:department|division|team|unit):\s*([^\n\r,;.]{2,40})', cleaned, re.I)
    if dm:
        dept_val = dm.group(1).strip()
        dept_ev = dm.group(0)

    # 6. Recruiter Name
    rec_val = None
    rec_ev = ""
    rec_conf = 0.0
    rec_match = re.search(r'(?:recruiter|hr manager|hiring manager|talent acquisition|authorized by|signatory):\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})', cleaned, re.I)
    if rec_match:
        rec_val = rec_match.group(1).strip()
        rec_ev = rec_match.group(0)
        rec_conf = 0.88
    else:
        # Check signature line
        sig_match = re.search(r'(?:Sincerely|Regards|Warm regards|Best regards|Authorized Signature)[\s\r\n]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,2})', cleaned)
        if sig_match:
            rec_val = sig_match.group(1).strip()
            rec_ev = sig_match.group(0)
            rec_conf = 0.75

    # 7. Recruiter Phone
    phone_val = (meta.get("company_phone") or "").strip()
    phone_src = "metadata" if phone_val else "document"
    phone_ev = ""
    if not phone_val:
        pm = re.search(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3,5}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\+91[\s-]?\d{10}', cleaned)
        if pm:
            phone_val = pm.group(0).strip()
            phone_ev = pm.group(0)

    # 8. Salary / Compensation
    sal_val = None
    sal_ev = ""
    sm = re.search(r'(?:salary|compensation|stipend|ctc|package|remuneration):\s*([^\n\r,;.]{3,40})', cleaned, re.I)
    if sm:
        sal_val = sm.group(1).strip()
        sal_ev = sm.group(0)
    else:
        num_sal = re.search(r'(?:₹|\$|INR|USD|EUR)\s*[\d,]+(?:\s*(?:k|lac|lakh|per\s+(?:annum|year|month)|pa|pm|yr))?', cleaned, re.I)
        if num_sal:
            sal_val = num_sal.group(0).strip()
            sal_ev = num_sal.group(0)

    # 9. Location
    loc_val = (meta.get("job_location") or "").strip()
    loc_src = "metadata" if loc_val else "document"
    loc_ev = ""
    if not loc_val:
        lm = re.search(r'(?:location|address|work location|base|workplace):\s*([^\n\r,;.]{3,50})', cleaned, re.I)
        if lm:
            loc_val = lm.group(1).strip()
            loc_ev = lm.group(0)

    # 10. Application / Portal URL
    app_url = None
    app_ev = ""
    portal_match = re.search(r'(?:portal|apply online|application link|join here|access portal):\s*(https?:\/\/[^\s]+)', cleaned, re.I)
    if portal_match:
        app_url = portal_match.group(1).strip()
        app_ev = portal_match.group(0)

    # 11. Social / Messenger Links
    social_links = []
    for soc in re.finditer(r'(https?:\/\/(?:t\.me|telegram\.me|wa\.me|api\.whatsapp\.com|linkedin\.com)\/[^\s]+)', cleaned, re.I):
        social_links.append(soc.group(1))

    # Assemble structured entity dictionary
    return {
        "company_name": create_entity_field(resolved_comp, comp_conf, comp_src, comp_ev),
        "company_aliases": [m["company_name"] for m in possible_matches if m["company_name"] != resolved_comp],
        "job_title": create_entity_field(role_val, role_conf, role_src, role_ev),
        "department": create_entity_field(dept_val, 0.85 if dept_val else 0.0, "document", dept_ev),
        "recruiter_name": create_entity_field(rec_val, rec_conf, "document", rec_ev),
        "recruiter_email": create_entity_field(email_val, 0.95 if email_val else 0.0, email_src, email_ev),
        "recruiter_phone": create_entity_field(phone_val, 0.90 if phone_val else 0.0, phone_src, phone_ev),
        "company_address": create_entity_field(loc_val, 0.80 if loc_val else 0.0, loc_src, loc_ev),
        "company_website": create_entity_field(f"https://{domain}" if domain else None, dom_conf, dom_src, domain or ""),
        "company_domain": create_entity_field(domain, dom_conf, dom_src, domain or ""),
        "salary": create_entity_field(sal_val, 0.90 if sal_val else 0.0, "document", sal_ev),
        "location": create_entity_field(loc_val, 0.80 if loc_val else 0.0, loc_src, loc_ev),
        "application_url": create_entity_field(app_url, 0.90 if app_url else 0.0, "document", app_ev),
        "social_links": social_links,
        "possible_matches": possible_matches
    }
