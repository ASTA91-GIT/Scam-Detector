"""
Company Intelligence Package for ScamGuard AI
Provides automated extraction of corporate entities, RDAP registration verification,
SSRF-safe website reachability, email domain corroboration, lookalike detection,
and public knowledge graph retrieval.
"""

from backend.company_intelligence.service import CompanyIntelligenceService
from backend.company_intelligence.extractor import extract_company_entities, discover_official_domain
from backend.company_intelligence.rdap import fetch_rdap_data, format_domain_age
from backend.company_intelligence.website import check_website_intelligence
from backend.company_intelligence.email import analyze_email_domain
from backend.company_intelligence.similarity import detect_lookalike_domain
from backend.company_intelligence.search import fetch_company_profile

__all__ = [
    "CompanyIntelligenceService",
    "extract_company_entities",
    "discover_official_domain",
    "fetch_rdap_data",
    "format_domain_age",
    "check_website_intelligence",
    "analyze_email_domain",
    "detect_lookalike_domain",
    "fetch_company_profile"
]
