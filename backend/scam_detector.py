"""
AI/NLP Scam Detection Engine
Cybersecurity forensics engine: keyword detection, urgency analysis, red flags,
exact evidence extraction, domain heuristics, and risk breakdown scoring.
"""

import re
import socket
from urllib.parse import urlparse

# -----------------------------
# CONFIGURATION & THREAT DICTIONARIES
# -----------------------------

SCAM_KEYWORDS = {
    'payment': ['pay', 'fee', 'deposit', 'registration fee', 'training fee', 'processing fee', 
                'money transfer', 'wire transfer', 'western union', 'moneygram', 'cash app', 
                'zelle', 'venmo', 'bitcoin', 'crypto', 'cryptocurrency', 'usdt', 'gift card'],
    'urgency': ['urgent', 'urgently', 'immediately', 'asap', 'right away', 'hurry', 'limited time', 
                'act now', 'expires today', 'last chance', 'immediate opening', 'start today'],
    'too_good': ['guaranteed income', 'guaranteed salary', 'no experience needed', 'no interview', 
                 'easy money', 'earn $500/day', 'high salary', 'unlimited earning', 'work 1 hour', 
                 'quick cash', 'instant hire', 'no skills required'],
    'personal_info': ['bank account', 'credit card', 'debit card', 'ssn', 'social security', 
                      'passport copy', 'routing number', 'otp', 'verification code', 'mother maiden name'],
    'suspicious_process': ['telegram', 'whatsapp only', 'signal app', 'google hangouts', 
                           'check deposit', 're-shipping', 'package forwarding', 'mystery shopper', 
                           'envelope stuffing', 'payment processing agent'],
    'grammar_anomalies': ['kindly revert', 'do the needful', 'dear candidate', 'esteemed job seeker', 
                          'revert back', 'congratulation for selection']
}

FREE_EMAIL_DOMAINS = [
    'gmail.com', 'yahoo.com', 'hotmail.com', 'outlook.com',
    'aol.com', 'protonmail.com', 'icloud.com', 'zoho.com',
    'yandex.com', 'mail.com', 'gmx.com'
]

SUSPICIOUS_TLDS = [
    '.top', '.xyz', '.click', '.buzz', '.fit', '.surf', '.work', 
    '.rest', '.cam', '.gq', '.ml', '.cf', '.tk', '.ga', '.icu'
]

# -----------------------------
# DETECTION & EVIDENCE EXTRACTION HELPERS
# -----------------------------

def extract_snippet(text, match_str, padding=40):
    """Find the exact sentence or surrounding context around a matched keyword/phrase"""
    if not match_str or not text:
        return ""
    idx = text.lower().find(match_str.lower())
    if idx == -1:
        return match_str
    start = max(0, idx - padding)
    end = min(len(text), idx + len(match_str) + padding)
    snippet = text[start:end].strip()
    if start > 0:
        snippet = "..." + snippet
    if end < len(text):
        snippet = snippet + "..."
    return snippet


def detect_scam_keywords(text):
    text_lower = text.lower()
    detected = {}
    score = 0
    snippets = {}

    for category, keywords in SCAM_KEYWORDS.items():
        hits = []
        for k in keywords:
            if re.search(r'\b' + re.escape(k) + r'\b', text_lower):
                hits.append(k)
                if category not in snippets:
                    snippets[category] = extract_snippet(text, k)
        if hits:
            detected[category] = hits
            score += len(hits)

    return detected, score, snippets


def analyze_urgency_language(text):
    patterns = [
        r'\b(urgent|urgently|immediately|asap|hurry|act now|right away)\b',
        r'\b(deadline|expires today|last chance|offer valid for \d+ hours?)\b',
        r'!{2,}'
    ]

    matches = []
    text_lower = text.lower()
    for p in patterns:
        found = re.findall(p, text_lower)
        if found:
            for item in found:
                if isinstance(item, tuple):
                    matches.extend([x for x in item if x])
                else:
                    matches.append(item)

    evidence = extract_snippet(text, matches[0]) if matches else ""
    return len(matches), matches, evidence


def analyze_grammar_quality(text):
    issues = 0
    patterns = [r'\bkindly\b', r'\brevert back\b', r'\bdo the needful\b', r'\bcongratulation for selection\b']
    matched_phrases = []
    text_lower = text.lower()
    for p in patterns:
        if re.search(p, text_lower):
            issues += 1
            clean_word = p.replace(r'\b', '')
            matched_phrases.append(clean_word)
    evidence = extract_snippet(text, matched_phrases[0]) if matched_phrases else ""
    return issues, matched_phrases, evidence


def detect_financial_red_flags(text):
    patterns = [
        r'\b(pay|payment|fee|deposit|charges|purchase equipment|reimburse)\b',
        r'\b(bitcoin|crypto|usdt|wire transfer|zelle|venmo|gift cards?)\b',
        r'\b(bank account|routing number|credit card|cheque|check)\b'
    ]

    matches = []
    text_lower = text.lower()
    for p in patterns:
        found = re.findall(p, text_lower)
        if found:
            for item in found:
                if isinstance(item, tuple):
                    matches.extend([x for x in item if x])
                else:
                    matches.append(item)

    evidence = extract_snippet(text, matches[0]) if matches else ""
    return len(matches), matches, evidence


def check_email_domain(email):
    if not email or '@' not in email:
        return False, None
    domain = email.split('@')[1].lower().strip()
    return domain in FREE_EMAIL_DOMAINS, domain


def verify_website_exists(url):
    if not url:
        return False, "No website provided"
    try:
        url_str = url.strip()
        if not url_str.startswith('http://') and not url_str.startswith('https://'):
            url_str = 'https://' + url_str
        parsed = urlparse(url_str)
        domain = parsed.netloc or parsed.path
        if ':' in domain:
            domain = domain.split(':')[0]
        socket.gethostbyname(domain)
        return True, "Domain DNS verified"
    except Exception as e:
        return False, f"DNS lookup failed: {str(e)}"

# -----------------------------
# URL SCANNER FOR PHISHING & HEURISTICS
# -----------------------------

def scan_url_safety(url, company_name=None):
    """
    Evaluates URL security without executing unsafe downloads or exploits.
    Checks protocol, TLD, IP hostnames, phishing keywords, and reachability.
    """
    if not url or len(url.strip()) < 3:
        return {
            'is_suspicious': True,
            'risk_level': 'High Risk',
            'score': 20,
            'findings': ['Invalid or empty URL provided'],
            'details': {}
        }

    url = url.strip()
    raw_url = url
    if not url.startswith('http://') and not url.startswith('https://'):
        url = 'https://' + url

    findings = []
    score = 100

    try:
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if ':' in domain:
            domain = domain.split(':')[0]

        is_https = raw_url.startswith('https://')
        if not is_https and raw_url.startswith('http://'):
            findings.append("Insecure HTTP protocol used instead of HTTPS")
            score -= 25

        # Check for direct IP address in domain
        if re.match(r'^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$', domain):
            findings.append("Direct IP address used instead of reputable domain name")
            score -= 40

        # Check suspicious TLDs
        has_suspicious_tld = any(domain.endswith(tld) for tld in SUSPICIOUS_TLDS)
        if has_suspicious_tld:
            findings.append("Domain utilizes a high-risk / low-reputation top-level domain (TLD)")
            score -= 30

        # Check for deceptive phishing words in subdomains or path
        phish_keywords = ['verify', 'login', 'secure-hr', 'portal-login', 'account-update', 'pay-fee', 'jobs-online']
        matched_kw = [k for k in phish_keywords if k in url.lower()]
        if matched_kw:
            findings.append(f"Suspicious phishing keyword(s) detected in URL structure: {', '.join(matched_kw)}")
            score -= 30

        # DNS resolution
        dns_ok, dns_msg = verify_website_exists(domain)
        if not dns_ok:
            findings.append("Domain does not resolve via public DNS (unreachable or inactive host)")
            score -= 35

        # Company mismatch check
        if company_name:
            clean_comp = re.sub(r'[^a-zA-Z0-9]', '', company_name.lower())
            if len(clean_comp) >= 4 and clean_comp not in domain.replace('.', ''):
                findings.append(f"Domain does not appear to reflect company name '{company_name}'")
                score -= 15

        score = max(0, min(100, score))
        risk_level = "Safe" if score >= 80 else ("Suspicious" if score >= 50 else "High Risk")

        return {
            'url': raw_url,
            'domain': domain,
            'is_https': is_https,
            'dns_reachable': dns_ok,
            'score': score,
            'risk_level': risk_level,
            'findings': findings if findings else ["URL structure matches standard legitimate web patterns"]
        }

    except Exception as e:
        return {
            'url': raw_url,
            'domain': 'unknown',
            'is_https': False,
            'dns_reachable': False,
            'score': 25,
            'risk_level': 'High Risk',
            'findings': [f"Malformed URL: {str(e)}"]
        }

# -----------------------------
# RISK BREAKDOWN & SCORING
# -----------------------------

def calculate_trust_score(keyword_score, urgency, grammar, financial, email_free, website_ok, company_match):
    score = 100
    score -= min(keyword_score * 5, 25)
    score -= min(urgency * 6, 20)
    score -= min(grammar * 5, 15)
    score -= min(financial * 8, 30)

    if email_free:
        score -= 15
    if not website_ok:
        score -= 15
    if not company_match:
        score -= 15

    return max(0, min(100, score))


def get_risk_level(score):
    if score >= 80:
        return "Safe"
    elif score >= 50:
        return "Suspicious"
    return "High Risk"


def get_risk_color(risk_level):
    if risk_level == "Safe":
        return "success"
    elif risk_level == "Suspicious":
        return "warning"
    return "danger"

# -----------------------------
# STRUCTURED RED FLAGS & RECOMMENDATIONS
# -----------------------------

def generate_red_flags_and_recommendations(analysis, raw_text=""):
    """
    Generates structured red flags containing severity, title, explanation,
    evidence snippet, and actionable recommendation.
    """
    structured_flags = []
    recommendations = []

    # 1. Financial Red Flag
    if analysis['financial_flags_count'] > 0:
        evidence = analysis.get('financial_evidence') or (analysis.get('financial_matches') and analysis['financial_matches'][0]) or ""
        structured_flags.append({
            'severity': 'CRITICAL',
            'title': 'Advance Payment or Monetary Transfer Requested',
            'explanation': 'Legitimate employers never require job seekers to pay registration fees, purchase equipment in advance, or accept checks for forwarding.',
            'evidence': evidence if evidence else "Payment or fee terminology identified in offer text.",
            'recommendation': 'Cease all communications and do not transfer funds, wire money, or provide bank details under any circumstances.'
        })
        recommendations.append("Do NOT send money, crypto, or cash via any channel.")

    # 2. Personal Info Red Flag
    detected_kw = analysis.get('keyword_detections', {})
    if 'personal_info' in detected_kw:
        evidence = analysis.get('keyword_snippets', {}).get('personal_info', 'Request for sensitive identifiers')
        structured_flags.append({
            'severity': 'HIGH',
            'title': 'Sensitive Identification or Banking Information Demanded',
            'explanation': 'Scammers frequently gather social security numbers, banking credentials, or government IDs early in the process to commit identity fraud.',
            'evidence': evidence,
            'recommendation': 'Never disclose passport numbers, OTP codes, or banking credentials before receiving a verified, formal offer with verified corporate identity.'
        })
        recommendations.append("Never share OTPs, bank account numbers, or SSN during the interview or preliminary screening.")

    # 3. Urgency / Psychological Manipulation
    if analysis['urgency_score'] > 0:
        evidence = analysis.get('urgency_evidence') or ""
        structured_flags.append({
            'severity': 'HIGH' if analysis['urgency_score'] >= 2 else 'MEDIUM',
            'title': 'High-Pressure Urgency Tactics Detected',
            'explanation': 'Artificial deadlines and pressure to act immediately are classic manipulation tactics designed to prevent candidates from conducting due diligence.',
            'evidence': evidence if evidence else "Immediate action demanded without standard review period.",
            'recommendation': 'Take time to step back, independently contact the company HR department, and never rush into signing or payment.'
        })
        recommendations.append("Resist artificial urgency; legitimate hiring procedures allow reasonable review time.")

    # 4. Email Domain Discrepancy
    if analysis['email_domain_suspicious']:
        email_dom = analysis.get('email_domain', 'free provider')
        structured_flags.append({
            'severity': 'HIGH',
            'title': 'Recruiter Utilizing Free Public Email Provider',
            'explanation': f"The recruiter is using a generic domain (@{email_dom}) rather than an authenticated corporate domain (@company.com).",
            'evidence': f"Recruiter contact domain: @{email_dom}",
            'recommendation': 'Look up the enterprise website directly and reach out to the talent acquisition team through verified corporate channels.'
        })
        recommendations.append("Contact the company through its official website careers page, not via free email addresses.")

    # 5. Website Verification Failure
    if not analysis['website_exists'] and analysis.get('website_status') != "No website provided":
        structured_flags.append({
            'severity': 'HIGH',
            'title': 'Company Web Presence Unverified or Inaccessible',
            'explanation': 'The designated company website could not be reached via standard DNS resolution, which strongly correlates with fly-by-night fraudulent entities.',
            'evidence': f"Status: {analysis.get('website_status', 'DNS failure')}",
            'recommendation': 'Verify corporate registrations through state business registers (e.g. SEC EDGAR, Companies House, MCA).'
        })
        recommendations.append("Verify the employer's corporate registration on official business registries.")

    # 6. Domain Mismatch
    if not analysis['company_match']:
        structured_flags.append({
            'severity': 'HIGH',
            'title': 'Recruiter Domain Does Not Match Company Website',
            'explanation': 'The email sender domain does not belong to the domain name of the claimed company website, indicating potential executive or recruiter impersonation.',
            'evidence': "Email domain does not match official company domain.",
            'recommendation': 'Confirm whether the sender is an authorized external agency or impersonator by cross-referencing LinkedIn and the corporate switchboard.'
        })
        recommendations.append("Validate the recruiter's identity against the company's verified LinkedIn employee directory.")

    # 7. Unrealistic Offer / Too Good To Be True
    if 'too_good' in detected_kw:
        evidence = analysis.get('keyword_snippets', {}).get('too_good', '')
        structured_flags.append({
            'severity': 'MEDIUM',
            'title': 'Unrealistic Compensation or Bypassed Evaluation',
            'explanation': 'Offers guaranteeing high compensation for minimal effort or bypassing interviews entirely are standard lures for recruitment fraud.',
            'evidence': evidence if evidence else "Guaranteed income with no interview or technical screening.",
            'recommendation': 'Compare compensation against current market rates on Glassdoor, Levels.fyi, or Payscale.'
        })
        recommendations.append("Beware of offers offering high salary for minimal tasks or without technical interviews.")

    # 8. Grammar & Phrasing Anomalies
    if analysis['grammar_issues'] > 0:
        evidence = analysis.get('grammar_evidence', '')
        structured_flags.append({
            'severity': 'LOW',
            'title': 'Non-Standard Phrasing or Known Scam Formulae',
            'explanation': 'Phrasing such as "kindly revert", "do the needful", or poorly formatted contractual text often characterizes syndicated overseas phishing rings.',
            'evidence': evidence if evidence else "Non-standard phrasing detected in communication.",
            'recommendation': 'Inspect official offer documentation for standard corporate formatting, legal disclaimers, and legitimate company headers.'
        })

    # Default safe recommendation if no red flags found
    if not structured_flags:
        recommendations.append("No critical indicators detected. Continue standard job search safety practices.")
        recommendations.append("Always verify offer letters with the company's formal HR division before signing.")

    # Backward-compatible list of string titles
    legacy_red_flags = [f['title'] for f in structured_flags]

    return structured_flags, legacy_red_flags, recommendations

# -----------------------------
# MAIN ANALYSIS ENGINE
# -----------------------------

def analyze_job_offer(text, company_email=None, company_website=None, company_name=None, job_title=None):
    """
    Forensic analysis of job offer text, contact information, and domain authenticity.
    """
    keywords, keyword_score, keyword_snippets = detect_scam_keywords(text)
    urgency_score, urgency_matches, urgency_evidence = analyze_urgency_language(text)
    grammar_issues, grammar_matches, grammar_evidence = analyze_grammar_quality(text)
    financial_count, financial_matches, financial_evidence = detect_financial_red_flags(text)

    email_suspicious, email_domain = check_email_domain(company_email) if company_email else (False, None)
    website_exists, website_status = verify_website_exists(company_website) if company_website else (True, "No website provided")

    company_match = True
    if company_email and company_website:
        try:
            email_dom = company_email.split('@')[1].lower()
            web_url = company_website if company_website.startswith('http') else 'https://' + company_website
            web_dom = urlparse(web_url).netloc.lower()
            if ':' in web_dom:
                web_dom = web_dom.split(':')[0]
            # Match domain or subdomain
            company_match = (email_dom in web_dom) or (web_dom in email_dom)
        except Exception:
            company_match = True

    trust_score = calculate_trust_score(
        keyword_score,
        urgency_score,
        grammar_issues,
        financial_count,
        email_suspicious,
        website_exists,
        company_match
    )

    risk_level = get_risk_level(trust_score)
    risk_color = get_risk_color(risk_level)

    # Modular Risk Breakdown Scores (0 - 100 where 100 is completely safe, 0 is extreme risk)
    payment_risk = max(0, 100 - (financial_count * 35))
    identity_risk = 30 if ('personal_info' in keywords) else 100
    urgency_risk = max(0, 100 - (urgency_score * 30))
    contact_risk = 25 if email_suspicious else 100
    company_risk = (100 if website_exists else 30) if company_website else 90
    if not company_match:
        company_risk = min(company_risk, 40)
    language_risk = max(0, 100 - (grammar_issues * 25))

    risk_breakdown = {
        'payment_risk': payment_risk,
        'identity_risk': identity_risk,
        'urgency_risk': urgency_risk,
        'contact_risk': contact_risk,
        'company_risk': company_risk,
        'language_risk': language_risk
    }

    explanations = []
    if financial_count:
        explanations.append(f"Financial transaction or advance fee requests identified ({financial_count} occurrences).")
    if 'personal_info' in keywords:
        explanations.append("Requests for sensitive personal identifiers (SSN, banking credentials) detected.")
    if urgency_score:
        explanations.append(f"High-urgency language and pressure tactics detected ({urgency_score} indicators).")
    if email_suspicious:
        explanations.append(f"Public free email domain (@{email_domain}) used instead of corporate email.")
    if not website_exists and company_website:
        explanations.append("Provided company website could not be verified via public DNS.")
    if not company_match:
        explanations.append("Email domain does not match the company website domain.")
    if 'too_good' in keywords:
        explanations.append("Unusually high compensation or bypassed hiring requirements detected.")
    if not explanations:
        explanations.append("No typical scam indicators or red flags detected in the analyzed offer.")

    prelim_result = {
        "trust_score": trust_score,
        "risk_level": risk_level,
        "risk_color": risk_color,
        "keyword_score": keyword_score,
        "explanations": explanations,
        "keyword_detections": keywords,
        "keyword_snippets": keyword_snippets,
        "urgency_score": urgency_score,
        "urgency_evidence": urgency_evidence,
        "grammar_issues": grammar_issues,
        "grammar_evidence": grammar_evidence,
        "financial_flags_count": financial_count,
        "financial_matches": financial_matches,
        "financial_evidence": financial_evidence,
        "company_email": company_email,
        "email_domain": email_domain,
        "email_domain_suspicious": email_suspicious,
        "company_website": company_website,
        "website_exists": website_exists,
        "website_status": website_status,
        "company_match": company_match,
        "company_name": company_name,
        "job_title": job_title,
        "risk_breakdown": risk_breakdown
    }

    structured_flags, legacy_red_flags, recommendations = generate_red_flags_and_recommendations(prelim_result, text)
    prelim_result["structured_red_flags"] = structured_flags
    prelim_result["red_flags"] = legacy_red_flags
    prelim_result["recommendations"] = recommendations

    return prelim_result
