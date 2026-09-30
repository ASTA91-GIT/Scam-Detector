"""
RDAP Domain Intelligence Engine
Queries official RDAP (Registration Data Access Protocol) servers for domain telemetry.
Extracts registration date, registrar, expiration date, status, nameservers,
and computes calibrated domain age without ever inventing data.
"""

import logging
import re
from datetime import datetime, timezone
from typing import Dict, Any, Optional, List
import requests

from backend.company_intelligence.schemas import empty_domain_intelligence
from backend.network_security import validate_safe_url

logger = logging.getLogger("scamguard.company_intelligence.rdap")

# RDAP bootstrap endpoints
RDAP_BASE_URL = "https://rdap.org/domain"
REQUEST_TIMEOUT_SECONDS = 5


def format_domain_age(days: int) -> str:
    """Formats domain age into human-readable representation."""
    if days is None or days < 0:
        return "Information unavailable"
    if days == 0:
        return "0 days (Registered today)"
    if days == 1:
        return "1 day"
    if days < 30:
        return f"{days} days"

    years = days // 365
    remaining_days = days % 365
    months = remaining_days // 30

    if years == 0:
        if months == 1:
            return "1 month"
        return f"{months} months"
    else:
        y_label = "1 year" if years == 1 else f"{years} years"
        if months > 0:
            m_label = "1 month" if months == 1 else f"{months} months"
            return f"{y_label} {m_label}"
        return y_label


def parse_iso_datetime(date_str: str) -> Optional[datetime]:
    """Robustly parses ISO 8601 RDAP date strings."""
    if not date_str or not isinstance(date_str, str):
        return None

    cleaned = date_str.strip().replace("Z", "+00:00")
    # Truncate fractional seconds to 6 digits if longer
    cleaned = re.sub(r'(\.\d{6})\d+', r'\1', cleaned)

    try:
        dt = datetime.fromisoformat(cleaned)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        # Fallback regex extraction of YYYY-MM-DD
        m = re.match(r'^(\d{4})-(\d{2})-(\d{2})', date_str)
        if m:
            try:
                return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), tzinfo=timezone.utc)
            except Exception:
                return None
        return None


def fetch_rdap_data(domain: str) -> Dict[str, Any]:
    """
    Performs real RDAP lookup for a given domain using RDAP gateway (rdap.org).
    Returns real structured domain intelligence or status="UNAVAILABLE".
    Never invents or fabricates domain age.
    """
    clean_domain = (domain or "").lower().strip()
    if clean_domain.startswith("www."):
        clean_domain = clean_domain[4:]

    # Remove port or path if any
    clean_domain = clean_domain.split(":")[0].split("/")[0].strip()

    result = empty_domain_intelligence(clean_domain)

    # Basic domain format validation
    if not clean_domain or "." not in clean_domain or len(clean_domain) < 4:
        result["domain_status"] = "UNAVAILABLE"
        result["rdap_status"] = "INVALID_DOMAIN"
        return result

    rdap_url = f"{RDAP_BASE_URL}/{clean_domain}"
    is_safe, _, err = validate_safe_url(rdap_url)
    if not is_safe:
        logger.warning(f"RDAP query blocked by SSRF check: {err}")
        result["domain_status"] = "UNAVAILABLE"
        result["rdap_status"] = "BLOCKED_SSRF"
        return result

    headers = {
        "User-Agent": "ScamGuard-RDAP-Client/2.0 (+https://scamguard.local)",
        "Accept": "application/rdap+json, application/json"
    }

    try:
        resp = requests.get(rdap_url, headers=headers, timeout=(REQUEST_TIMEOUT_SECONDS, REQUEST_TIMEOUT_SECONDS), allow_redirects=True)
        if resp.status_code == 404:
            result["domain_status"] = "UNAVAILABLE"
            result["rdap_status"] = "NOT_FOUND"
            return result

        if resp.status_code != 200:
            result["domain_status"] = "UNAVAILABLE"
            result["rdap_status"] = f"HTTP_{resp.status_code}"
            return result

        data = resp.json()
        now = datetime.now(timezone.utc)

        # 1. Extract Events (Registration & Expiration)
        creation_date = None
        expiration_date = None

        events = data.get("events") or []
        for ev in events:
            action = (ev.get("eventAction") or "").lower()
            date_val = ev.get("eventDate")
            if not date_val:
                continue

            parsed_dt = parse_iso_datetime(date_val)
            if not parsed_dt:
                continue

            if action in ("registration", "registered", "created"):
                creation_date = parsed_dt
            elif action in ("expiration", "expired", "expiry"):
                expiration_date = parsed_dt

        # 2. Extract Registrar
        registrar_name = "Information unavailable"
        entities = data.get("entities") or []
        for ent in entities:
            roles = [r.lower() for r in (ent.get("roles") or [])]
            if "registrar" in roles:
                vcard = ent.get("vcardArray")
                if vcard and len(vcard) > 1 and isinstance(vcard[1], list):
                    for prop in vcard[1]:
                        if len(prop) > 3 and prop[0] == "fn":
                            registrar_name = str(prop[3]).strip()
                            break
                if registrar_name == "Information unavailable":
                    registrar_name = ent.get("handle") or ent.get("fn") or "Registered Entity"

        # 3. Extract Status
        status_list = data.get("status") or []
        if isinstance(status_list, list) and status_list:
            clean_status = ", ".join(status_list[:3])
        else:
            clean_status = "Active" if creation_date else "UNAVAILABLE"

        # 4. Extract Nameservers
        nameservers: List[str] = []
        ns_raw = data.get("nameservers") or []
        for ns in ns_raw:
            ns_name = ns.get("ldhName") or ns.get("handle")
            if ns_name:
                nameservers.append(ns_name.lower())

        # 5. Compute calibrated Domain Age
        age_days = None
        age_months = None
        age_years = None
        age_str = "Information unavailable"
        is_recent = False
        is_est = False

        if creation_date:
            delta = now - creation_date
            age_days = max(0, delta.days)
            age_years = round(age_days / 365.25, 2)
            age_months = round(age_days / 30.44, 1)
            age_str = format_domain_age(age_days)
            is_recent = age_days <= 90
            is_est = age_days >= 730  # 2+ years

        result.update({
            "domain": clean_domain,
            "registrar": registrar_name,
            "creation_date": creation_date.isoformat() if creation_date else None,
            "expiration_date": expiration_date.isoformat() if expiration_date else None,
            "domain_status": clean_status,
            "nameservers": nameservers,
            "domain_age_days": age_days,
            "domain_age_months": age_months,
            "domain_age_years": age_years,
            "domain_age_formatted": age_str,
            "is_recently_registered": is_recent,
            "is_established": is_est,
            "rdap_status": "SUCCESS",
            "lookup_timestamp": now.isoformat()
        })
        return result

    except requests.exceptions.Timeout:
        logger.warning(f"RDAP lookup timed out for domain: {clean_domain}")
        result["domain_status"] = "UNAVAILABLE"
        result["rdap_status"] = "TIMEOUT"
        return result
    except Exception as e:
        logger.warning(f"RDAP lookup failed for domain {clean_domain}: {e}")
        result["domain_status"] = "UNAVAILABLE"
        result["rdap_status"] = "ERROR"
        return result
