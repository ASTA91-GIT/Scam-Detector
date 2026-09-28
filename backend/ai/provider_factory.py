"""
AI Provider Factory
Manages local offline LLM resolution for Scam Detector.
Enforces local Ollama execution as the authoritative primary intelligence engine.
"""

import os
from typing import Dict, Any, Tuple
from backend.ai.provider import AIProvider
from backend.ai.ollama_provider import OllamaProvider

def get_primary_ai_provider() -> OllamaProvider:
    """
    Returns the primary local Ollama provider.
    Ensures that no cloud AI API or silent fallback is used for primary scam analysis.
    """
    base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    model = os.getenv("AI_MODEL", "llama3.1:8b")
    return OllamaProvider(base_url=base_url, model=model)


def get_provider() -> Tuple[AIProvider, str]:
    """
    Returns (provider_instance, provider_name).
    Enforces local Ollama as the active provider.
    """
    provider = get_primary_ai_provider()
    health = provider.check_health()
    if health.get("available"):
        return provider, "ollama"
    try:
        from backend.ai.heuristic_provider import HeuristicProvider
        return HeuristicProvider(), "heuristic_offline"
    except Exception:
        return provider, "ollama"


def get_ai_status() -> Dict[str, Any]:
    """
    Backend health check for the local AI engine.
    Used by /api/ai/status and diagnostics.
    """
    provider = get_primary_ai_provider()
    health = provider.check_health()

    if health.get("available"):
        return {
            "available": True,
            "provider": "ollama",
            "active_provider": "ollama",
            "model": provider.model,
            "base_url": provider.base_url,
            "installed_models": health.get("installed_models", [])
        }
    else:
        return {
            "available": False,
            "provider": "ollama",
            "active_provider": "offline",
            "model": provider.model,
            "base_url": provider.base_url,
            "error": health.get("error", "Local AI model unavailable. Start Ollama and ensure the configured model is installed.")
        }
