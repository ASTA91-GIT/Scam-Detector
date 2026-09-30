"""
Test Suite for Real Company Intelligence & Company Verification
Verifies all 24 required test scenarios defined in Section 31 of specification:
1. Company clearly present
2. Company missing
3. Company extracted from email
4. Company website present
5. Domain age available
6. RDAP unavailable
7. Website reachable
8. Website unreachable
9. Matching email domain
10. Mismatching email domain
11. Gmail recruiter
12. Lookalike domain
13. New domain
14. Established domain
15. Unsupported TLD
16. Multiple company matches
17. SSRF localhost URL
18. Private IP URL
19. Timeout
20. Normal certificate
21. Legitimate internship offer
22. Suspicious job offer
23. Company exists but offer contains scam indicators
24. Company intelligence unavailable
"""

import os
import sys
import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from backend.company_intelligence.extractor import extract_company_entities, discover_official_domain
from backend.company_intelligence.rdap import fetch_rdap_data, format_domain_age
from backend.company_intelligence.website import check_website_intelligence, validate_safe_url
from backend.company_intelligence.email import analyze_email_domain
from backend.company_intelligence.similarity import detect_lookalike_domain
from backend.company_intelligence.service import CompanyIntelligenceService


@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.test_client() as client:
        yield client


# --------------------------------------------------------------------------
# Test 1: Company clearly present
# --------------------------------------------------------------------------
def test_01_company_clearly_present():
    doc_text = """
    OFFER OF EMPLOYMENT
    Apex Horizon Technologies Pvt Ltd
    123 Tech Park, Bangalore, Karnataka

    Dear Candidate,
    We are pleased to offer you the position of Senior Software Engineer at Apex Horizon Technologies Pvt Ltd.
    """
    res = extract_company_entities(doc_text)
    assert res['company_name']['value'] is not None
    assert 'Apex Horizon' in res['company_name']['value']
    assert res['company_name']['confidence'] >= 0.7
    assert res['job_title']['value'] == 'Senior Software Engineer'


# --------------------------------------------------------------------------
# Test 2: Company missing
# --------------------------------------------------------------------------
def test_02_company_missing():
    doc_text = """
    URGENT WORK FROM HOME OPPORTUNITY!
    Earn $500 per day by clicking buttons and submitting order reviews.
    Contact us immediately via telegram: @daily_tasks
    """
    res = extract_company_entities(doc_text)
    assert res['company_name']['value'] is None
    assert res['company_name']['value'] != "Unspecified Organization"


# --------------------------------------------------------------------------
# Test 3: Company extracted from email
# --------------------------------------------------------------------------
def test_03_company_extracted_from_email():
    doc_text = """
    Congratulations on your selection for the Junior Developer role.
    Please contact Sarah Connor for onboarding.
    Email: hr@innovatesoftware.com
    """
    res = extract_company_entities(doc_text)
    assert res['recruiter_email']['value'] == 'hr@innovatesoftware.com'
    # Extractor uses email domain to infer company if not explicitly found in text
    assert res['company_name']['value'] is not None
    assert 'Innovatesoftware' in res['company_name']['value'] or 'innovatesoftware' in res['company_name']['value'].lower()


# --------------------------------------------------------------------------
# Test 4: Company website present
# --------------------------------------------------------------------------
def test_04_company_website_present():
    doc_text = """
    Nexus Enterprise Solutions
    Visit our careers portal at https://www.nexusexample.com/jobs
    For questions, email careers@nexusexample.com
    """
    res = extract_company_entities(doc_text)
    assert res['company_website']['value'] is not None
    assert 'nexusexample.com' in res['company_website']['value']

    domain, src, conf = discover_official_domain(
        text=doc_text,
        company_name='Nexus Enterprise Solutions',
        recruiter_email=res['recruiter_email']['value']
    )
    assert domain == 'nexusexample.com'


# --------------------------------------------------------------------------
# Test 5: Domain age available
# --------------------------------------------------------------------------
def test_05_domain_age_available():
    fake_rdap_response = {
        "handle": "EXAMPLE-COM",
        "events": [
            {"eventAction": "registration", "eventDate": "2020-01-15T10:00:00Z"},
            {"eventAction": "expiration", "eventDate": "2028-01-15T10:00:00Z"}
        ],
        "entities": [
            {
                "roles": ["registrar"],
                "vcardArray": ["vcard", [["fn", {}, "text", "Example Registrar LLC"]]]
            }
        ],
        "nameservers": [{"ldhName": "ns1.example.com"}, {"ldhName": "ns2.example.com"}],
        "status": ["active"]
    }

    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = fake_rdap_response

        res = fetch_rdap_data('example.com')
        assert res['domain_status'] == 'active'
        assert res['domain_age_days'] is not None
        assert res['domain_age_days'] > 365
        assert res['domain_age_years'] >= 4.0
        assert "years" in res['domain_age_formatted']
        assert res['registrar'] == 'Example Registrar LLC'


# --------------------------------------------------------------------------
# Test 6: RDAP unavailable
# --------------------------------------------------------------------------
def test_06_rdap_unavailable():
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 404
        res = fetch_rdap_data('nonexistent-domain-12345.xyz')
        assert res['domain_status'] == 'UNAVAILABLE'
        assert res['domain_age_days'] is None
        assert res['domain_age_years'] is None
        assert res['domain_age_formatted'] == 'Information unavailable'


# --------------------------------------------------------------------------
# Test 7: Website reachable
# --------------------------------------------------------------------------
def test_07_website_reachable():
    with patch('requests.get') as mock_get:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.url = 'https://www.example.com/'
        mock_resp.text = '<html><head><title>Example Domain</title></head><body>Welcome</body></html>'
        mock_resp.history = []
        mock_get.return_value = mock_resp

        res = check_website_intelligence('example.com')
        assert res['reachable'] is True
        assert res['status_code'] == 200
        assert res['https'] is True
        assert res['tls_certificate'] is True


# --------------------------------------------------------------------------
# Test 8: Website unreachable
# --------------------------------------------------------------------------
def test_08_website_unreachable():
    with patch('requests.get', side_effect=Exception("Connection refused")):
        res = check_website_intelligence('unreachable-server-site.test')
        assert res['reachable'] is False
        assert res['https'] is False
        assert res['status_code'] is None


# --------------------------------------------------------------------------
# Test 9: Matching email domain
# --------------------------------------------------------------------------
def test_09_matching_email_domain():
    res = analyze_email_domain(
        email='recruitment.lead@cloudtech.com',
        official_domain='cloudtech.com'
    )
    assert res['status'] == 'MATCH'
    assert res['match'] is True
    assert res['email_domain'] == 'cloudtech.com'


# --------------------------------------------------------------------------
# Test 10: Mismatching email domain
# --------------------------------------------------------------------------
def test_10_mismatching_email_domain():
    res = analyze_email_domain(
        email='hr@cloudtech-careers-online.net',
        official_domain='cloudtech.com'
    )
    assert res['status'] == 'MISMATCH'
    assert res['match'] is False
    assert res['email_domain'] == 'cloudtech-careers-online.net'


# --------------------------------------------------------------------------
# Test 11: Gmail recruiter
# --------------------------------------------------------------------------
def test_11_gmail_recruiter():
    res = analyze_email_domain(
        email='recruiter.apex.corp@gmail.com',
        official_domain='apexcorp.com'
    )
    assert res['status'] == 'PERSONAL_EMAIL_PROVIDER'
    assert res['match'] is False
    assert res['is_personal_provider'] is True
    assert "public webmail" in res['explanation'].lower()


# --------------------------------------------------------------------------
# Test 12: Lookalike domain
# --------------------------------------------------------------------------
def test_12_lookalike_domain():
    # 1. Homoglyph / substitution: micros0ft.com vs microsoft.com
    res1 = detect_lookalike_domain('micros0ft.com', 'Microsoft Corporation')
    assert res1['detected'] is True
    assert any("substitution" in r.lower() or "character" in r.lower() for r in res1['reasons'])

    # 2. Suspicious compound suffix: microsoft-careers-jobs.com vs microsoft.com
    res2 = detect_lookalike_domain('microsoft-careers-jobs.com', 'Microsoft Corporation')
    assert res2['detected'] is True
    assert any("embedded" in r.lower() or "keyword" in r.lower() or "suffix" in r.lower() for r in res2['reasons'])


# --------------------------------------------------------------------------
# Test 13: New domain (< 90 days)
# --------------------------------------------------------------------------
def test_13_new_domain():
    recent_date = (datetime.now(timezone.utc) - timedelta(days=25)).isoformat()
    fake_data = {
        "events": [{"eventAction": "registration", "eventDate": recent_date}],
        "status": ["active"]
    }
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = fake_data

        res = fetch_rdap_data('freshly-registered.co')
        assert res['domain_age_days'] is not None
        assert res['domain_age_days'] <= 30
        assert res['domain_age_years'] < 0.2


# --------------------------------------------------------------------------
# Test 14: Established domain (> 5 years)
# --------------------------------------------------------------------------
def test_14_established_domain():
    old_date = (datetime.now(timezone.utc) - timedelta(days=365 * 6)).isoformat()
    fake_data = {
        "events": [{"eventAction": "registration", "eventDate": old_date}],
        "status": ["active"]
    }
    with patch('requests.get') as mock_get:
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = fake_data

        res = fetch_rdap_data('establishedcorp.org')
        assert res['domain_age_days'] > 2000
        assert res['domain_age_years'] >= 5.0


# --------------------------------------------------------------------------
# Test 15: Unsupported TLD
# --------------------------------------------------------------------------
def test_15_unsupported_tld():
    res = fetch_rdap_data('example.invalidtldxyz')
    assert res['domain_status'] == 'UNAVAILABLE'
    assert res['domain_age_formatted'] == 'Information unavailable'


# --------------------------------------------------------------------------
# Test 16: Multiple company matches
# --------------------------------------------------------------------------
def test_16_multiple_company_matches():
    doc_text = """
    EMPLOYMENT OFFER
    Client Organization: Acronis Cyber Systems Inc.
    Staffing Vendor: Global Talent Solutions LLC
    Payroll Partner: PayFlow Services Ltd.

    We welcome you to join Acronis Cyber Systems Inc. through Global Talent Solutions LLC.
    """
    res = extract_company_entities(doc_text)
    assert 'possible_matches' in res
    assert len(res['possible_matches']) >= 2
    match_names = [m['company_name'] for m in res['possible_matches']]
    assert any('Acronis' in n for n in match_names)
    assert any('Global Talent' in n for n in match_names)


# --------------------------------------------------------------------------
# Test 17: SSRF localhost URL
# --------------------------------------------------------------------------
def test_17_ssrf_localhost_url():
    is_safe1, _, err1 = validate_safe_url('http://localhost:8080/internal-status')
    assert is_safe1 is False
    assert err1 is not None

    is_safe2, _, err2 = validate_safe_url('http://127.0.0.1/admin')
    assert is_safe2 is False
    assert err2 is not None


# --------------------------------------------------------------------------
# Test 18: Private IP URL
# --------------------------------------------------------------------------
def test_18_private_ip_url():
    is_safe1, _, err1 = validate_safe_url('http://192.168.1.10/router')
    assert is_safe1 is False
    assert err1 is not None

    is_safe2, _, err2 = validate_safe_url('http://10.0.0.1:5000/config')
    assert is_safe2 is False
    assert err2 is not None


# --------------------------------------------------------------------------
# Test 19: Timeout handling
# --------------------------------------------------------------------------
def test_19_timeout():
    import requests
    with patch('requests.get', side_effect=requests.exceptions.Timeout("Request timed out after 5 seconds")):
        res = check_website_intelligence('very-slow-unresponsive-server.com')
        assert res['reachable'] is False
        assert res['status_code'] is None


# --------------------------------------------------------------------------
# Test 20: Normal certificate
# --------------------------------------------------------------------------
def test_20_normal_certificate():
    with patch('requests.Session.get') as mock_get, \
         patch('backend.company_intelligence.website.validate_safe_url', return_value=(True, 'secure-verified-corp.com', None)):
        resp = MagicMock()
        resp.status_code = 200
        resp.url = 'https://secure-verified-corp.com'
        resp.history = []
        resp.raw.read.return_value = b'<html><head><title>Secure Portal</title></head></html>'
        mock_get.return_value = resp

        res = check_website_intelligence('secure-verified-corp.com')
        assert res['reachable'] is True
        assert res['https'] is True
        assert res['tls_certificate'] is True


# --------------------------------------------------------------------------
# Test 21: Legitimate internship offer
# --------------------------------------------------------------------------
def test_21_legitimate_internship_offer():
    doc_text = """
    OFFER LETTER - SOFTWARE ENGINEERING INTERNSHIP
    Stripe Technology India Pvt Ltd
    Building 4, Outer Ring Road, Bengaluru, India

    Dear Rahul,
    We are pleased to offer you an internship as a Software Engineering Intern at Stripe Technology India Pvt Ltd.
    Stipend: INR 75,000 per month
    Duration: 6 Months
    Official Website: https://www.stripe.com
    HR Representative: Sarah Jenkins
    HR Email: sjenkins@stripe.com
    """
    with patch('backend.company_intelligence.service.fetch_rdap_data') as mock_rdap, \
         patch('backend.company_intelligence.service.check_website_intelligence') as mock_web:

        mock_rdap.return_value = {
            "domain": "stripe.com",
            "domain_status": "active",
            "domain_age_days": 4500,
            "domain_age_years": 12.3,
            "domain_age_formatted": "12 years 3 months",
            "registrar": "MarkMonitor",
            "nameservers": ["ns1.stripe.com"]
        }
        mock_web.return_value = {
            "reachable": True,
            "https": True,
            "status_code": 200,
            "final_url": "https://stripe.com",
            "tls_certificate": True
        }

        ci = CompanyIntelligenceService.build_company_intelligence(text=doc_text)
        assert ci['company']['name'] is not None
        assert 'Stripe' in ci['company']['name']
        assert ci['domain']['domain'] == 'stripe.com'
        assert ci['email']['match'] is True
        assert ci['email']['status'] == 'MATCH'
        assert ci['trust_model']['verified'] is not None
        assert len(ci['sources']) >= 2


# --------------------------------------------------------------------------
# Test 22: Suspicious job offer
# --------------------------------------------------------------------------
def test_22_suspicious_job_offer():
    doc_text = """
    IMMEDIATE HIRE - DATA ENTRY OPERATOR
    Company: Global Apex Marketing Services
    Work from home. $90,000 per year.
    To process your application and equipment shipment, deposit $250 via Bitcoin or wire transfer.
    Send your receipt to hr.apex@gmail.com
    """
    ci = CompanyIntelligenceService.build_company_intelligence(text=doc_text)
    assert ci['email']['status'] == 'PERSONAL_EMAIL_PROVIDER'
    assert ci['email']['domain'] == 'gmail.com'
    assert 'gmail.com' in ci['ai_assessment'] or 'personal' in ci['ai_assessment'].lower()


# --------------------------------------------------------------------------
# Test 23: Company exists but offer contains scam indicators
# --------------------------------------------------------------------------
def test_23_company_exists_but_offer_contains_scam_indicators():
    # Legitimate corporate entity name is cited, but recruiter uses spoofed/different lookalike channel
    doc_text = """
    OFFICIAL OFFER LETTER
    Microsoft Corporation
    One Microsoft Way, Redmond, WA

    Dear Candidate,
    Congratulations on being hired as Senior Operations Specialist.
    Please contact your onboarding coordinator at hr@microsoft-careers-portal.com.
    Prior to receiving your MacBook Pro, you are required to purchase $400 Apple Gift Cards for IT configuration.
    """
    ci = CompanyIntelligenceService.build_company_intelligence(
        text=doc_text,
        metadata={
            'company_name': 'Microsoft Corporation',
            'company_email': 'hr@microsoft-careers-portal.com'
        }
    )
    # The system correctly identifies Microsoft Corporation as claimed company,
    # but detects recruiter email domain as lookalike or mismatch
    assert ci['company']['name'] is not None
    assert 'Microsoft' in ci['company']['name']
    assert ci['lookalike']['detected'] is True or ci['email']['status'] == 'MISMATCH'
    # Trust model maintains distinction: company existence != job offer legitimate
    assert "independently verify" in ci['ai_assessment'] or "signals" in ci['ai_assessment']


# --------------------------------------------------------------------------
# Test 24: Company intelligence unavailable
# --------------------------------------------------------------------------
def test_24_company_intelligence_unavailable():
    ci = CompanyIntelligenceService.build_company_intelligence(text="")
    assert ci['company']['name'] is None
    assert ci['domain']['domain'] is None
    assert ci['domain']['status'] == 'UNAVAILABLE'
    assert ci['website']['reachable'] is False
    assert "does not clearly identify" in ci['ai_assessment'] or "cannot be corroborated" in ci['ai_assessment']


# --------------------------------------------------------------------------
# Test API Endpoint: GET /api/company-intelligence
# --------------------------------------------------------------------------
def test_api_company_intelligence_endpoint(client):
    with patch('backend.company_intelligence.service.CompanyIntelligenceService.build_company_intelligence') as mock_build:
        mock_build.return_value = {
            "company": {
                "name": "Test Labs Inc",
                "industry": "Software",
                "location": "Boston, MA",
                "founded": "2015",
                "description": "Tech test company",
                "website": "https://testlabs.com"
            },
            "domain": {
                "domain": "testlabs.com",
                "age_days": 1800,
                "age_years": 4.9,
                "age_formatted": "4 years 11 months",
                "registrar": "GoDaddy",
                "status": "active"
            },
            "website": {
                "reachable": True,
                "https": True,
                "status_code": 200,
                "final_url": "https://testlabs.com",
                "tls_certificate": True
            },
            "email": {
                "email": "careers@testlabs.com",
                "domain": "testlabs.com",
                "match": True,
                "status": "MATCH",
                "explanation": "Corporate domain matches"
            },
            "lookalike": {
                "detected": False,
                "similarity": 0.0,
                "reasons": []
            },
            "sources": [
                {"name": "Domain Registration", "url": "https://rdap.org", "retrieved_at": "2026-09-30T10:00:00Z", "data_obtained": "Domain metadata"}
            ],
            "retrieved_at": "2026-09-30T10:00:00Z"
        }

        res = client.get('/api/company-intelligence?company=Test%20Labs%20Inc&domain=testlabs.com&email=careers@testlabs.com')
        assert res.status_code == 200
        data = res.get_json()
        assert data['status'] == 'success'
        assert data['company']['name'] == 'Test Labs Inc'
        assert data['domain']['domain'] == 'testlabs.com'
        assert data['email']['match'] is True
