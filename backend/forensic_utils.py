"""
Forensic Intelligence Utilities
Provides entity extraction, company/domain intelligence gathering,
and structured AI Opinion construction for the Forensic Investigation Console.
"""

import re
import socket
from urllib.parse import urlparse
from typing import Dict, Any, List, Optional
from datetime import datetime

FREE_EMAIL_DOMAINS = {
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
    'aol.com', 'protonmail.com', 'icloud.com', 'zoho.com',
    'yandex.com', 'mail.com', 'gmx.com'
}

SUSPICIOUS_TLDS = {
    '.top', '.xyz', '.click', '.buzz', '.fit', '.surf', '.work',
    '.rest', '.cam', '.gq', '.ml', '.cf', '.tk', '.ga', '.icu'
}


def extract_entities(text: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, str]:
    """
    Extract key forensic entities from document text and user-provided metadata.
    """
    meta = metadata or {}
    text_clean = text or ""

    # Company
    company = meta.get("company_name") or ""
    if not company or company.lower() in ["not specified", "unknown"]:
        comp_match = re.search(r'(?:company|organization|employer|organization name|issued by|institution):\s*([^\n\r,]+)', text_clean, re.I)
        if comp_match:
            company = comp_match.group(1).strip()
        else:
            # Check for header-like company pattern
            header_match = re.search(r'^[A-Z0-9\s&.,-]{3,40}(?:Inc|LLC|Corp|Ltd|Technologies|Solutions|Enterprises|Pvt|Private Limited)\b', text_clean, re.M)
            company = header_match.group(0).strip() if header_match else "Unspecified Organization"

    # Role / Title
    role = meta.get("job_title") or ""
    if not role or role.lower() in ["job offer", "document"]:
        role_match = re.search(r'(?:job title|position|role|designation|awarded for|certificate in|certificate of):\s*([^\n\r,]+)', text_clean, re.I)
        if role_match:
            role = role_match.group(1).strip()
        else:
            role = "General Document / Offer"

    # Recruiter / Signatory
    recruiter = ""
    rec_match = re.search(r'(?:recruiter|hr manager|hiring manager|talent acquisition|signatory|authorized by|instructor):\s*([^\n\r,]+)', text_clean, re.I)
    if rec_match:
        recruiter = rec_match.group(1).strip()
    else:
        # Check signature block
        sig_match = re.search(r'(?:Sincerely|Regards|Best regards|Authorized Signature)[\s\r\n]+([A-Z][a-z]+ [A-Z][a-z]+)', text_clean)
        recruiter = sig_match.group(1).strip() if sig_match else "Not Specified"

    # Email
    email = meta.get("company_email") or ""
    if not email:
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text_clean)
        email = email_match.group(0).strip() if email_match else ""

    # Phone
    phone = meta.get("company_phone") or ""
    if not phone:
        phone_match = re.search(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3,5}\)?[-.\s]?\d{3}[-.\s]?\d{4}|\+91[\s-]?\d{10}', text_clean)
        phone = phone_match.group(0).strip() if phone_match else ""

    # Salary / Compensation
    salary = ""
    sal_match = re.search(r'(?:salary|compensation|stipend|ctc|package|remuneration):\s*([^\n\r,]+)', text_clean, re.I)
    if sal_match:
        salary = sal_match.group(1).strip()
    else:
        num_sal = re.search(r'(?:₹|\$|INR|USD|EUR)\s*[\d,]+(?:\s*(?:k|lac|lakh|per\s+(?:annum|year|month)|pa|pm|yr))?', text_clean, re.I)
        salary = num_sal.group(0).strip() if num_sal else "Not Stated"

    # Payment / Fee Request
    payment_request = "None Detected"
    fee_match = re.search(r'(?:(?:pay|remit|deposit|fee|charge|transfer)\s+(?:of\s+)?(?:₹|\$|INR|USD|EUR)?\s*[\d,]+|(?:₹|\$|INR|USD|EUR)\s*[\d,]+\s*(?:refundable|security|deposit|fee|charge))', text_clean, re.I)
    if fee_match:
        payment_request = fee_match.group(0).strip()

    # Communication Channel
    comm = "Standard Electronic / Mail"
    if re.search(r'\btelegram\b', text_clean, re.I):
        comm = "Telegram (External Instant Messenger)"
    elif re.search(r'\bwhatsapp\b', text_clean, re.I):
        comm = "WhatsApp (Direct Mobile Messaging)"
    elif re.search(r'\bsignal\b', text_clean, re.I):
        comm = "Signal Messenger"
    elif email and any(email.lower().endswith(dom) for dom in FREE_EMAIL_DOMAINS):
        comm = f"Public Webmail (@{email.split('@')[-1]})"
    elif email:
        comm = f"Enterprise Mail (@{email.split('@')[-1]})"

    # Location
    location = meta.get("job_location") or ""
    if not location:
        loc_match = re.search(r'(?:location|address|work location|base):\s*([^\n\r,]+)', text_clean, re.I)
        location = loc_match.group(1).strip() if loc_match else "Remote / Unspecified"

    return {
        "company": company,
        "role": role,
        "recruiter": recruiter,
        "email": email or "Not Disclosed",
        "phone": phone or "Not Disclosed",
        "salary": salary,
        "payment_request": payment_request,
        "communication": comm,
        "location": location
    }



# Known major brand domains for lookalike / typosquatting detection
TARGETED_BRANDS = {
    "microsoft.com": "Microsoft",
    "google.com": "Google",
    "paypal.com": "PayPal",
    "amazon.com": "Amazon",
    "apple.com": "Apple",
    "linkedin.com": "LinkedIn",
    "meta.com": "Meta",
    "facebook.com": "Facebook",
    "netflix.com": "Netflix",
    "chase.com": "Chase",
    "wellsfargo.com": "Wells Fargo",
    "binance.com": "Binance",
    "coinbase.com": "Coinbase",
    "dropbox.com": "Dropbox",
    "adobe.com": "Adobe",
    "telegram.org": "Telegram",
    "whatsapp.com": "WhatsApp"
}

# Common character substitution map for homoglyph / typosquatting detection
HOMOGLYPH_MAP = {
    '0': 'o',
    '1': 'l',
    'i': 'l',
    '5': 's',
    '3': 'e',
    '4': 'a',
    '8': 'b',
    'v': 'u',
}


def _levenshtein_distance(s1: str, s2: str) -> int:
    """Calculates Levenshtein edit distance between two strings"""
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


def detect_lookalike_domain(domain: str, claimed_company: str = "") -> Dict[str, Any]:
    """
    Detects typosquatting, character substitutions (micros0ft.com, paypa1.com),
    hyphen manipulation (company-careers-example.com, company-support-login.com),
    and Punycode (xn--) impersonation.
    Returns:
        possible_lookalike: bool
        similarity_score: int (0-100)
        matched_brand: str
        explanation: str
    NOTE: Do NOT automatically call a domain malicious solely because similarity is high.
    """
    if not domain:
        return {
            "possible_lookalike": False,
            "similarity_score": 0,
            "matched_brand": "None",
            "target_domain": "",
            "explanation": "No domain provided for lookalike evaluation."
        }

    clean_dom = domain.lower().strip()
    if clean_dom.startswith("www."):
        clean_dom = clean_dom[4:]

    # Check Punycode / Unicode lookalike
    if clean_dom.startswith("xn--") or ".xn--" in clean_dom:
        return {
            "possible_lookalike": True,
            "similarity_score": 88,
            "matched_brand": "Internationalized Domain / Punycode",
            "target_domain": clean_dom,
            "explanation": "Punycode (xn--) domain detected, which can be used for homograph character spoofing."
        }

    # Normalize homoglyphs/substitutions
    normalized = clean_dom
    has_substitutions = False
    sub_explanations = []
    for num_char, letter in HOMOGLYPH_MAP.items():
        if num_char in normalized:
            has_substitutions = True
            sub_explanations.append(f"'{num_char}' substituted for '{letter}'")
            normalized = normalized.replace(num_char, letter)

    # Check hyphen manipulation / suspicious prefixes & suffixes
    suspicious_keywords = ["careers", "support", "login", "portal", "verify", "secure", "auth", "jobs", "hr"]
    parts = clean_dom.split('.')
    main_label = parts[0] if parts else clean_dom

    has_suspicious_hyphen = False
    for kw in suspicious_keywords:
        if f"-{kw}" in main_label or f"{kw}-" in main_label:
            has_suspicious_hyphen = True
            break

    # Compare against targeted brands
    best_match_brand = ""
    best_match_dom = ""
    highest_sim = 0
    best_explanation = ""

    for target_dom, brand in TARGETED_BRANDS.items():
        target_label = target_dom.split('.')[0]
        # Direct exact match is legitimate brand domain, not a lookalike
        if clean_dom == target_dom:
            return {
                "possible_lookalike": False,
                "similarity_score": 100,
                "matched_brand": brand,
                "target_domain": target_dom,
                "explanation": f"Domain is the legitimate official domain for {brand}."
            }

        # Check normalized match (e.g. micros0ft.com -> microsoft.com)
        if normalized == target_dom:
            return {
                "possible_lookalike": True,
                "similarity_score": 95,
                "matched_brand": brand,
                "target_domain": target_dom,
                "explanation": f"Character substitution detected mimicking {brand} ({target_dom}): {', '.join(sub_explanations)}."
            }

        # Levenshtein distance on main labels
        dist = _levenshtein_distance(main_label, target_label)
        max_len = max(len(main_label), len(target_label))
        sim = int(max(0, (1 - dist / max_len) * 100))

        # Check if brand name is embedded with hyphens e.g. "paypal-careers.com"
        if target_label in main_label and main_label != target_label:
            sim = max(sim, 82)

        if sim > highest_sim:
            highest_sim = sim
            best_match_brand = brand
            best_match_dom = target_dom

    if highest_sim >= 80:
        exp = f"Domain structure is similar to {best_match_brand} ({best_match_dom})."
        if has_substitutions:
            exp += f" Contains character substitutions: {', '.join(sub_explanations)}."
        if has_suspicious_hyphen:
            exp += " Contains hyphenated credential/portal pattern."
        return {
            "possible_lookalike": True,
            "similarity_score": highest_sim,
            "matched_brand": best_match_brand,
            "target_domain": best_match_dom,
            "explanation": exp
        }

    if has_suspicious_hyphen:
        return {
            "possible_lookalike": True,
            "similarity_score": 72,
            "matched_brand": "Generic Portal",
            "target_domain": clean_dom,
            "explanation": f"Domain '{clean_dom}' contains hyphenated credential/career portal keywords."
        }

    return {
        "possible_lookalike": False,
        "similarity_score": highest_sim,
        "matched_brand": best_match_brand if highest_sim > 50 else "None",
        "target_domain": best_match_dom if highest_sim > 50 else "",
        "explanation": "No significant typosquatting or brand lookalike patterns detected."
    }


def extract_domain_intelligence(
    metadata: Optional[Dict[str, Any]] = None,
    entities: Optional[Dict[str, str]] = None,
    text: str = ""
) -> Dict[str, Any]:
    """
    Evaluates claimed web presence, DNS resolution, domain status, email consistency,
    and typosquatting lookalike analysis.
    Domain age and existence are provided as context, NOT definitive proof of fraud.
    """
    meta = metadata or {}
    ents = entities or {}

    raw_web = meta.get("company_website") or ""
    raw_email = ents.get("email") or meta.get("company_email") or ""
    claimed_company = ents.get("company") or meta.get("company_name") or "Claimed Entity"

    # Extract target domain
    target_domain = ""
    if raw_web:
        clean_url = raw_web if (raw_web.startswith("http://") or raw_web.startswith("https://")) else f"https://{raw_web}"
        try:
            target_domain = urlparse(clean_url).netloc.lower().split(":")[0]
        except Exception:
            target_domain = ""

    email_domain = ""
    if raw_email and "@" in raw_email and not raw_email.startswith("Not Disclosed"):
        email_domain = raw_email.split("@")[-1].lower().strip()

    active_domain = target_domain or email_domain or ""

    # Check DNS reachability & records
    has_a_record = False
    has_mx_record = False
    has_ns_record = False
    domain_status = "Unchecked / Not Provided"
    dns_note = "Domain details were not provided in document context."

    if active_domain and active_domain not in FREE_EMAIL_DOMAINS:
        try:
            socket.gethostbyname(active_domain)
            has_a_record = True
            domain_status = "Active / Resolving"
            dns_note = f"Host '{active_domain}' resolves via public DNS."
        except Exception:
            domain_status = "Unresolved / Inactive Host"
            dns_note = f"Host '{active_domain}' failed DNS resolution."

        # MX heuristic
        if email_domain and email_domain == active_domain:
            has_mx_record = has_a_record
        if has_a_record:
            has_ns_record = True

    # Email domain match check
    if email_domain and target_domain:
        if email_domain == target_domain or target_domain.endswith(f".{email_domain}"):
            match_status = "MATCH"
            match_label = "Corporate Match: Recruiter email matches claimed corporate domain."
        else:
            match_status = "MISMATCH"
            match_label = f"Domain Discrepancy: Recruiter uses @{email_domain} while company website is {target_domain}."
    elif email_domain in FREE_EMAIL_DOMAINS:
        match_status = "FREE_WEBMAIL"
        match_label = f"Public Webmail: Recruiter communicates via consumer webmail (@{email_domain})."
    elif email_domain:
        match_status = "CORPORATE_DOMAIN"
        match_label = f"Custom Domain: @{email_domain} is a private corporate domain."
    else:
        match_status = "UNSPECIFIED"
        match_label = "No recruiter email address provided for domain cross-referencing."

    # Lookalike Domain Detection
    lookalike_info = detect_lookalike_domain(active_domain, claimed_company)

    # Domain Age Context (Heuristic & contextual, never invented)
    is_free = email_domain in FREE_EMAIL_DOMAINS
    is_suspicious_tld = any(active_domain.endswith(tld) for tld in SUSPICIOUS_TLDS)

    if not active_domain:
        domain_age_context = "Domain age unavailable"
        domain_created = "N/A"
        registrar = "N/A"
    elif is_free:
        domain_age_context = "Public Webmail Provider (Established infrastructure)"
        domain_created = "Established Provider"
        registrar = "Public Email Service"
    elif has_a_record:
        domain_age_context = "Domain age unavailable (DNS Active)"
        domain_created = "Active Record"
        registrar = "Public Registry"
    else:
        domain_age_context = "Domain age unavailable (Unresolved Host)"
        domain_created = "Pending Verification"
        registrar = "Unknown Registrar"

    return {
        "claimed_company": claimed_company,
        "recruiter_domain": email_domain or (target_domain or "Not Provided"),
        "company_website": target_domain or (f"https://{email_domain}" if (email_domain and not is_free) else ""),
        "domain_age": domain_age_context,
        "domain_created": domain_created,
        "registrar": registrar,
        "domain_status": domain_status,
        "dns_records": {
            "a_record": has_a_record,
            "mx_record": has_mx_record,
            "ns_record": has_ns_record
        },
        "dns_note": dns_note,
        "https_available": True if target_domain else False,
        "email_domain_match": match_status,
        "match_label": match_label,
        "is_suspicious_tld": is_suspicious_tld,
        "lookalike": lookalike_info
    }


def extract_url_intelligence(text: str, claimed_company: str = "") -> List[Dict[str, Any]]:
    """
    Extracts URLs from document text and assesses security context:
    HTTPS status, domain, lookalike similarity, and risk context.
    Observed fact != final scam verdict.
    """
    if not text:
        return []

    # Find URLs
    raw_urls = re.findall(r'https?://[^\s<>"\')]+|[a-zA-Z0-9.-]+\.[a-zA-Z]{2,4}/[^\s<>"\')]*', text)
    results = []
    seen = set()

    for u in raw_urls:
        clean_u = u.strip().rstrip('.,;:!?)')
        if clean_u in seen:
            continue
        seen.add(clean_u)

        full_url = clean_u if clean_u.startswith("http") else f"https://{clean_u}"
        try:
            parsed = urlparse(full_url)
            domain = (parsed.netloc or parsed.path).lower().split(':')[0]
            is_https = full_url.lower().startswith("https://")
        except Exception:
            continue

        lookalike = detect_lookalike_domain(domain, claimed_company)

        # Risk context
        if lookalike.get("possible_lookalike"):
            risk_context = "Elevated uncertainty (Lookalike pattern detected)"
        elif any(domain.endswith(tld) for tld in SUSPICIOUS_TLDS):
            risk_context = "Elevated uncertainty (High-risk TLD)"
        elif not is_https:
            risk_context = "Unencrypted connection (HTTP)"
        else:
            risk_context = "Standard public web address"

        results.append({
            "url": clean_u,
            "domain": domain,
            "https": is_https,
            "redirects": 0,
            "lookalike": "Possible" if lookalike.get("possible_lookalike") else "None",
            "lookalike_details": lookalike,
            "domain_age": "Domain age unavailable",
            "risk_context": risk_context
        })

    return results


def build_forensic_signals(reasoning: List[Dict[str, Any]], doc_type: str = "JOB_OFFER") -> List[Dict[str, Any]]:
    """
    Constructs the 6-pillar forensic signal matrix.
    Scores represent risk (0-100), where HIGHER = HIGHER RISK.
    """
    signals = {
        "PAYMENT": {
            "name": "PAYMENT RISK",
            "score": 0,
            "explanation": "No upfront fee solicitation or advance payment demand detected.",
            "severity": "SAFE"
        },
        "IDENTITY": {
            "name": "IDENTITY RISK",
            "score": 0,
            "explanation": "No sensitive government ID, biometric, or banking credentials demanded.",
            "severity": "SAFE"
        },
        "URGENCY": {
            "name": "URGENCY RISK",
            "score": 0,
            "explanation": "Timeline and communication follow professional, non-pressured pacing.",
            "severity": "SAFE"
        },
        "CONTACT": {
            "name": "CONTACT RISK",
            "score": 0,
            "explanation": "Communication adheres to standard corporate channels or official context.",
            "severity": "SAFE"
        },
        "COMPANY": {
            "name": "COMPANY RISK",
            "score": 0,
            "explanation": "Organizational footprint and document context are internally consistent.",
            "severity": "SAFE"
        },
        "LANGUAGE": {
            "name": "LANGUAGE RISK",
            "score": 0,
            "explanation": "Linguistic structure and tone match standard professional formatting.",
            "severity": "SAFE"
        }
    }

    # Evaluate reasoning items
    for item in reasoning:
        finding = (item.get("finding", "") + " " + item.get("explanation", "")).lower()
        impact = int(item.get("impact_on_score") or 25)
        sev = (item.get("severity") or "HIGH").upper()

        if any(w in finding for w in ["payment", "fee", "deposit", "money", "crypto", "usdt", "cost", "charge", "zelle", "western union"]):
            signals["PAYMENT"]["score"] = min(100, max(signals["PAYMENT"]["score"], impact + 30))
            signals["PAYMENT"]["explanation"] = item.get("finding") or "Advance fee or security deposit requested."
            signals["PAYMENT"]["severity"] = sev

        if any(w in finding for w in ["identity", "ssn", "passport", "bank", "aadhaar", "pan", "cheque", "credential", "card"]):
            signals["IDENTITY"]["score"] = min(100, max(signals["IDENTITY"]["score"], impact + 25))
            signals["IDENTITY"]["explanation"] = item.get("finding") or "Excessive personal or financial credentials demanded."
            signals["IDENTITY"]["severity"] = sev

        if any(w in finding for w in ["urgency", "urgent", "pressure", "immediately", "today", "expire", "24 hours", "deadline"]):
            signals["URGENCY"]["score"] = min(100, max(signals["URGENCY"]["score"], impact + 20))
            signals["URGENCY"]["explanation"] = item.get("finding") or "Artificial deadline or high-pressure tactics detected."
            signals["URGENCY"]["severity"] = sev

        if any(w in finding for w in ["email", "domain", "contact", "gmail", "yahoo", "telegram", "whatsapp", "unverified"]):
            signals["CONTACT"]["score"] = min(100, max(signals["CONTACT"]["score"], impact + 25))
            signals["CONTACT"]["explanation"] = item.get("finding") or "Unverified or external recruiter communication channel."
            signals["CONTACT"]["severity"] = sev

        if any(w in finding for w in ["company", "impersonat", "unregistered", "fake", "website", "existence", "authenticity"]):
            signals["COMPANY"]["score"] = min(100, max(signals["COMPANY"]["score"], impact + 15))
            signals["COMPANY"]["explanation"] = item.get("finding") or "Entity verification incomplete or inconsistent."
            signals["COMPANY"]["severity"] = sev

        if any(w in finding for w in ["grammar", "spelling", "manipulat", "promise", "unrealistic", "task", "anomal"]):
            signals["LANGUAGE"]["score"] = min(100, max(signals["LANGUAGE"]["score"], impact + 15))
            signals["LANGUAGE"]["explanation"] = item.get("finding") or "Pressure, manipulation, or linguistic anomalies observed."
            signals["LANGUAGE"]["severity"] = sev

    # Format list
    result_list = []
    for key in ["PAYMENT", "IDENTITY", "URGENCY", "CONTACT", "COMPANY", "LANGUAGE"]:
        sig = signals[key]
        score = sig["score"]
        if score >= 75:
            sev = "CRITICAL"
        elif score >= 50:
            sev = "HIGH"
        elif score >= 25:
            sev = "MEDIUM"
        elif score > 0:
            sev = "LOW"
        else:
            sev = "SAFE"
        sig["severity"] = sev
        result_list.append(sig)

    return result_list


def build_ai_opinion(
    ai_result: Dict[str, Any],
    text: str = "",
    metadata: Optional[Dict[str, Any]] = None,
    entities: Optional[Dict[str, str]] = None,
    domain_intel: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Constructs the structured, evidence-grounded AI Opinion without exposing raw chain of thought.
    """
    classification = ai_result.get("classification", "LOW_RISK")
    risk_score = ai_result.get("risk_score", 0)
    confidence = ai_result.get("confidence", 90)
    doc_type = ai_result.get("document_type", "GENERAL_DOCUMENT")
    summary = ai_result.get("summary", "")
    reasoning = ai_result.get("reasoning", [])
    positive_signals = ai_result.get("positive_signals", [])
    uncertainties = ai_result.get("uncertainties", [])

    # Assessment headline
    if classification == "HIGH_RISK":
        assessment_headline = "Based on the extracted content, this document contains multiple independent indicators associated with fraudulent recruitment activity."
    elif classification == "MEDIUM_RISK":
        assessment_headline = "The document exhibits suspicious patterns or unverified communication channels that warrant heightened scrutiny."
    elif doc_type == "CERTIFICATE":
        assessment_headline = "The document is consistent with a participation or milestone credential. No material scam indicators were identified in the extracted text."
    else:
        assessment_headline = "The document does not contain strong indicators of scam behavior based on the available evidence."

    # Evidence-first reasoning items: OBSERVATION -> EVIDENCE -> INTERPRETATION -> RISK IMPACT
    opinion_reasoning = []
    for item in reasoning:
        evidence = item.get("evidence", "").strip()
        finding = item.get("finding", "Risk Indicator").strip()
        explanation = item.get("explanation", "").strip()
        sev = (item.get("severity") or "HIGH").upper()

        opinion_reasoning.append({
            "observation": finding,
            "evidence": evidence,
            "interpretation": explanation,
            "risk_impact": sev
        })

    # Legitimate positive signals
    formatted_positives = []
    for pos in positive_signals:
        f = pos.get("finding", "").strip()
        e = pos.get("evidence", "").strip()
        exp = pos.get("explanation", "").strip()
        if f:
            formatted_positives.append({
                "finding": f,
                "evidence": e,
                "explanation": exp
            })

    # Default positive signals for clean certificates if empty
    if not formatted_positives and doc_type == "CERTIFICATE" and classification == "LOW_RISK":
        formatted_positives = [
            {"finding": "No advance payment request", "evidence": "", "explanation": "The document contains zero solicitation for money, training deposits, or administrative fees."},
            {"finding": "No credential harvesting", "evidence": "", "explanation": "The document does not request identity numbers, banking cards, or personal accounts."},
            {"finding": "Standard credential wording", "evidence": "", "explanation": "Vocabulary and milestone descriptions match standard academic and industry learning programs."}
        ]

    # Uncertainties (distinguishing UNKNOWN from FRAUD)
    formatted_uncertainties = list(uncertainties)
    if doc_type == "CERTIFICATE":
        if not any("authenticity" in u.lower() for u in formatted_uncertainties):
            formatted_uncertainties.append("Certificate authenticity could not be independently confirmed from document text alone.")
        if not any("primarily designed" in u.lower() for u in formatted_uncertainties):
            formatted_uncertainties.append("The system is primarily designed for recruitment and job-offer scam analysis.")

    # Overall conclusion
    if classification == "HIGH_RISK":
        overall_conclusion = "The combination of financial solicitation, sensitive data collection, artificial urgency, or unverified communication channels produces a high-risk forensic determination."
    elif classification == "MEDIUM_RISK":
        overall_conclusion = "Due to ambiguous employer footprints or unverified external channels, further independent verification with corporate offices is strongly recommended."
    elif doc_type == "CERTIFICATE":
        overall_conclusion = "The available evidence does not provide sufficient grounds to classify this document as suspicious. Offline authenticity remains an uncertainty rather than an indicator of fraud."
    else:
        overall_conclusion = "The available evidence does not provide sufficient grounds to classify this document as suspicious. Standard due diligence is recommended."

    return {
        "assessment": assessment_headline,
        "summary": summary,
        "classification": classification,
        "risk_score": risk_score,
        "confidence": confidence,
        "document_type": doc_type,
        "reasoning": opinion_reasoning,
        "positive_signals": formatted_positives,
        "uncertainties": formatted_uncertainties,
        "overall_conclusion": overall_conclusion
    }


def build_document_intelligence(
    ai_result: Dict[str, Any],
    text: str = "",
    file_info: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Assembles technical document forensic metrics.
    """
    finfo = file_info or {}
    text_len = len(text)
    pages = finfo.get("page_count") or (1 if text_len < 3000 else max(1, text_len // 2500))

    ocr_quality = "Good (Clean Vector/OCR Extraction)"
    if text_len < 100:
        ocr_quality = "Poor / Low Text Yield"
    elif ai_result.get("extraction_warning"):
        ocr_quality = "Degraded / Partial Extraction"

    doc_assess = ai_result.get("document_assessment") or {}
    synth_possible = doc_assess.get("possible_synthetic_document", False)
    synth_conf = doc_assess.get("confidence", 50)
    synth_exp = doc_assess.get("explanation", "Standard document composition.")

    synth_label = "Possible Synthetic Formatting" if synth_possible else "Standard Composition"

    return {
        "document_type": ai_result.get("document_type", "UNKNOWN"),
        "document_type_confidence": ai_result.get("document_type_confidence", 85),
        "pages": pages,
        "ocr_quality": ocr_quality,
        "text_characters": text_len,
        "ocr_confidence": 94 if text_len > 200 else 70,
        "ai_confidence": ai_result.get("confidence", 90),
        "synthetic_assessment": synth_label,
        "synthetic_confidence": synth_conf,
        "synthetic_explanation": synth_exp
    }
