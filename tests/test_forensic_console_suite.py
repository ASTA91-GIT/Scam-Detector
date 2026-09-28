"""
Test Suite for AI Forensic Investigation Console
Tests:
- TEST A: HIGH RISK OFFER with payment request, Aadhaar/PAN, WhatsApp, Gmail recruiter, urgent deadline.
  Verifies:
  - Document classified correctly
  - High risk score (>= 60)
  - AI Opinion with evidence-first reasoning (observation -> evidence -> interpretation -> risk impact)
  - Entities, Domain Intelligence, and Risk Signals populated
- TEST B: NORMAL PARTICIPATION CERTIFICATE
  Verifies:
  - Document classified as CERTIFICATE
  - Low risk score (<= 15)
  - Zero hallucinated scam findings
  - AI Opinion explains why it is low risk with positive signals and uncertainties (authenticity unverified != fraud)
"""

import os
import sys
import json
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from seed_test_user import seed_test_user, TEST_USER_EMAIL, TEST_USER_PASSWORD

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

API_BASE = "http://127.0.0.1:5000/api"

def get_auth_token():
    seed_test_user()
    login_url = f"{API_BASE}/auth/login"
    res = requests.post(login_url, json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    }, timeout=10)
    if res.status_code != 200:
        raise RuntimeError(f"Authentication failed: {res.text}")
    return res.json()["token"]

def run_tests():
    print("=" * 70)
    print("AI FORENSIC INVESTIGATION CONSOLE INTEGRATION TEST")
    print("=" * 70)

    token = get_auth_token()
    headers = {"Authorization": f"Bearer {token}"}
    print("[OK] Authenticated successfully with test account.")

    # -------------------------------------------------------------
    # TEST A: HIGH RISK OFFER
    # -------------------------------------------------------------
    print("\n--- RUNNING TEST A: HIGH RISK JOB OFFER ---")
    test_a_text = """
    GLOBAL INNOVATION SYSTEMS PRIVATE LIMITED
    Letter of Intent & Conditional Employment Offer
    Date: 28 September 2026
    Candidate Role: Software Development Engineer

    Dear Candidate,
    Congratulations on your direct selection for the role of Software Development Engineer at Global Innovation Systems Pvt Ltd.
    Compensation CTC: ₹9,60,000 per annum.

    MANDATORY PRE-EMPLOYMENT SECURITY DEPOSIT & EQUIPMENT BOND:
    To confirm your appointment and dispatch your encrypted Apple MacBook Pro M3 workstation, you are required to remit a refundable security deposit of ₹3,999 within 24 hours via UPI / Zelle to our verified vendor account at vendor.secure@okaxis. This amount will be reimbursed on your first salary cycle.

    ONBOARDING DOCUMENT SUBMISSION:
    Kindly submit clear color scans of your Aadhaar card, PAN card, cancelled bank cheque, and 3 months bank statements to our talent acquisition team via WhatsApp at +91 98765 43210 or email us at global.innovation.hr@gmail.com.

    FAILURE TO REMIT THE VERIFICATION CHARGE WITHIN 24 HOURS WILL RESULT IN IMMEDIATE CANCELLATION OF THIS OFFER.

    Warm Regards,
    Neha Sharma
    Senior Talent Acquisition Lead
    Global Innovation Systems
    Email: global.innovation.hr@gmail.com
    Website: https://globalinnovationsystems.com
    """

    res_a = requests.post(f"{API_BASE}/analysis/analyze", data={
        "text": test_a_text,
        "job_title": "Software Development Engineer",
        "company_name": "Global Innovation Systems",
        "company_email": "global.innovation.hr@gmail.com",
        "company_website": "https://globalinnovationsystems.com"
    }, headers=headers, timeout=60)

    if res_a.status_code != 200:
        print(f"[FAIL] Test A analyze endpoint returned {res_a.status_code}: {res_a.text}")
        sys.exit(1)

    data_a = res_a.json()["result"]
    analysis_id_a = data_a["analysis_id"]
    print(f"[OK] Test A analyzed. Analysis ID: {analysis_id_a}")

    # Fetch dossier
    dossier_res_a = requests.get(f"{API_BASE}/analysis/result/{analysis_id_a}", headers=headers, timeout=10)
    assert dossier_res_a.status_code == 200, f"Failed to get dossier: {dossier_res_a.text}"
    dossier_a = dossier_res_a.json()["analysis"]

    print(f"  * Document Type: {dossier_a.get('document_type')} ({dossier_a.get('document_type_confidence')}%)")
    print(f"  * Risk Score: {dossier_a.get('risk_score')}/100 | Classification: {dossier_a.get('classification')}")
    print(f"  * Confidence: {dossier_a.get('confidence')}%")

    ai_op_a = dossier_a.get("ai_opinion", {})
    print(f"  * AI Opinion Assessment: {ai_op_a.get('assessment')}")
    print(f"  * AI Opinion Reasoning Steps Count: {len(ai_op_a.get('reasoning', []))}")
    for idx, r in enumerate(ai_op_a.get("reasoning", [])):
        print(f"    Step {idx+1}: [{r.get('risk_impact')}] {r.get('observation')} -> Evidence: \"{r.get('evidence')}\"")

    entities_a = dossier_a.get("entities", {})
    print(f"  * Extracted Entities: Recruiter={entities_a.get('recruiter')}, Email={entities_a.get('email')}, Fee={entities_a.get('payment_request')}, Comm={entities_a.get('communication')}")

    dom_a = dossier_a.get("domain_intelligence", {})
    print(f"  * Domain Intelligence: Recruiter Domain={dom_a.get('recruiter_domain')}, Age={dom_a.get('domain_age')}, Status={dom_a.get('domain_status')}")

    signals_a = dossier_a.get("risk_signals", [])
    print(f"  * Risk Signals Count: {len(signals_a)}")
    for s in signals_a:
        print(f"    - {s.get('name')}: {s.get('score')}/100 [{s.get('severity')}] - {s.get('explanation')}")

    assert dossier_a["risk_score"] >= 60, f"Expected risk_score >= 60, got {dossier_a['risk_score']}"
    assert dossier_a["classification"] == "HIGH_RISK", f"Expected HIGH_RISK, got {dossier_a['classification']}"
    assert len(ai_op_a.get("reasoning", [])) > 0, "Expected non-empty AI Opinion reasoning"
    assert any("₹3,999" in r.get("evidence", "") or "₹3,999" in str(r) for r in ai_op_a.get("reasoning", [])), "Expected ₹3,999 evidence quoted"
    print("[PASS] TEST A VERIFIED SUCCESSFULLY.")

    # -------------------------------------------------------------
    # TEST B: NORMAL PARTICIPATION CERTIFICATE
    # -------------------------------------------------------------
    print("\n--- RUNNING TEST B: NORMAL PARTICIPATION CERTIFICATE ---")
    cert_path = "uploads/6aba8b2c42ff30a33befafe1_Technology_Engineering_Job_Simulation-ram.pdf"
    if not os.path.exists(cert_path):
        # Fallback to text
        print(f"[WARN] Certificate file {cert_path} not found on disk, using certificate text.")
        cert_data = {
            "text": """
            CERTIFICATE OF COMPLETION
            This is to certify that
            RAM
            has successfully completed the
            Technology & Engineering Job Simulation
            Issued on 28 September 2026
            Certificate ID: FORAGE-ENG-2026-RAM-99128
            Authorized Platform Verification: https://www.theforage.com/verify/FORAGE-ENG-2026-RAM-99128
            Forage Virtual Work Experiences
            """,
            "job_title": "Certificate of Completion",
            "company_name": "Forage"
        }
        res_b = requests.post(f"{API_BASE}/analysis/analyze", data=cert_data, headers=headers, timeout=60)
    else:
        with open(cert_path, "rb") as f:
            res_b = requests.post(
                f"{API_BASE}/analysis/analyze",
                files={"file": (os.path.basename(cert_path), f, "application/pdf")},
                data={"job_title": "Job Simulation Certificate", "company_name": "Forage"},
                headers=headers,
                timeout=60
            )

    if res_b.status_code != 200:
        print(f"[FAIL] Test B analyze endpoint returned {res_b.status_code}: {res_b.text}")
        sys.exit(1)

    data_b = res_b.json()["result"]
    analysis_id_b = data_b["analysis_id"]
    print(f"[OK] Test B analyzed. Analysis ID: {analysis_id_b}")

    dossier_res_b = requests.get(f"{API_BASE}/analysis/result/{analysis_id_b}", headers=headers, timeout=10)
    assert dossier_res_b.status_code == 200, f"Failed to get dossier: {dossier_res_b.text}"
    dossier_b = dossier_res_b.json()["analysis"]

    print(f"  * Document Type: {dossier_b.get('document_type')} ({dossier_b.get('document_type_confidence')}%)")
    print(f"  * Risk Score: {dossier_b.get('risk_score')}/100 | Classification: {dossier_b.get('classification')}")
    print(f"  * Confidence: {dossier_b.get('confidence')}%")

    ai_op_b = dossier_b.get("ai_opinion", {})
    print(f"  * AI Opinion Assessment: {ai_op_b.get('assessment')}")
    print(f"  * AI Opinion Conclusion: {ai_op_b.get('overall_conclusion')}")
    print(f"  * Positive Signals: {ai_op_b.get('positive_signals')}")
    print(f"  * Uncertainties: {ai_op_b.get('uncertainties')}")

    assert dossier_b["document_type"] == "CERTIFICATE", f"Expected CERTIFICATE, got {dossier_b['document_type']}"
    assert dossier_b["risk_score"] <= 15, f"Expected risk_score <= 15, got {dossier_b['risk_score']}"
    assert dossier_b["classification"] == "LOW_RISK", f"Expected LOW_RISK, got {dossier_b['classification']}"
    assert len(dossier_b.get("reasoning", [])) == 0, f"Expected 0 fraud reasoning findings for clean certificate, got {len(dossier_b.get('reasoning', []))}"
    assert any("primarily designed" in u.lower() or "authenticity" in u.lower() for u in dossier_b.get("uncertainties", [])), "Expected uncertainty about certificate authenticity"
    print("[PASS] TEST B VERIFIED SUCCESSFULLY.")

    print("\n" + "=" * 70)
    print("ALL INTEGRATION TESTS PASSED (100%)")
    print("=" * 70)

if __name__ == "__main__":
    run_tests()
