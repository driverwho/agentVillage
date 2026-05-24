from __future__ import annotations
from typing import Dict, Optional
from server.models.belief import Belief
from server.core.belief_store import BeliefStore


class BeliefPropagator:
    """对话中的信念传播。

    对话结束后调用，将摘要内容转化为参与者的信念。
    """

    def __init__(self, belief_stores: Dict[str, BeliefStore]):
        self._stores = belief_stores

    def propagate_from_dialogue(
        self,
        speaker_id: str,
        listener_id: str,
        summary: str,
        game_time: Dict[str, int],
    ) -> None:
        """对话摘要 → 信念传播。

        speaker 获得 witnessed/high 信念（自己经历的对话）
        listener 获得 told_by:speaker/medium 信念
        """
        if speaker_id in self._stores:
            speaker_belief = Belief(
                content=summary,
                source="witnessed",
                confidence="high",
                acquired_at=dict(game_time),
                about=self._extract_about(speaker_id, listener_id),
            )
            self._stores[speaker_id].add(speaker_belief)

        if listener_id in self._stores:
            listener_belief = Belief(
                content=summary,
                source=f"told_by:{speaker_id}",
                confidence="medium",
                acquired_at=dict(game_time),
                about=self._extract_about(speaker_id, listener_id),
            )
            self._stores[listener_id].add(listener_belief)

    def share_belief(
        self,
        from_npc: str,
        to_npc: str,
        belief: Belief,
        new_content: Optional[str] = None,
        game_time: Optional[Dict[str, int]] = None,
    ) -> bool:
        """NPC 主动将一条信念分享给另一个 NPC。

        confidence 降一级，source 变为 told_by:from_npc。
        """
        store = self._stores.get(to_npc)
        if store is None:
            return False
        content = new_content or belief.content
        propagated = belief.propagate(teller_id=from_npc, new_content=content)
        if game_time:
            propagated.acquired_at = dict(game_time)
        return store.add(propagated)

    def _extract_about(self, speaker_id: str, listener_id: str) -> list:
        about = []
        if speaker_id != "world":
            about.append(speaker_id)
        if listener_id != "world":
            about.append(listener_id)
        return about or ["world"]
