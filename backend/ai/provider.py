"""
Base AI Provider Interface
Defines the standard contract for CaseAI LLM providers.
"""
from abc import ABC, abstractmethod
from typing import Generator, List, Dict, Any, Optional

class AIProvider(ABC):
    """Abstract Base Class for all CaseAI LLM Providers"""

    @abstractmethod
    def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.2
    ) -> str:
        """
        Synchronous non-streaming generation.
        Returns complete response string.
        """
        pass

    @abstractmethod
    def stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.2
    ) -> Generator[str, None, None]:
        """
        Streaming generation yielding text chunks as they arrive from the LLM.
        """
        pass

    @abstractmethod
    def check_health(self) -> Dict[str, Any]:
        """
        Verify connection and availability of the provider.
        Returns dict with status, provider name, model, and message.
        """
        pass
