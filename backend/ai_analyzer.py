"""
AI Semantic Scam Analysis Engine
Uses local offline Ollama model (llama3.1:8b / llama3.2:3b) as the primary intelligence engine.
Performs semantic & contextual scam analysis with evidence-linked reasoning.
Zero cloud API keys, zero external network dependency.
"""

from typing import Dict, Any, Optional
from backend.ai.provider_factory import get_primary_ai_provider

def run_semantic_scam_analysis(text: str, metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Executes primary semantic and contextual scam analysis via local offline LLM.
    Strictly returns validated forensic analysis dict:
    - risk_score (0-100)
    - confidence (0-100)
    - classification (LOW_RISK | MEDIUM_RISK | HIGH_RISK)
    - summary
    - reasoning (list of findings with evidence, explanation, impact_on_score)
    - positive_signals
    - uncertainties
    - document_assessment (possible_synthetic_document, confidence, explanation)
    - recommendations
    - model_name
    """
    provider = get_primary_ai_provider()
    return provider.analyze_document(document_text=text, metadata=metadata)


def ai_scam_analysis(text: str, rule_result: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Backward-compatible entry point for the analysis pipeline.
    Invokes the local offline LLM.
    """
    metadata = {}
    if rule_result:
        metadata = {
            "company_name": rule_result.get("company_name", ""),
            "job_title": rule_result.get("job_title", ""),
            "company_email": rule_result.get("company_email", ""),
            "company_website": rule_result.get("company_website", ""),
            "company_phone": rule_result.get("company_phone", ""),
            "job_location": rule_result.get("job_location", "")
        }
    return run_semantic_scam_analysis(text=text, metadata=metadata)
