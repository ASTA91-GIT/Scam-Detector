"""
AI Provider Factory
Resolves the active AI provider based on environment configuration,
health checks, and graceful fallbacks.
"""
import os
from typing import Dict, Any, Tuple
from backend.ai.provider import AIProvider
from backend.ai.ollama_provider import OllamaProvider
from backend.ai.openai_provider import OpenAIProvider
from backend.ai.heuristic_provider import HeuristicProvider

def get_provider() -> Tuple[AIProvider, str]:
    """
    Returns (provider_instance, provider_name).
    Graceful priority:
    1. If AI_PROVIDER == 'ollama' and Ollama is reachable -> OllamaProvider
    2. If AI_PROVIDER == 'openai' and API key is set -> OpenAIProvider
    3. Auto-detect: check Ollama health -> if ok, OllamaProvider
    4. Auto-detect: check OPENAI_API_KEY -> if set, OpenAIProvider
    5. Fallback: HeuristicProvider
    """
    requested = os.getenv("AI_PROVIDER", "auto").lower()

    if requested == "ollama":
        provider = OllamaProvider()
        health = provider.check_health()
        if health.get("available"):
            return provider, "ollama"
        # If explicitly requested but offline, check OpenAI fallback
        if os.getenv("OPENAI_API_KEY"):
            return OpenAIProvider(), "openai"
        return HeuristicProvider(), "heuristic_offline"

    elif requested == "openai":
        if os.getenv("OPENAI_API_KEY"):
            return OpenAIProvider(), "openai"
        # Check Ollama fallback
        provider = OllamaProvider()
        if provider.check_health().get("available"):
            return provider, "ollama"
        return HeuristicProvider(), "heuristic_offline"

    # Auto mode:
    # 1. Check local Ollama
    ollama = OllamaProvider()
    if ollama.check_health().get("available"):
        return ollama, "ollama"

    # 2. Check OpenAI key
    if os.getenv("OPENAI_API_KEY"):
        return OpenAIProvider(), "openai"

    # 3. Fallback to heuristic
    return HeuristicProvider(), "heuristic"


def get_ai_status() -> Dict[str, Any]:
    """Provides system diagnostics on available AI providers"""
    ollama = OllamaProvider()
    ollama_health = ollama.check_health()

    openai_key = os.getenv("OPENAI_API_KEY", "")
    openai_available = bool(openai_key and len(openai_key.strip()) > 5)

    _, active_name = get_provider()

    return {
        "active_provider": active_name,
        "ollama": {
            "configured_url": ollama.base_url,
            "target_model": ollama.model,
            "running": ollama_health.get("available", False),
            "details": ollama_health.get("message", "")
        },
        "openai": {
            "configured": openai_available,
            "target_model": os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
        },
        "recommendation": (
            "Ready for local inference" if ollama_health.get("available")
            else "For local unlimited inference, start Ollama ('ollama run llama3'). For cloud inference, set OPENAI_API_KEY in .env."
        )
    }
