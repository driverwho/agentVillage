import time
import asyncio
from typing import List, Dict, Any, Set, Optional
from dataclasses import dataclass, field


MAX_LOGS = 200


@dataclass
class LLMRequestLog:
    id: int
    timestamp: float
    npc_id: str
    model: str
    request_messages: List[Dict[str, str]]
    response_raw: Optional[Dict[str, Any]]
    estimated_tokens: int
    latency_ms: float
    success: bool
    error: str = ""


class LLMRequestLogger:
    def __init__(self):
        self._logs: List[LLMRequestLog] = []
        self._counter = 0
        self._watchers: Set[asyncio.Queue] = set()

    def log(self, npc_id: str, model: str, request_messages: List[Dict[str, str]],
            response_raw: Optional[Dict[str, Any]], estimated_tokens: int,
            latency_ms: float, success: bool, error: str = "") -> LLMRequestLog:
        self._counter += 1
        entry = LLMRequestLog(
            id=self._counter,
            timestamp=time.time(),
            npc_id=npc_id,
            model=model,
            request_messages=request_messages,
            response_raw=response_raw,
            estimated_tokens=estimated_tokens,
            latency_ms=round(latency_ms, 1),
            success=success,
            error=error,
        )
        self._logs.append(entry)
        if len(self._logs) > MAX_LOGS:
            self._logs = self._logs[-MAX_LOGS:]
        for q in list(self._watchers):
            try:
                q.put_nowait(entry)
            except asyncio.QueueFull:
                pass
        return entry

    def get_recent(self, n: int = 50) -> List[Dict[str, Any]]:
        return [self._to_dict(e) for e in self._logs[-n:]]

    def subscribe(self) -> asyncio.Queue:
        q: asyncio.Queue = asyncio.Queue(maxsize=100)
        self._watchers.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue) -> None:
        self._watchers.discard(q)

    @staticmethod
    def _to_dict(e: LLMRequestLog) -> Dict[str, Any]:
        return {
            "id": e.id,
            "timestamp": e.timestamp,
            "npc_id": e.npc_id,
            "model": e.model,
            "request_messages": e.request_messages,
            "response_raw": e.response_raw,
            "estimated_tokens": e.estimated_tokens,
            "latency_ms": e.latency_ms,
            "success": e.success,
            "error": e.error,
        }


llm_logger = LLMRequestLogger()
