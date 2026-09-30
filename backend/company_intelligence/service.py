"""
Company Intelligence Core Service
Orchestrates entity extraction, official domain discovery, RDAP registration telemetry,
website probing, DNS checks, lookalike analysis, and external public registry lookups.
Enforces the 4-tier Trust Model: OBSERVED, VERIFIED, INFERRED, UNKNOWN.
"""

import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List

from backend.company_intelligence.schemas import (
    empty_company_profile,
    empty_domain_intelligence,
    empty_website_intelligence,
    empty_email_analysis,
    empty_lookalike_analysis,
    empty_dns_intelligence
)
from backend.company_intelligence.extractor import (
    extract_company_entities,
    discover_official_domain,
    clean_ocr_text
)
from backend.company_intelligence.rdap import fetch_rdap_data
from backend.company_intelligence.website import check_website_intelligence
from backend.company_intelligence.email import analyze_email_domain
from backend.company_intelligence.similarity import detect_lookalike_domain
from backend.company_intelligence.search import fetch_company_profile
from backend.company_intelligence.dns_checker import resolve_dns_records
from backend.company_intelligence.cache import get_cached_intelligence, save_cached_intelligence

logger = logging.getLogger("scamguard.company_intelligence.service")


class CompanyIntelligenceService:
    """
    High-assurance company intelligence and verification engine.
    """

    @classmethod
    def extract_company(cls, text: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Extracts complete structured company and recruiter entities."""
        return extract_company_entities(text, metadata)

    @classmethod
    def discover_domain(cls,
                        company_name: Optional[str],
                        text: str = "",
                        email: Optional[str] = None,
                        metadata: Optional[Dict[str, Any]] = None) -> Optional[str]:
        """Discovers the company's official domain using multi-signal priority."""
        domain, _, _ = discover_official_domain(text, company_name, email, metadata)
        return domain

    @classmethod
    def fetch_company_profile(cls,
                              company_name: Optional[str],
                              domain: Optional[str] = None,
                              website_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Fetches public information from verified knowledge registries."""
        return fetch_company_profile(company_name, domain, website_data)

    @classmethod
    def fetch_domain_intelligence(cls, domain: str) -> Dict[str, Any]:
        """Retrieves official RDAP domain registration records and calculates domain age."""
        return fetch_rdap_data(domain)

    @classmethod
    def check_website(cls, domain: str, url: Optional[str] = None) -> Dict[str, Any]:
        """Performs SSRF-safe website reachability, HTTPS, and TLS verification."""
        target = url or domain
        return check_website_intelligence(target)

    @classmethod
    def analyze_email_domain(cls, email: Optional[str], official_domain: Optional[str]) -> Dict[str, Any]:
        """Evaluates whether recruiter email matches company official domain."""
        return analyze_email_domain(email, official_domain)

    @classmethod
    def detect_lookalike_domain(cls, domain: str, company_name: Optional[str] = None) -> Dict[str, Any]:
        """Checks for typosquatting, character substitutions, or suspicious brand combinations."""
        return detect_lookalike_domain(domain, company_name)

    @classmethod
    def build_company_intelligence(cls,
                                   text: str = "",
                                   metadata: Optional[Dict[str, Any]] = None,
                                   file_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Full end-to-end execution of the Company Intelligence Pipeline.
        1. Extract Entities (company, recruiter, email, website)
        2. Resolve Official Domain
        3. Check MongoDB Cache for Domain Telemetry
        4. RDAP Domain Intelligence (Creation date, Age, Registrar)
        5. SSRF-Safe Website Health & TLS Check
        6. DNS Resolution (A, AAAA, MX, NS)
        7. Recruiter Email Domain Verification
        8. Lookalike & Typosquatting Detection
        9. Public Company Profile Retrieval (Wikipedia, DDG)
        10. Trust Model & AI Company Assessment Construction
        """
        now_iso = datetime.now(timezone.utc).isoformat()
        sources: List[Dict[str, Any]] = []

        # 1. Extract Entities
        entities = cls.extract_company(text, metadata)
        company_field = entities.get("company_name", {})
        claimed_company = company_field.get("value")
        recruiter_email = entities.get("recruiter_email", {}).get("value")
        explicit_website = entities.get("company_website", {}).get("value")
        possible_matches = entities.get("possible_matches", [])

        # 2. Discover Domain
        domain = entities.get("company_domain", {}).get("value")
        if not domain and explicit_website:
            domain = cls.discover_domain(claimed_company, text, recruiter_email, metadata)

        rdap_data = None
        website_data = None
        dns_data = None
        is_cached = False

        # 3. Check Cache
        if domain:
            cached = get_cached_intelligence(domain)
            if cached:
                rdap_data = cached.get("rdap_data")
                website_data = cached.get("website_data")
                dns_data = cached.get("dns_data")
                sources.extend(cached.get("sources", []))
                is_cached = True

        # 4. Fetch Domain Telemetry if not cached
        if domain and not rdap_data:
            rdap_data = cls.fetch_domain_intelligence(domain)
            if rdap_data.get("rdap_status") == "SUCCESS":
                sources.append({
                    "source_name": "RDAP Official Registry (ICANN / Registry Gateway)",
                    "source_url": f"https://rdap.org/domain/{domain}",
                    "retrieved_timestamp": now_iso,
                    "data_obtained": f"Registration date ({rdap_data.get('creation_date')}), Registrar ({rdap_data.get('registrar')})"
                })

        if not rdap_data:
            rdap_data = empty_domain_intelligence(domain or "")

        # 5. Check Website if not cached
        if domain and not website_data:
            website_data = cls.check_website(domain, url=explicit_website)
            if website_data.get("reachable"):
                sources.append({
                    "source_name": f"Verified Web Host ({website_data.get('final_url')})",
                    "source_url": website_data.get("final_url"),
                    "retrieved_timestamp": now_iso,
                    "data_obtained": f"HTTP status {website_data.get('status_code')}, HTTPS: {website_data.get('https')}, TLS Valid: {website_data.get('tls_certificate_valid')}"
                })

        if not website_data:
            website_data = empty_website_intelligence(explicit_website or (f"https://{domain}" if domain else ""))

        # 6. DNS Records if not cached
        if domain and not dns_data:
            dns_data = resolve_dns_records(domain)
        if not dns_data:
            dns_data = empty_dns_intelligence()

        # Cache refreshed intelligence if fresh
        if domain and not is_cached:
            save_cached_intelligence(
                domain=domain,
                company_name=claimed_company,
                rdap_data=rdap_data,
                website_data=website_data,
                dns_data=dns_data,
                sources=sources
            )

        # 7. Email Domain Verification
        email_analysis = cls.analyze_email_domain(recruiter_email, domain)

        # 8. Lookalike Detection
        lookalike = cls.detect_lookalike_domain(domain, claimed_company)

        # 9. Public Company Profile
        company_profile = cls.fetch_company_profile(claimed_company, domain, website_data)
        if company_profile.get("sources"):
            for s in company_profile["sources"]:
                sources.append({
                    "source_name": s.get("source_name", "Public Registry"),
                    "source_url": s.get("source_url", ""),
                    "retrieved_timestamp": now_iso,
                    "data_obtained": s.get("data_obtained", "Public corporate profile")
                })

        # 10. Document Claim vs Public Information Comparison
        name_comparison = "UNVERIFIED"
        if claimed_company and company_profile.get("verified_presence"):
            if claimed_company.lower() in (company_profile.get("name") or "").lower():
                name_comparison = "NAME_MATCH"
            else:
                name_comparison = "NAME_MISMATCH"

        domain_comparison = email_analysis.get("match_type", "UNKNOWN")

        # 11. 4-Tier Trust Model Construction
        observed = []
        verified = []
        inferred = []
        unknown = []

        # Observed
        if claimed_company:
            observed.append(f"Document claims the employer is '{claimed_company}'.")
        else:
            observed.append("No unambiguous company or organization name could be identified in the document.")

        if recruiter_email:
            observed.append(f"Recruiter contact email cited in document is '{recruiter_email}'.")

        # Verified
        if rdap_data.get("rdap_status") == "SUCCESS":
            age_label = rdap_data.get("domain_age_formatted", "")
            verified.append(f"Official domain '{domain}' is registered with {rdap_data.get('registrar')} (Domain Age: {age_label}).")
        elif domain:
            verified.append(f"Domain '{domain}' was evaluated via network telemetry.")

        if website_data.get("reachable"):
            https_note = "HTTPS enabled" if website_data.get("https") else "HTTP only (no TLS)"
            verified.append(f"Website at '{website_data.get('final_url')}' is reachable (HTTP {website_data.get('status_code')}, {https_note}).")

        # Inferred
        if email_analysis.get("match"):
            inferred.append(f"Recruiter email domain (@{email_analysis.get('email_domain')}) is consistent with the corporate domain.")
        elif email_analysis.get("is_free_provider"):
            inferred.append(f"Recruiter uses a free public email service (@{email_analysis.get('email_domain')}), which is an informal hiring vector.")
        elif email_analysis.get("match_type") == "MISMATCH":
            inferred.append(f"Email domain (@{email_analysis.get('email_domain')}) does not match company domain ({domain}).")

        if lookalike.get("detected"):
            inferred.append(f"Potential lookalike indicator: {lookalike.get('explanation')}")

        # Unknown
        if not company_profile.get("verified_presence"):
            unknown.append("Independent public corporate registry records could not be confirmed for the claimed employer.")

        rec_name = entities.get("recruiter_name", {}).get("value")
        if rec_name:
            unknown.append(f"The specific recruiter individual '{rec_name}' could not be independently authenticated via public registries.")
        else:
            unknown.append("No specific recruiter signatory name was provided in the document.")

        # 12. Synthesized AI Company Assessment
        ai_assessment = cls._build_ai_company_assessment(
            claimed_company=claimed_company,
            domain=domain,
            rdap_data=rdap_data,
            website_data=website_data,
            email_analysis=email_analysis,
            lookalike=lookalike,
            company_profile=company_profile
        )

        return {
            "status": "success",
            "company": {
                "name": claimed_company,
                "display_name": claimed_company or "Company not identified",
                "identified": bool(claimed_company),
                "industry": company_profile.get("industry", "Information unavailable"),
                "location": company_profile.get("location", "Information unavailable"),
                "description": company_profile.get("description", "Information unavailable"),
                "founded_year": company_profile.get("founded_year"),
                "website": explicit_website or (f"https://{domain}" if domain else None),
                "logo_url": company_profile.get("logo_url"),
                "verified_presence": company_profile.get("verified_presence", False),
                "possible_matches": possible_matches
            },
            "domain": {
                "domain": domain,
                "display_domain": domain or "--",
                "identified": bool(domain),
                "creation_date": rdap_data.get("creation_date"),
                "expiration_date": rdap_data.get("expiration_date"),
                "age_days": rdap_data.get("domain_age_days"),
                "age_months": rdap_data.get("domain_age_months"),
                "age_years": rdap_data.get("domain_age_years"),
                "age_formatted": rdap_data.get("domain_age_formatted", "Information unavailable"),
                "registrar": rdap_data.get("registrar", "Information unavailable"),
                "status": rdap_data.get("domain_status", "UNAVAILABLE"),
                "nameservers": rdap_data.get("nameservers", []),
                "is_recently_registered": rdap_data.get("is_recently_registered", False),
                "is_established": rdap_data.get("is_established", False)
            },
            "website": {
                "reachable": website_data.get("reachable", False),
                "https": website_data.get("https", False),
                "status_code": website_data.get("status_code"),
                "final_url": website_data.get("final_url", ""),
                "tls_certificate": website_data.get("tls_certificate", website_data.get("tls_certificate_valid", False)),
                "tls_certificate_valid": website_data.get("tls_certificate_valid", False),
                "title": website_data.get("title")
            },
            "dns": dns_data,
            "email": {
                "email": recruiter_email or "Not disclosed",
                "domain": email_analysis.get("email_domain", ""),
                "match": email_analysis.get("match", False),
                "status": email_analysis.get("status", email_analysis.get("match_type", "UNKNOWN")),
                "match_type": email_analysis.get("match_type", "UNKNOWN"),
                "is_free_provider": email_analysis.get("is_free_provider", False),
                "is_personal_provider": email_analysis.get("is_personal_provider", email_analysis.get("is_free_provider", False)),
                "explanation": email_analysis.get("explanation", "")
            },
            "lookalike": {
                "detected": lookalike.get("detected", False),
                "similarity": lookalike.get("similarity", 0),
                "matched_brand": lookalike.get("matched_brand"),
                "target_domain": lookalike.get("target_domain"),
                "explanation": lookalike.get("explanation", ""),
                "reasons": lookalike.get("reasons", [lookalike.get("explanation", "")]) if lookalike.get("detected") else []
            },
            "comparison": {
                "name_match": name_comparison,
                "domain_match": domain_comparison
            },
            "trust_model": {
                "observed": observed,
                "verified": verified,
                "inferred": inferred,
                "unknown": unknown
            },
            "ai_assessment": ai_assessment,
            "sources": sources,
            "entities": entities,
            "retrieved_at": now_iso
        }

    @staticmethod
    def _build_ai_company_assessment(claimed_company: Optional[str],
                                     domain: Optional[str],
                                     rdap_data: Dict[str, Any],
                                     website_data: Dict[str, Any],
                                     email_analysis: Dict[str, Any],
                                     lookalike: Dict[str, Any],
                                     company_profile: Dict[str, Any]) -> str:
        """
        Constructs an evidence-grounded AI Company Assessment summary paragraph.
        Strictly observes the boundary between company presence and offer legitimacy.
        """
        if not claimed_company:
            return (
                "The analyzed document does not clearly identify an employing organization or registered corporate entity. "
                "Without a verifiable company identity or official domain, claims and terms within the document cannot be corroborated against public registries."
            )

        parts = [f"The document identifies '{claimed_company}' as the employer."]

        if domain:
            if rdap_data.get("rdap_status") == "SUCCESS":
                parts.append(
                    f"Public domain intelligence for '{domain}' confirms registration through {rdap_data.get('registrar')} "
                    f"(Domain Age: {rdap_data.get('domain_age_formatted')})."
                )
            elif website_data.get("reachable"):
                parts.append(f"The domain '{domain}' is active and responds over HTTP ({website_data.get('final_url')}).")
            else:
                parts.append(f"Domain telemetry for '{domain}' could not be independently retrieved from RDAP.")

        if email_analysis.get("match"):
            parts.append("The recruiter email domain matches the official organizational domain.")
        elif email_analysis.get("is_free_provider"):
            parts.append(f"The recruiter contact utilizes a public webmail service (@{email_analysis.get('email_domain')}), which lacks organizational affiliation.")
        elif email_analysis.get("match_type") == "MISMATCH":
            parts.append(f"The recruiter's email domain (@{email_analysis.get('email_domain')}) differs from the discovered corporate domain ({domain}).")

        if lookalike.get("detected"):
            parts.append(f"Notice: Lookalike analysis identified potential similarity anomalies ({lookalike.get('explanation')}).")

        parts.append(
            "These signals describe the external digital footprint of the claimed entity; they do not independently prove or disprove the authenticity of the specific job offer or recruiter."
        )

        return " ".join(parts)
