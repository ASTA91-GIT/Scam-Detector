import os
import requests

# -----------------------------
# Hugging Face Configuration
# -----------------------------

HF_API_TOKEN = os.getenv("HF_API_TOKEN")

HF_MODEL_URL = (
    "https://api-inference.huggingface.co/models/"
    "mistralai/Mistral-7B-Instruct-v0.2"
)

HEADERS = {
    "Authorization": f"Bearer {HF_API_TOKEN}",
    "Content-Type": "application/json"
}


# -----------------------------
# Main AI Function
# -----------------------------

def ai_scam_analysis(text: str, rule_result: dict) -> str:
    """
    Generates a human-style AI explanation focusing on intent,
    desperation, pressure, and manipulation tactics.
    """

    # If token missing, fallback immediately
    if not HF_API_TOKEN:
        return _fallback_explanation(rule_result)

    prompt = f"""
You are a cybersecurity expert analyzing job scam messages.

Explain the INTENT and PSYCHOLOGICAL TACTICS used in the message.
Focus on:
- desperation
- urgency or pressure
- manipulation
- removal of normal hiring steps
- emotional exploitation

Do NOT list keywords.
Do NOT repeat the message.
Explain like you are warning a real person.

Job message:
{text}

Detected risk level: {rule_result.get("risk_level")}
Trust score: {rule_result.get("trust_score")}

Write a short, clear paragraph.
"""

    try:
        response = requests.post(
            HF_MODEL_URL,
            headers=HEADERS,
            json={
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 160,
                    "temperature": 0.35,
                    "top_p": 0.9,
                    "return_full_text": False
                }
            },
            timeout=15
        )

        if response.status_code == 200:
            data = response.json()

            # HF text-generation models return a list
            if isinstance(data, list) and len(data) > 0:
                generated_text = data[0].get("generated_text", "").strip()

                if len(generated_text) > 40:
                    return generated_text

    except Exception as e:
        print("❌ Hugging Face AI error:", e)

    # Safe fallback if anything fails
    return _fallback_explanation(rule_result)


# -----------------------------
# Fallback Explanation
# -----------------------------

def _fallback_explanation(rule_result: dict) -> str:
    explanation = []

    if rule_result.get("risk_level") == "High Risk":
        explanation.append(
            "The message appears intentionally written to pressure the reader into quick action."
        )

    if rule_result.get("urgency_score", 0) > 0:
        explanation.append(
            "Urgent language creates desperation and discourages independent verification."
        )

    if rule_result.get("financial_flags_count", 0) > 0:
        explanation.append(
            "Early requests for money suggest manipulative intent rather than legitimate hiring."
        )

    if not rule_result.get("website_exists", True):
        explanation.append(
            "The absence of verifiable company information increases the likelihood of deception."
        )

    explanation.append(
        "Overall, the tone and structure resemble common employment scam techniques."
    )

    return " ".join(explanation)
