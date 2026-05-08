import os
import asyncio
from typing import List, Dict, Any
import httpx


class LLMClient:
    def __init__(self, api_key: str | None = None, base_url: str = "https://api.deepseek.com"):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=60.0)
        self.semaphore = asyncio.Semaphore(3)

    async def chat(self, messages: List[Dict[str, str]], model: str = "deepseek-chat") -> Dict[str, Any]:
        async with self.semaphore:
            resp = await self.client.post(
                f"{self.base_url}/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json={"model": model, "messages": messages, "temperature": 0.7},
            )
            resp.raise_for_status()
            return resp.json()

    async def chat_with_retry(self, messages: List[Dict[str, str]], model: str = "deepseek-chat", retries: int = 1) -> Dict[str, Any]:
        for attempt in range(retries + 1):
            try:
                return await self.chat(messages, model)
            except Exception:
                if attempt == retries:
                    raise
                await asyncio.sleep(1)
