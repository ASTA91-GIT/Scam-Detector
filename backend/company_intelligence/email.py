"""
Email Domain Verification Engine
Compares recruiter and corporate email addresses against official company domains.
Classifies domain relationship as MATCH, MISMATCH, PERSONAL_EMAIL_PROVIDER, or UNKNOWN.
"""

from typing import Dict, Any, Optional
from backend.company_intelligence.schemas import empty_email_analysis

FREE_EMAIL_PROVIDERS = {
    'gmail.com', 'googlemail.com', 'yahoo.com', 'yahoo.co.in', 'yahoo.co.uk',
    'hotmail.com', 'outlook.com', 'live.com', 'msn.com',
    'aol.com', 'proton.me', 'protonmail.com', 'icloud.com', 'me.com',
    'zoho.com', 'yandex.com', 'yandex.ru', 'mail.com', 'gmx.com',
    'rediffmail.com', 'tutanota.com'
}


def normalize_domain(domain: Optional[str]) -> str:
    """Strips leading protocol, www., and trailing paths from domain string."""
    if not domain:
        return ""
    d = domain.lower().strip()
    if d.startswith("https://"):
        d = d[8:]
    elif d.startswith("http://"):
        d = d[7:]
    if d.startswith("www."):
        d = d[4:]
    return d.split("/")[0].split(":")[0].strip()


def analyze_email_domain(email: Optional[str], official_domain: Optional[str]) -> Dict[str, Any]:
    """
    Analyzes recruiter email domain vs company official domain.
    Explicit comparison result states:
    - MATCH: Email domain matches official domain (or valid organizational subdomain)
    - MISMATCH: Email domain differs from official domain, or uses a public webmail provider
    - POSSIBLE_MATCH: Email domain exhibits partial brand overlap or alternate corporate extension
    - INSUFFICIENT_DATA: Recruiter email or official domain is missing
    - UNAVAILABLE: External domain verification unavailable
    """
    res = empty_email_analysis(email or "", official_domain or "")
    if not email or not email.strip():
        res["match_type"] = "INSUFFICIENT_DATA"
        res["status"] = "INSUFFICIENT_DATA"
        res["comparison_result"] = "INSUFFICIENT_DATA"
        res["explanation"] = "No recruiter email address identified in document or metadata for verification."
        return res

    if "@" not in email:
        res["match_type"] = "UNAVAILABLE"
        res["status"] = "UNAVAILABLE"
        res["comparison_result"] = "UNAVAILABLE"
        res["explanation"] = f"Recruiter contact '{email}' is not a valid email address; domain verification unavailable."
        return res

    clean_email = email.strip()
    email_domain = clean_email.split("@")[-1].lower().strip()
    norm_official = normalize_domain(official_domain)

    if norm_official == "unavailable" or official_domain == "UNAVAILABLE":
        res["email"] = clean_email
        res["email_domain"] = email_domain
        res["match_type"] = "UNAVAILABLE"
        res["status"] = "UNAVAILABLE"
        res["comparison_result"] = "UNAVAILABLE"
        res["explanation"] = "External domain telemetry is unavailable for comparison."
        return res

    res["email"] = clean_email
    res["email_domain"] = email_domain
    res["official_domain"] = norm_official

    # Check for personal webmail provider
    if email_domain in FREE_EMAIL_PROVIDERS:
        res["match"] = False
        res["is_free_provider"] = True
        res["is_personal_provider"] = True
        res["match_type"] = "PERSONAL_EMAIL_PROVIDER"
        res["status"] = "PERSONAL_EMAIL_PROVIDER"
        res["comparison_result"] = "MISMATCH"
        res["explanation"] = (
            f"Recruiter contact uses a free public webmail / email service (@{email_domain}) rather than an organizational domain. "
            "A Gmail or personal address is common in informal communication and is not standalone proof of fraud, "
            "but lacks corporate domain authentication."
        )
        return res

    res["is_free_provider"] = False
    res["is_personal_provider"] = False

    if not norm_official:
        res["match"] = False
        res["match_type"] = "UNKNOWN"
        res["status"] = "UNKNOWN"
        res["comparison_result"] = "INSUFFICIENT_DATA"
        res["explanation"] = f"Recruiter email uses @{email_domain}, but no official company domain was available for comparison."
        return res

    # Exact domain match
    if email_domain == norm_official:
        res["match"] = True
        res["match_type"] = "MATCH"
        res["status"] = "MATCH"
        res["comparison_result"] = "MATCH"
        res["explanation"] = (
            f"Recruiter email domain (@{email_domain}) directly matches the official company domain. "
            "A matching domain demonstrates sender consistency but does not independently authenticate this recruiter or offer letter."
        )
        return res

    # Subdomain match (e.g. careers.example.com or mail.example.com vs example.com)
    if email_domain.endswith(f".{norm_official}") or norm_official.endswith(f".{email_domain}"):
        res["match"] = True
        res["match_type"] = "MATCH"
        res["status"] = "MATCH"
        res["comparison_result"] = "MATCH"
        res["explanation"] = (
            f"Recruiter email domain (@{email_domain}) is an organizational subdomain of {norm_official}. "
            "A matching subdomain demonstrates organizational association but does not guarantee the offer is genuine."
        )
        return res

    # Check for possible cross-TLD match (e.g. acme.co.uk vs acme.com or acme.org vs acme.com)
    official_base = norm_official.split(".")[0]
    email_base = email_domain.split(".")[0]
    if official_base == email_base and len(official_base) >= 3:
        res["match"] = True
        res["match_type"] = "POSSIBLE_MATCH"
        res["status"] = "POSSIBLE_MATCH"
        res["comparison_result"] = "POSSIBLE_MATCH"
        res["explanation"] = (
            f"Recruiter email domain (@{email_domain}) shares the primary organizational name '{official_base}' with {norm_official}, "
            "but uses a different top-level domain. Requires verification."
        )
        return res

    # Definite mismatch
    res["match"] = False
    res["match_type"] = "MISMATCH"
    res["status"] = "MISMATCH"
    res["comparison_result"] = "MISMATCH"
    res["explanation"] = f"Recruiter email domain (@{email_domain}) differs from the discovered company domain ({norm_official})."
    return res
