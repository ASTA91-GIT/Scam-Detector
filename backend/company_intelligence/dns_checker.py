"""
DNS Intelligence Utility
Resolves A, AAAA, MX, and NS DNS records using dnspython.
Acts as supporting contextual intelligence only; missing records are never treated
as standalone proof of fraud.
"""

import logging
from typing import Dict, Any, List
import dns.resolver

from backend.company_intelligence.schemas import empty_dns_intelligence

logger = logging.getLogger("scamguard.company_intelligence.dns")
DNS_TIMEOUT_SECONDS = 3.0


def resolve_dns_records(domain: str) -> Dict[str, Any]:
    """
    Queries public DNS servers for A, AAAA, MX, and NS records for a domain.
    Enforces strict timeouts.
    """
    res = empty_dns_intelligence()
    if not domain:
        return res

    clean_dom = domain.lower().strip()
    if clean_dom.startswith("www."):
        clean_dom = clean_dom[4:]
    clean_dom = clean_dom.split("/")[0].split(":")[0]

    resolver = dns.resolver.Resolver()
    resolver.timeout = DNS_TIMEOUT_SECONDS
    resolver.lifetime = DNS_TIMEOUT_SECONDS

    # 1. A Records
    try:
        a_answers = resolver.resolve(clean_dom, "A")
        res["a_records"] = [str(r.address) for r in a_answers]
        res["has_a"] = len(res["a_records"]) > 0
    except Exception:
        res["has_a"] = False

    # 2. AAAA Records
    try:
        aaaa_answers = resolver.resolve(clean_dom, "AAAA")
        res["aaaa_records"] = [str(r.address) for r in aaaa_answers]
        res["has_aaaa"] = len(res["aaaa_records"]) > 0
    except Exception:
        res["has_aaaa"] = False

    # 3. MX Records
    try:
        mx_answers = resolver.resolve(clean_dom, "MX")
        res["mx_records"] = [str(r.exchange).rstrip(".") for r in mx_answers]
        res["has_mx"] = len(res["mx_records"]) > 0
    except Exception:
        res["has_mx"] = False

    # 4. NS Records
    try:
        ns_answers = resolver.resolve(clean_dom, "NS")
        res["ns_records"] = [str(r.target).rstrip(".") for r in ns_answers]
        res["has_ns"] = len(res["ns_records"]) > 0
    except Exception:
        res["has_ns"] = False

    if res["has_a"] or res["has_mx"] or res["has_ns"]:
        res["dns_status"] = "ACTIVE"
    else:
        res["dns_status"] = "UNRESOLVED"

    return res
