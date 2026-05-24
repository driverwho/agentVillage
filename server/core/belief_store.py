from __future__ import annotations
import json
import os
from typing import List, Optional
from server.models.belief import Belief

CONFIDENCE_PRIORITY = {"high": 3, "medium": 2, "low": 1}


class BeliefStore:
    """每个 NPC 独立的信念存储。

    持久化到 {base_path}/{npc_id}_beliefs.json
    """

    def __init__(self, npc_id: str, base_path: str = "data/users/default/beliefs"):
        self.npc_id = npc_id
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)
        self._beliefs: List[Belief] = []
        self._load()

    def _file_path(self) -> str:
        return os.path.join(self.base_path, f"{self.npc_id}_beliefs.json")

    def _load(self) -> None:
        path = self._file_path()
        if not os.path.exists(path):
            self._beliefs = []
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._beliefs = [Belief.from_dict(d) for d in data]

    def _save(self) -> None:
        path = self._file_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump([b.to_dict() for b in self._beliefs], f, ensure_ascii=False, indent=2)

    def add(self, belief: Belief) -> bool:
        for existing in self._beliefs:
            if existing.content == belief.content and existing.source == belief.source:
                return False
        self._beliefs.append(belief)
        self._save()
        return True

    def get(self, belief_id: str) -> Optional[Belief]:
        for b in self._beliefs:
            if b.id == belief_id:
                return b
        return None

    def get_all(self) -> List[Belief]:
        return list(self._beliefs)

    def get_by_about(self, subject: str) -> List[Belief]:
        return [b for b in self._beliefs if subject in b.about]

    def get_active(self, current_day: int) -> List[Belief]:
        return [b for b in self._beliefs if not b.is_expired(current_day)]

    def get_for_context(
        self,
        current_day: int,
        max_count: int = 20,
        relevance_filter: Optional[List[str]] = None,
    ) -> List[Belief]:
        active = self.get_active(current_day)
        if relevance_filter:
            active = [
                b for b in active
                if any(subj in b.about for subj in relevance_filter)
            ]

        def sort_key(b: Belief):
            priority = CONFIDENCE_PRIORITY.get(b.confidence, 0)
            recency = b.acquired_at.get("day", 0) * 24 + b.acquired_at.get("hour", 0)
            return (-priority, -recency)

        active.sort(key=sort_key)
        return active[:max_count]
