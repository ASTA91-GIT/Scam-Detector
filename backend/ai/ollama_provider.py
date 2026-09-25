"""
Ollama Provider for Local LLM Execution
Enables local, private, offline-capable AI inference using Ollama.
Supports streaming responses, local health checking, and zero external token consumption.
"""
import os
import json
import requests
from typing import Generator, List, Dict, Any, Optional
from backend.ai.provider import AIProvider

class OllamaProvider(AIProvider):
    """Local Ollama client implementing AIProvider with streaming support"""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None
    ):
        self.base_url = (base_url or os.getenv("OLLAMA_BASE_URL") or "http://localhost:11434").rstrip("/")
        self.model = model or os.getenv("AI_MODEL") or "llama3"
        self.timeout = int(os.getenv("OLLAMA_TIMEOUT", "60"))

    def check_health(self) -> Dict[str, Any]:
        """Check if local Ollama daemon is reachable and list installed models"""
        import socket
        from urllib.parse import urlparse

        parsed = urlparse(self.base_url)
        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 11434

        # Fast socket test to prevent HTTP timeout delays
        try:
            with socket.create_connection((host, port), timeout=0.3):
                pass
        except Exception:
            return {
                "available": False,
                "provider": "ollama",
                "message": f"Could not connect to Ollama at {self.base_url}. Ensure 'ollama serve' is running."
            }

        try:
            res = requests.get(f"{self.base_url}/api/tags", timeout=2)
            if res.status_code == 200:
                data = res.json()
                models = [m.get("name") for m in data.get("models", [])]
                model_present = any(self.model in m for m in models)
                return {
                    "available": True,
                    "provider": "ollama",
                    "base_url": self.base_url,
                    "target_model": self.model,
                    "model_installed": model_present,
                    "available_models": models,
                    "message": f"Ollama is running locally. Model '{self.model}' {'ready' if model_present else 'needs download (ollama pull ' + self.model + ')'}."
                }
            return {
                "available": False,
                "provider": "ollama",
                "message": f"Ollama responded with HTTP {res.status_code}"
            }
        except Exception as e:
            return {
                "available": False,
                "provider": "ollama",
                "message": f"Could not connect to Ollama at {self.base_url}: {str(e)}"
            }

    def _prepare_payload(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str],
        max_tokens: int,
        temperature: float,
        stream: bool
    ) -> Dict[str, Any]:
        formatted_messages = []
        if system_prompt:
            formatted_messages.append({"role": "system", "content": system_prompt})
        for m in messages:
            formatted_messages.append({
                "role": m.get("role", "user"),
                "content": m.get("content", "")
            })

        return {
            "model": self.model,
            "messages": formatted_messages,
            "stream": stream,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }

    def generate(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.2
    ) -> str:
        """Synchronous generation using Ollama"""
        payload = self._prepare_payload(messages, system_prompt, max_tokens, temperature, stream=False)
        try:
            res = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout
            )
            res.raise_for_status()
            data = res.json()
            return data.get("message", {}).get("content", "").strip()
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Ollama generation failed: {str(e)}")

    def stream(
        self,
        messages: List[Dict[str, str]],
        system_prompt: Optional[str] = None,
        max_tokens: int = 1000,
        temperature: float = 0.2
    ) -> Generator[str, None, None]:
        """Streaming generator yielding text deltas as Ollama streams them"""
        payload = self._prepare_payload(messages, system_prompt, max_tokens, temperature, stream=True)
        try:
            with requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                stream=True,
                timeout=self.timeout
            ) as res:
                res.raise_for_status()
                for line in res.iter_lines(decode_unicode=True):
                    if not line:
                        continue
                    try:
                        chunk = json.loads(line)
                        content = chunk.get("message", {}).get("content", "")
                        if content:
                            yield content
                        if chunk.get("done", False):
                            break
                    except json.JSONDecodeError:
                        continue
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"Ollama stream error: {str(e)}")
