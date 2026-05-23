from __future__ import annotations
from typing import Any, Dict, Tuple
from server.hooks.base import Hook
from server.models.game_time import GameTime
from server.core.location_registry import LocationRegistry


class InteractionCounter:
    def __init__(self):
        self._counts: Dict[Tuple, int] = {}

    def get_today_count(self, pair_key: Tuple[str, str], day: int) -> int:
        return self._counts.get((pair_key, day), 0)

    def increment(self, pair_key: Tuple[str, str], day: int) -> None:
        key = (pair_key, day)
        self._counts[key] = self._counts.get(key, 0) + 1


def should_interact(initiator, target, game_time: GameTime,
                    counter: InteractionCounter) -> bool:
    relationships = initiator.background.get("relationships", {})
    target_id = target.id if hasattr(target, 'id') else target.agent_id
    rel = relationships.get(target_id)
    if not rel:
        return False
    if not isinstance(rel, dict):
        return False
    if rel.get("trust_level", 0) < 4:
        return False
    initiator_id = initiator.id if hasattr(initiator, 'id') else initiator.agent_id
    pair_key = tuple(sorted([initiator_id, target_id]))
    if counter.get_today_count(pair_key, game_time.day) >= 2:
        return False
    if target.activity_state.status != "idle":
        return False
    return True


class InteractionHook(Hook):
    event = "post_move"

    def __init__(self, npc_registry: dict, location_registry: LocationRegistry,
                 interaction_runner):
        self.npc_registry = npc_registry
        self.location_registry = location_registry
        self.interaction_runner = interaction_runner
        self.counter = InteractionCounter()

    async def execute(self, context: Dict[str, Any]) -> None:
        actor_id = context["actor_id"]
        location = context["location"]
        game_time = context["game_time"]

        colocated_ids = self.location_registry.get_npcs_at(location) - {actor_id}
        initiator = self.npc_registry[actor_id]

        for target_id in colocated_ids:
            target = self.npc_registry.get(target_id)
            if not target:
                continue
            if should_interact(initiator, target, game_time, self.counter):
                await self.interaction_runner.run_conversation(
                    initiator=initiator,
                    target=target,
                    location=location,
                    game_time=game_time,
                )
                pair_key = tuple(sorted([actor_id, target_id]))
                self.counter.increment(pair_key, game_time.day)
