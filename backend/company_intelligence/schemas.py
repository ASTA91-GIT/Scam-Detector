"""
Company Intelligence Schemas and Data Models
Defines structured contracts for Company Intelligence, Domain Intelligence,
Website Verification, Email Analysis, and Trust Classification.
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, timezone


def create_entity_field(value: Optional[str] = None,
                        confidence: float = 0.0,
                        source: str = "document",
                        evidence: str = "") -> Dict[str, Any]:
    """
    Standard entity field contract:
    {
        "value": ...,
        "confidence": 0.0 - 1.0,
        "source": "document" | "metadata" | "inferred",
        "evidence": "..."
    }
    """
    return {
        "value": value,
        "confidence": round(float(confidence), 2),
        "source": source,
        "evidence": evidence or ""
    }


def empty_company_profile() -> Dict[str, Any]:
    return {
        "name": None,
        "legal_name": None,
        "industry": "Information unavailable",
        "location": "Information unavailable",
        "description": "Information unavailable",
        "founded_year": None,
        "website": None,
        "logo_url": None,
        "public_profiles": [],
        "verified_presence": False,
        "retrieval_status": "UNAVAILABLE"
    }


def empty_domain_intelligence(domain: str = "") -> Dict[str, Any]:
    return {
        "domain": domain,
        "registrar": "Information unavailable",
        "creation_date": None,
        "expiration_date": None,
        "domain_status": "UNAVAILABLE",
        "nameservers": [],
        "domain_age_days": None,
        "domain_age_months": None,
        "domain_age_years": None,
        "domain_age_formatted": "Information unavailable",
        "is_recently_registered": False,
        "is_established": False,
        "lookup_timestamp": datetime.now(timezone.utc).isoformat(),
        "rdap_status": "UNAVAILABLE"
    }


def empty_website_intelligence(url: str = "") -> Dict[str, Any]:
    return {
        "reachable": False,
        "https": False,
        "status_code": None,
        "final_url": url or "",
        "domain": "",
        "tls_certificate": False,
        "tls_certificate_valid": False,
        "redirect_target": None,
        "title": None,
        "checked_at": None,
        "error": None
    }


def empty_email_analysis(email: str = "", official_domain: str = "") -> Dict[str, Any]:
    return {
        "email": email or "",
        "email_domain": "",
        "official_domain": official_domain or "",
        "match": False,
        "status": "UNKNOWN",
        "match_type": "UNKNOWN",  # MATCH, MISMATCH, PERSONAL_EMAIL_PROVIDER, UNKNOWN
        "is_free_provider": False,
        "is_personal_provider": False,
        "explanation": "No recruiter email provided for verification."
    }


def empty_lookalike_analysis(domain: str = "") -> Dict[str, Any]:
    return {
        "detected": False,
        "similarity": 0,
        "matched_brand": None,
        "target_domain": None,
        "explanation": "No lookalike anomalies detected.",
        "reasons": []
    }


def empty_dns_intelligence() -> Dict[str, Any]:
    return {
        "has_a": False,
        "has_aaaa": False,
        "has_mx": False,
        "has_ns": False,
        "a_records": [],
        "mx_records": [],
        "ns_records": [],
        "txt_records": [],
        "dns_status": "UNAVAILABLE"
    }
