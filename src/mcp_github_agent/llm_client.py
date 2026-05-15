from __future__ import annotations
import os
import httpx


class LLMClient:
    def __init__(self) -> None:
        self.provider = os.getenv("LLM_PROVIDER", "ollama").lower()
        if self.provider != "ollama":
            raise ValueError(f"Unsupported LLM provider: {self.provider}")

        self.model = os.getenv("LLM_MODEL", "mistral")
        self.api_url = os.getenv("OLLAMA_API_URL", "http://localhost:11434")

    async def send_prompt(self, prompt: str, max_tokens: int = 1200) -> str:
        return await self._ollama_request(prompt, max_tokens)

    async def _ollama_request(self, prompt: str, max_tokens: int) -> str:
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "temperature": 0.2,
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(f"{self.api_url}/api/generate", json=payload)
            response.raise_for_status()
            result = response.json()
            return result.get("response", "")
