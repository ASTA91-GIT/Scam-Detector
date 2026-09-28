"""
Document-Type Aware Forensic Scam Test Suite
Validates the Document Classification & Context-Aware Scam Analysis architecture.

Tests:
1. Actual Uploaded Certificate: Technology_Engineering_Job_Simulation-ram.pdf
2. Test Case A: Normal participation certificate -> LOW_RISK
3. Test Case B: Normal achievement certificate -> LOW_RISK
4. Test Case C: Certificate containing a suspicious payment request -> Elevated risk based on actual evidence
5. Test Case D: Certificate containing a verification URL -> Contextual investigation without automatic scam penalty
6. Test Case E: AI-generated-looking certificate with no scam behavior -> LOW_RISK / uncertainty, NOT automatic HIGH_RISK
7. Test Case F: Job offer containing a payment request -> HIGH_RISK with evidence citation
"""

import os
import sys
import json
import requests

# Ensure workspace root in path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from seed_test_user import seed_test_user, TEST_USER_EMAIL, TEST_USER_PASSWORD

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:5000/api")
UPLOADS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads")
ACTUAL_CERT_FILE = os.path.join(UPLOADS_DIR, "6aba8b2c42ff30a33befafe1_Technology_Engineering_Job_Simulation-ram.pdf")

CERTIFICATE_TEST_CASES = {
    "1_actual_user_participation_certificate": {
        "is_file": True,
        "file_path": ACTUAL_CERT_FILE,
        "expected_type": "CERTIFICATE",
        "expected_classification": "LOW_RISK",
        "max_risk_score": 25,
        "description": "User's actual uploaded Forage Technology Engineering Job Simulation certificate"
    },

    "A_normal_participation_certificate": {
        "text": """CERTIFICATE OF PARTICIPATION
Presented to: Priya Sharma
For active participation in the National Women in Tech 2026 Virtual Summit held on March 14-16, 2026.
Organized by: TechLeaders Foundation India
Signatures:
Dr. Ananya Roy, Event Chairperson
Kavita Sen, Director of Outreach
Certificate ID: TLF-2026-CONF-9812""",
        "expected_type": "CERTIFICATE",
        "expected_classification": "LOW_RISK",
        "max_risk_score": 20,
        "description": "Standard conference participation certificate"
    },

    "B_normal_achievement_certificate": {
        "text": """ACADEMY OF APPLIED SCIENCES
CERTIFICATE OF ACADEMIC ACHIEVEMENT
This is to certify that
ALEXANDER D. MERCER
has demonstrated outstanding merit in Advanced Algorithmic Complexity, graduating in the top 5% of the Class of 2025.
Issued on December 15, 2025
Registrar: M. Abernathy
Dean of Faculty: Dr. H. Vance
Official Seal & Transcript Reference: AAS-ACAD-2025-4491""",
        "expected_type": "CERTIFICATE",
        "expected_classification": "LOW_RISK",
        "max_risk_score": 20,
        "description": "Standard university academic achievement certificate"
    },

    "C_certificate_with_suspicious_payment_request": {
        "text": """INTERNATIONAL MANAGEMENT CREDENTIALS INSTITUTE
CERTIFICATE OF COMPETENCY AWARD NOTICE
Candidate: Robert Davis
Congratulations! You have been awarded the Senior Executive Project Manager Credential.
CRITICAL PAYMENT REQUIRED TO RECEIVE CERTIFICATE:
To release your physical framed certificate and activate your permanent verification record, you must remit an administrative certificate release fee of $350 via Western Union or Bitcoin within 48 hours to our processing agent.
Failure to pay will result in cancellation of your award.""",
        "expected_type": ["CERTIFICATE", "PAYMENT_REQUEST"],
        "expected_classification": ["MEDIUM_RISK", "HIGH_RISK"],
        "min_risk_score": 50,
        "description": "Certificate containing an extortionate upfront fee demand"
    },

    "D_certificate_with_verification_url": {
        "text": """CERTIFICATE OF PARTICIPATION
Global AI Hackathon 2026
This acknowledges that Daniel Zhao successfully participated in the 48-Hour Open Source AI Challenge.
Project: Autonomous Assistive Navigation
Host: OpenAICode Community
To independently verify this digital certificate, visit our public verification registry at:
https://verify.openaicode.org/credentials/cert-88912-zhao
Date: February 20, 2026
Organizer Signature: Sarah Jenkins""",
        "expected_type": "CERTIFICATE",
        "expected_classification": "LOW_RISK",
        "max_risk_score": 25,
        "description": "Legitimate certificate containing an HTTPS credential verification URL"
    },

    "E_ai_generated_looking_certificate_no_scam": {
        "text": """DISTINGUISHED CERTIFICATE OF MERIT & SCHOLASTIC EXCELLENCE
In recognition of exemplary commitment and superior technical scholarship, this formal instrument confers upon
ELENA ROSTOVA
the status of Certified Machine Learning Systems Practitioner.
Conferred with highest commendations under the authority of the Global Curriculum Review Directorate.
Linguistic perfection, symmetrical floral border geometry, and pristine synthetic typographical layout.
Issued this 12th day of January, 2026.
Credential Identifier: GCRD-ML-2026-00412""",
        "expected_type": "CERTIFICATE",
        "expected_classification": "LOW_RISK",
        "max_risk_score": 25,
        "description": "AI-generated polished certificate with zero fraudulent actions"
    },

    "F_job_offer_with_payment_request": {
        "text": """APEX PHARMACEUTICAL RESEARCH INC.
FORMAL OFFER OF EMPLOYMENT
Position: Clinical Data Analyst
Base Salary: $110,000 per year
Congratulations! You have been selected for this remote position.
MANDATORY PRE-EMPLOYMENT SECURITY DEPOSIT:
To confirm your acceptance, you are required to remit a refundable security deposit of $1,500 via Zelle to our regional equipment vendor within 24 hours to cover your encrypted home lab workstation.
Send payment receipt to apex-onboarding-hr@gmail.com to finalize your contract.""",
        "expected_type": "JOB_OFFER",
        "expected_classification": "HIGH_RISK",
        "min_risk_score": 60,
        "description": "Actual job offer scam demanding advance money and using Gmail address"
    }
}


def run_certificate_test_suite():
    print("=" * 70)
    print("DOCUMENT-TYPE AWARE CONTEXTUAL SCAM TEST SUITE")
    print("=" * 70)

    # 1. Authenticate with test user
    seed_test_user()
    login_res = requests.post(f"{BASE_URL}/auth/login", json={
        "email": TEST_USER_EMAIL,
        "password": TEST_USER_PASSWORD
    }, timeout=5)

    if login_res.status_code != 200:
        print(f"[ERROR] Login failed: {login_res.text}")
        return False

    token = login_res.json().get("token")
    headers = {"Authorization": f"Bearer {token}"}
    print("[OK] Authenticated successfully with test user.\n")

    passed = 0
    total = len(CERTIFICATE_TEST_CASES)

    for test_key, tc in CERTIFICATE_TEST_CASES.items():
        print(f"--- Running Test: {test_key} ---")
        print(f"Description: {tc.get('description')}")

        try:
            if tc.get("is_file"):
                file_path = tc["file_path"]
                if not os.path.exists(file_path):
                    print(f"[SKIP] File not found: {file_path}")
                    continue
                filename = os.path.basename(file_path)
                with open(file_path, "rb") as f:
                    res = requests.post(
                        f"{BASE_URL}/analysis/analyze",
                        headers=headers,
                        files={"file": (filename, f, "application/pdf")},
                        data={"company_name": "", "job_title": ""},
                        timeout=120
                    )
            else:
                res = requests.post(
                    f"{BASE_URL}/analysis/analyze",
                    headers=headers,
                    json={"text": tc["text"]},
                    timeout=120
                )

            if res.status_code != 200:
                print(f"  [FAIL] HTTP {res.status_code}: {res.text}")
                continue

            data = res.json().get("result", {})
            doc_type = data.get("document_type")
            doc_conf = data.get("document_type_confidence")
            risk_score = data.get("risk_score")
            risk_conf = data.get("confidence")
            classification = data.get("classification")
            reasoning = data.get("reasoning", [])
            uncertainties = data.get("uncertainties", [])

            print(f"  [RESULT] Document Type: {doc_type} ({doc_conf}%)")
            print(f"  [RESULT] Risk Score: {risk_score}/100 | Confidence: {risk_conf}% | Classification: {classification}")
            print(f"  [RESULT] Findings Count: {len(reasoning)}")

            if reasoning:
                for idx, r in enumerate(reasoning, 1):
                    print(f"    * Finding {idx}: [{r.get('severity')}] {r.get('finding')}")
                    print(f"      Evidence: \"{r.get('evidence')}\"")
                    print(f"      Explanation: {r.get('explanation')}")

            if uncertainties:
                print(f"  [RESULT] Uncertainties: {uncertainties[:2]}")

            # Validation assertions
            expected_type = tc.get("expected_type")
            if isinstance(expected_type, list):
                assert doc_type in expected_type, f"Expected type in {expected_type}, got {doc_type}"
            else:
                assert doc_type == expected_type, f"Expected type {expected_type}, got {doc_type}"

            if "expected_classification" in tc:
                exp_cls = tc["expected_classification"]
                if isinstance(exp_cls, list):
                    assert classification in exp_cls, f"Expected classification in {exp_cls}, got {classification}"
                else:
                    assert classification == exp_cls, f"Expected classification {exp_cls}, got {classification}"

            if "max_risk_score" in tc:
                assert risk_score <= tc["max_risk_score"], f"Score {risk_score} exceeded maximum {tc['max_risk_score']}"

            if "min_risk_score" in tc:
                assert risk_score >= tc["min_risk_score"], f"Score {risk_score} below minimum {tc['min_risk_score']}"

            print("  [PASS] Test verified successfully.\n")
            passed += 1

        except Exception as e:
            print(f"  [FAIL] Test {test_key} assertion error: {e}\n")

    print("=" * 70)
    print(f"TEST SUITE FINISHED: {passed}/{total} PASSED")
    print("=" * 70)
    return passed == total


if __name__ == "__main__":
    success = run_certificate_test_suite()
    sys.exit(0 if success else 1)
