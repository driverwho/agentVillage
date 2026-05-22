import os
import asyncio
import time
from typing import List, Dict, Any
import httpx


class LLMClient:
    def __init__(self, api_key: str | None = None, base_url: str | None = None, model: str | None = None):
        self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY", "")
        self.base_url = base_url or os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
        self.model = model or os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
        self.client = httpx.AsyncClient(timeout=60.0)
        self.semaphore = asyncio.Semaphore(3)

    async def chat(self, messages: List[Dict[str, str]], model: str | None = None) -> Dict[str, Any]:
        model = model or self.model
        payload = {"model": model, "messages": messages, "temperature": 0.7}
        t0 = time.time()
        async with self.semaphore:
            print(f"[LLM] 请求 {model} — {len(messages)} 条消息, {sum(len(str(m.get('content',''))) for m in messages)} 字符")
            resp = await self.client.post(
                f"{self.base_url}/v1/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"},
                json=payload,
            )
            elapsed = (time.time() - t0) * 1000
            resp.raise_for_status()
            data = resp.json()
            usage = data.get("usage", {})
            cached = usage.get("prompt_cache_hit_tokens", 0)
            missed = usage.get("prompt_cache_miss_tokens", 0)
            total_prompt = usage.get("prompt_tokens", 0)
            reply_preview = data.get("choices", [{}])[0].get("message", {}).get("content", "")[:80]
            cache_pct = f"{cached/total_prompt*100:.0f}%" if total_prompt else "N/A"
            print(f"[LLM] 成功 — {elapsed:.0f}ms — 缓存命中:{cached} 未命中:{missed} ({cache_pct}) — 回复预览: {reply_preview}...")
            return data

    async def chat_with_retry(self, messages: List[Dict[str, str]], model: str | None = None, retries: int = 1) -> Dict[str, Any]:
        model = model or self.model
        for attempt in range(retries + 1):
            try:
                return await self.chat(messages, model)
            except Exception as e:
                print(f"[LLM] 失败 (第{attempt+1}次): {e}")
                if attempt == retries:
                    raise
                await asyncio.sleep(1)


# 全局单例
_llm_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    global _llm_client
    if _llm_client is None:
        api_key = os.getenv("DEEPSEEK_API_KEY", "")
        if not api_key:
            print("[LLM] 警告: DEEPSEEK_API_KEY 未设置，将使用 fallback 回复")
        _llm_client = LLMClient()
        print(f"[LLM] 初始化 — 模型: {_llm_client.model}, API: {_llm_client.base_url}")
    return _llm_client
