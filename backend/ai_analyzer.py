import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError("❌ GEMINI_API_KEY not found in .env")

genai.configure(api_key=GEMINI_API_KEY)

model = genai.GenerativeModel("gemini-pro")

def ai_scam_analysis(text, rule_result):
    prompt = f"""
You are a cybersecurity expert.

Analyze the following job offer and explain clearly:
- Why it may or may not be a scam
- Mention scam patterns
- Explain risks in simple terms
- Give clear advice to the user

Job Offer:
{text}

Rule-based findings:
{rule_result}

Write a detailed explanation (6–10 lines).
"""

    response = model.generate_content(prompt)
    return response.text.strip()
