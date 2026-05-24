from __future__ import annotations
from typing import Dict, List
from server.models.event import GameEvent
from server.models.belief import Belief
from server.core.belief_store import BeliefStore


class WitnessEngine:
    """事件 → 信念 转化引擎。

    根据事件的 visibility 规则，将事件内容分发为对应 NPC 的信念。
    """

    def __init__(self, belief_stores: Dict[str, BeliefStore]):
        self._stores = belief_stores

    def process_event(self, event: GameEvent) -> List[str]:
        """处理一个事件，返回获得新信念的 NPC ID 列表。"""
        recipients = self._resolve_recipients(event)
        affected = []

        for npc_id in recipients:
            store = self._stores.get(npc_id)
            if store is None:
                continue
            belief = Belief(
                content=event.content,
                source="witnessed",
                confidence="high",
                acquired_at=dict(event.timestamp),
                about=self._extract_about(event),
            )
            if store.add(belief):
                affected.append(npc_id)

        if event.reasoning and event.actor in self._stores:
            reasoning_belief = Belief(
                content=event.reasoning,
                source="witnessed",
                confidence="high",
                acquired_at=dict(event.timestamp),
                about=self._extract_about(event),
            )
            self._stores[event.actor].add(reasoning_belief)

        return affected

    def _resolve_recipients(self, event: GameEvent) -> List[str]:
        if event.visibility == "public":
            return list(self._stores.keys())
        if event.visibility == "private":
            return [event.actor] if event.actor in self._stores else []
        return [npc_id for npc_id in event.witnesses if npc_id in self._stores]

    def _extract_about(self, event: GameEvent) -> List[str]:
        about = []
        if event.actor != "world":
            about.append(event.actor)
        if event.type == "world":
            about.append("world")
        return about if about else ["world"]
