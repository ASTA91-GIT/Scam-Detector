"""
CaseAI AI Package
Exposes core providers, context builders, and chat services.
"""
from backend.ai.provider import AIProvider
from backend.ai.ollama_provider import OllamaProvider
from backend.ai.openai_provider import OpenAIProvider
from backend.ai.heuristic_provider import HeuristicProvider
from backend.ai.provider_factory import get_provider, get_ai_status
from backend.ai.case_context import get_case_context
from backend.ai.memory import CaseMemoryManager
from backend.ai.chat_service import CaseAIChatService

__all__ = [
    "AIProvider",
    "OllamaProvider",
    "OpenAIProvider",
    "HeuristicProvider",
    "get_provider",
    "get_ai_status",
    "get_case_context",
    "CaseMemoryManager",
    "CaseAIChatService"
]
