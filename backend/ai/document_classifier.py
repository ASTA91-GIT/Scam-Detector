"""
Semantic Document Type Classifier
Classifies extracted document text into functional document categories before forensic scam evaluation.
Supported types:
- JOB_OFFER: Formal employment or internship offer letters
- RECRUITMENT_MESSAGE: Short messaging/outreach (LinkedIn, WhatsApp, Telegram, SMS, job boards)
- RECRUITER_EMAIL: Candidate outreach email correspondence
- CERTIFICATE: Course completion, participation, credential, degree, or achievement certificates
- RESUME: Curriculum vitae or candidate resume
- INVOICE: Billing statements, invoices, purchase orders
- PAYMENT_REQUEST: Direct payment demands, transfer notices, wire instructions
- CONTRACT: General legal agreements, non-disclosure agreements, service contracts
- IDENTITY_DOCUMENT: Passports, driver's licenses, government IDs
- GENERAL_DOCUMENT: Informational articles, guides, essays, policy manuals
- UNKNOWN: Ambiguous, unclassifiable, or corrupted text
"""

import json
import re
from typing import Dict, Any, Optional, Tuple

ALLOWED_DOCUMENT_TYPES = [
    "JOB_OFFER",
    "RECRUITMENT_MESSAGE",
    "RECRUITER_EMAIL",
    "CERTIFICATE",
    "RESUME",
    "INVOICE",
    "PAYMENT_REQUEST",
    "CONTRACT",
    "IDENTITY_DOCUMENT",
    "GENERAL_DOCUMENT",
    "UNKNOWN"
]

DOCUMENT_CLASSIFICATION_SYSTEM_PROMPT = """You are an expert document taxonomy classifier.
Analyze the provided document text and classify it into EXACTLY ONE of the following categories:
- JOB_OFFER: Formal job or internship employment offers with compensation or role terms.
- RECRUITMENT_MESSAGE: Outreach messages from recruiters on WhatsApp, Telegram, LinkedIn, SMS, or job portals.
- RECRUITER_EMAIL: Formal email correspondence regarding a candidate's application or interview.
- CERTIFICATE: Academic, training, course completion, webinar, hackathon, or participation certificates/awards.
- RESUME: Candidate resume, CV, or professional biography.
- INVOICE: Invoices, billing statements, fee receipts, or vendor bills.
- PAYMENT_REQUEST: Solicitations or demands for direct financial transfer or wire payments.
- CONTRACT: General legal agreements, NDAs, contractor terms, or master service agreements.
- IDENTITY_DOCUMENT: Government identification documents (passports, driver's licenses, national IDs).
- GENERAL_DOCUMENT: Articles, whitepapers, memos, general corporate documentation, or announcements.
- UNKNOWN: If the document is indecipherable, severely fragmented, or does not clearly fit any category.

Return ONLY a strict JSON object with:
{
  "document_type": "<ONE_OF_THE_ABOVE>",
  "document_type_confidence": <integer 0-100>,
  "reasoning": "<brief explanation of classification rationale>"
}"""


def classify_document_type(
    document_text: str,
    metadata: Optional[Dict[str, Any]] = None,
    provider: Any = None
) -> Tuple[str, int, str]:
    """
    Classifies the document text semantically using the local offline model.
    Falls back to semantic structural heuristics if local inference is unavailable.
    Returns: (document_type, confidence_int, reasoning)
    """
    clean_sample = (document_text or "").strip()[:2000]

    # Quick pre-validation for empty or trivial text
    if not clean_sample or len(clean_sample) < 15:
        return "UNKNOWN", 50, "Extracted text too sparse for definitive classification."

    # 1. Attempt LLM Semantic Classification if provider supplied or available
    if provider is not None:
        try:
            prompt = f"""Classify the functional category of this document text:
<document_sample>
{clean_sample}
</document_sample>

Remember: Return strictly valid JSON adhering to the required schema."""

            raw_res = provider.generate(
                messages=[{"role": "user", "content": prompt}],
                system_prompt=DOCUMENT_CLASSIFICATION_SYSTEM_PROMPT,
                max_tokens=100,
                temperature=0.0,
                response_format="json"
            )

            parsed = _parse_classification_json(raw_res)
            if parsed:
                return parsed
        except Exception as e:
            print(f"[WARN] Local LLM classification attempt failed, using structural analysis: {e}")

    # 2. Structural & Contextual Heuristic Analysis (deterministic fallback / supplement)
    return heuristic_document_classification(clean_sample)


def _parse_classification_json(raw_json: str) -> Optional[Tuple[str, int, str]]:
    """Safely parse LLM classification response"""
    try:
        cleaned = (raw_json or "").strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        data = json.loads(cleaned)
        doc_type = str(data.get("document_type", "")).strip().upper()
        if doc_type not in ALLOWED_DOCUMENT_TYPES:
            doc_type = "UNKNOWN"

        raw_conf = data.get("document_type_confidence", 85)
        try:
            # Handle float 0.0-1.0 or 0-100
            val = float(raw_conf)
            if val <= 1.0 and val > 0:
                val = val * 100
            conf = max(0, min(100, int(round(val))))
        except (ValueError, TypeError):
            conf = 80

        reasoning = str(data.get("reasoning", "")).strip() or f"Classified as {doc_type} based on structural content."
        return doc_type, conf, reasoning
    except Exception:
        return None


def heuristic_document_classification(text: str) -> Tuple[str, int, str]:
    """
    Context-aware structural classification of document text.
    Handles academic certificates, resumes, invoices, and offers.
    """
    text_lower = text.lower()

    # --- CERTIFICATE ---
    cert_signals = [
        "certificate of completion",
        "certificate of participation",
        "certificate of achievement",
        "certificate of appreciation",
        "has completed practical tasks",
        "has successfully completed",
        "job simulation",
        "certificate of excellence",
        "this certificate is presented to",
        "hereby certifies that",
        "enrolment verification code",
        "user verification code",
        "issued by forage",
        "coursera",
        "udemy",
        "edx"
    ]
    cert_matches = sum(1 for s in cert_signals if s in text_lower)
    if "certificate" in text_lower and (cert_matches >= 1 or "issued by" in text_lower or "presented to" in text_lower or "has completed" in text_lower):
        return "CERTIFICATE", 95, "Document contains explicit certificate terminology, recipient attribution, and completion verification markers."

    # --- RESUME ---
    resume_signals = [
        "curriculum vitae",
        "work experience",
        "education",
        "skills & abilities",
        "professional summary",
        "academic background",
        "projects & publications"
    ]
    resume_matches = sum(1 for s in resume_signals if s in text_lower)
    if resume_matches >= 3 or "curriculum vitae" in text_lower:
        return "RESUME", 92, "Document exhibits standard resume formatting, sections, and candidate biography."

    # --- INVOICE / PAYMENT REQUEST ---
    invoice_signals = ["invoice #", "bill to:", "total due", "remit payment to", "payment terms: net", "invoice date"]
    if any(s in text_lower for s in invoice_signals):
        return "INVOICE", 90, "Document contains billing structure, line items, or payment invoicing terms."

    # --- RECRUITMENT MESSAGE ---
    msg_signals = ["telegram", "whatsapp", "congratulations! you have been selected", "daily payout", "part-time online", "work from your phone"]
    if any(s in text_lower for s in msg_signals) and len(text) < 600:
        return "RECRUITMENT_MESSAGE", 88, "Short outreach message with direct messaging or mobile work solicitation."

    # --- JOB OFFER ---
    offer_signals = [
        "offer of employment",
        "employment agreement",
        "appointment letter",
        "formal offer",
        "annual base salary",
        "terms of employment",
        "remuneration & perquisites",
        "congratulations on your offer",
        "we are pleased to offer you",
        "position of"
    ]
    offer_matches = sum(1 for s in offer_signals if s in text_lower)
    if offer_matches >= 2 or "offer of employment" in text_lower or "appointment letter" in text_lower:
        return "JOB_OFFER", 92, "Document structured as a formal employment or internship offer with compensation or appointment details."

    # --- CONTRACT ---
    if "this agreement" in text_lower and ("governing law" in text_lower or "terms and conditions" in text_lower):
        return "CONTRACT", 85, "Document represents a formal legal contract or binding agreement."

    return "GENERAL_DOCUMENT", 70, "Document contains general text without definitive specialized employment, academic, or billing taxonomy."
