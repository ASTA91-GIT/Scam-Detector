"""
OpenAI-Compatible Provider for Cloud or Self-Hosted Inference
Supports OpenAI, Groq, OpenRouter, DeepSeek, or LM Studio via standard /v1/chat/completions.
Includes Server-Sent Events (SSE) streaming and API health checking.
"""
import os
import json
import requests
from typing import Generator, List, Dict, Any, Optional
from backend.ai.provider import AIProvider

class OpenAIProvider(AIProvider):
    """OpenAI-compatible client implementing AIProvider with SSE streaming"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        self.model = model or os.getenv("OPENAI_MODEL") or "gpt-4o-mini"
        self.timeout = int(os.getenv("AI_TIMEOUT", "60"))

    def check_health(self) -> Dict[str, Any]:
        """Check if API key is present and endpoint responds"""
        if not self.api_key:
            return {
                "available": False,
                "provider": "openai",
                "message": "OPENAI_API_KEY is not configured in environment or .env."
            }
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            res = requests.get(f"{self.base_url}/models", headers=headers, timeout=5)
            if res.status_code == 200:
                return {
                    "available": True,
                    "provider": "openai",
                    "base_url": self.base_url,
                    "target_model": self.model,
                    "message": f"Connected to OpenAI-compatible provider at {self.base_url} (Model: {self.model})."
                }
            return {
                "available": False,
                "provider": "openai",
                "message": f"Endpoint returned HTTP {res.status_code}: {res.text[:150]}"
            }
        except Exception as e:
            return {
                "available": False,
                "provider": "openai",
                "message": f"Connection to {self.base_url} failed: {str(e)}"
            }

    def _prepare_messages(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str]
    ) -> List[Dict[str, str]]:
        formatted = []
        if system_prompt:
            formatted.append({"role": "system", "content": system_prompt})
        for m in messages:
            formatted.append({
                "role": m.get("role", "user"),
                "content": m.get("content", "")
            })
        return formatted

    def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.2
    ) -> str:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAIProvider.")

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": self._prepare_messages(messages, system_prompt),
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": False
        }

        res = requests.post(url, headers=headers, json=payload, timeout=self.timeout)
        res.raise_for_status()
        data = res.json()
        return data["choices"][0]["message"]["content"].strip()

    def stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.2
    ) -> Generator[str, None, None]:
        if not self.api_key:
            raise ValueError("OPENAI_API_KEY is required for OpenAIProvider.")

        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": self._prepare_messages(messages, system_prompt),
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True
        }

        with requests.post(url, headers=headers, json=payload, stream=True, timeout=self.timeout) as res:
            res.raise_for_status()
            for line in res.iter_lines(decode_unicode=True):
                if not line:
                    continue
                if line.startswith("data: "):
                    data_str = line[6:].strip()
                    if data_str == "[DONE]":
                        break
                    try:
                        data = json.loads(data_str)
                        delta = data["choices"][0].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            yield content
                    except Exception:
                        continue
