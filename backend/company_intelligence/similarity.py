"""
Lookalike Domain Detection Engine
Identifies typosquatting, character substitutions (homoglyphs), hyphen insertions,
brand name embedding, and suspicious suffix patterns.
Never claims impersonation as a definitive fact solely from mathematical similarity.
"""

import re
from typing import Dict, Any, Optional

# Homoglyph character substitution map
HOMOGLYPH_MAP = {
    '0': 'o',
    '1': 'l',
    'i': 'l',
    '5': 's',
    '3': 'e',
    '4': 'a',
    '8': 'b',
    'v': 'u',
    'vv': 'w',
}

COMMON_TECH_BRANDS = {
    "google": "Google",
    "microsoft": "Microsoft",
    "apple": "Apple",
    "amazon": "Amazon",
    "meta": "Meta",
    "facebook": "Facebook",
    "netflix": "Netflix",
    "paypal": "PayPal",
    "linkedin": "LinkedIn",
    "oracle": "Oracle",
    "salesforce": "Salesforce",
    "adobe": "Adobe",
    "cisco": "Cisco",
    "ibm": "IBM",
    "intel": "Intel",
    "nvidia": "NVIDIA",
    "spotify": "Spotify",
    "uber": "Uber",
    "twitter": "Twitter",
    "telegram": "Telegram",
    "whatsapp": "WhatsApp",
    "tcs": "Tata Consultancy Services",
    "infosys": "Infosys",
    "wipro": "Wipro",
    "hcl": "HCLTech",
    "accenture": "Accenture",
    "deloitte": "Deloitte"
}

SUSPICIOUS_KEYWORD_PATTERNS = [
    "careers", "career", "jobs", "job", "hiring", "recruit", "recruitment",
    "verify", "verification", "auth", "portal", "login", "support",
    "security", "hr", "offer", "interview", "assessment", "work"
]


def _levenshtein_distance(s1: str, s2: str) -> int:
    """Computes edit distance between two strings."""
    if len(s1) < len(s2):
        return _levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    prev = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        curr = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = prev[j + 1] + 1
            deletions = curr[j] + 1
            substitutions = prev[j] + (c1 != c2)
            curr.append(min(insertions, deletions, substitutions))
        prev = curr
    return prev[-1]


def detect_lookalike_domain(domain: Optional[str],
                            company_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Evaluates whether a domain exhibits lookalike or typosquatting patterns.
    Returns:
    {
        "detected": bool,
        "similarity": int (0-100),
        "matched_brand": Optional[str],
        "target_domain": Optional[str],
        "explanation": str
    }
    """
    if not domain:
        return {
            "detected": False,
            "similarity": 0,
            "matched_brand": None,
            "target_domain": None,
            "explanation": "No domain provided for lookalike evaluation."
        }

    clean_dom = domain.lower().strip()
    if clean_dom.startswith("www."):
        clean_dom = clean_dom[4:]
    clean_dom = clean_dom.split("/")[0].split(":")[0]

    # 1. Punycode check
    if clean_dom.startswith("xn--") or ".xn--" in clean_dom:
        return {
            "detected": True,
            "similarity": 85,
            "matched_brand": "Internationalized / Punycode Domain",
            "target_domain": clean_dom,
            "explanation": "Punycode (xn--) domain detected. This format can be used for visual spoofing using non-ASCII lookalike characters."
        }

    parts = clean_dom.split(".")
    main_label = parts[0] if parts else clean_dom

    # Normalize homoglyphs in main label
    normalized_label = main_label
    substitutions_found = []
    for num_c, char_l in HOMOGLYPH_MAP.items():
        if num_c in normalized_label:
            substitutions_found.append(f"'{num_c}' replacing '{char_l}'")
            normalized_label = normalized_label.replace(num_c, char_l)

    # Candidate brands to test: known brands + the claimed company if provided
    brands_to_check = dict(COMMON_TECH_BRANDS)
    if company_name:
        clean_comp = re.sub(r'[^a-zA-Z0-9]', '', company_name).lower()
        if len(clean_comp) >= 3:
            brands_to_check[clean_comp] = company_name

    for brand_key, brand_title in brands_to_check.items():
        if len(brand_key) < 3:
            continue

        # If domain label is exact brand name and standard TLD, it is the legitimate brand, not a lookalike
        if main_label == brand_key and parts[-1] in ("com", "org", "net", "in", "co"):
            continue

        # Check A: Character substitution match (e.g. micros0ft.com or paypa1.com)
        if substitutions_found and normalized_label == brand_key:
            exp = f"Potential lookalike domain: Uses character substitution ({', '.join(substitutions_found)}) imitating {brand_title}."
            return {
                "detected": True,
                "similarity": 92,
                "matched_brand": brand_title,
                "target_domain": f"{brand_key}.com",
                "explanation": exp,
                "reasons": [exp]
            }

        # Check B: Brand name embedded with hyphens or suspicious keywords (e.g. microsoft-careers-example.com, microsoftjobs-example.com)
        has_hyphen = "-" in main_label
        has_kw = any(kw in main_label for kw in SUSPICIOUS_KEYWORD_PATTERNS)

        if brand_key in main_label and main_label != brand_key:
            if has_hyphen or has_kw:
                exp = f"Potential lookalike domain: Contains brand name '{brand_title}' combined with supplementary keywords/hyphens ({main_label})."
                return {
                    "detected": True,
                    "similarity": 80,
                    "matched_brand": brand_title,
                    "target_domain": f"{brand_key}.com",
                    "explanation": exp,
                    "reasons": [exp]
                }

        # Check C: Levenshtein distance 1 edit from brand name (e.g. googel, micorsoft)
        if len(brand_key) >= 5 and len(main_label) >= 4:
            dist = _levenshtein_distance(main_label, brand_key)
            if dist == 1 and main_label != brand_key:
                exp = f"Potential lookalike domain: Single-character misspelling of known brand '{brand_title}' (edit distance 1)."
                return {
                    "detected": True,
                    "similarity": 88,
                    "matched_brand": brand_title,
                    "target_domain": f"{brand_key}.com",
                    "explanation": exp,
                    "reasons": [exp]
                }

    return {
        "detected": False,
        "similarity": 0,
        "matched_brand": None,
        "target_domain": None,
        "explanation": "No lookalike or typosquatting indicators detected for this domain.",
        "reasons": []
    }
