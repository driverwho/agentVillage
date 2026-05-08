from typing import Dict, Any
from server.core.time_system import TimeSystem
from server.core.message_bus import MessageBus
from server.core.state_store import JsonStore
from server.models.player_state import PlayerState
from server.agents.farmer import FarmerAgent
from server.agents.bartender import BartenderAgent
from server.llm.token_budget import TokenBudget


class Orchestrator:
    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.time_system = TimeSystem()
        self.message_bus = MessageBus()
        self.store = JsonStore(base_path=f"data/users/{user_id}")
        self.npcs: Dict[str, Any] = {}
        self.player_state = PlayerState(name="玩家")
        self._init_npcs()

    def _init_npcs(self) -> None:
        self.npcs["farmer"] = FarmerAgent(
            memory_base=f"data/users/{self.user_id}/memory",
            budget=TokenBudget(daily_limit=5000),
        )
        self.npcs["bartender"] = BartenderAgent(
            memory_base=f"data/users/{self.user_id}/memory",
            budget=TokenBudget(daily_limit=5000),
        )

    def advance_time(self, minutes: int = 60) -> None:
        # 自动取消暂停以推进时间
        if self.time_system.is_paused:
            self.time_system.is_paused = False
        is_hour = self.time_system.tick(minutes)
        if is_hour:
            for npc in self.npcs.values():
                npc.on_hour_tick(self.time_system.game_time)
        self._auto_save()

    def _auto_save(self) -> None:
        self.store.save("world_state", {
            "game_time": self.time_system.game_time.to_dict(),
            "is_paused": self.time_system.is_paused,
        })
        self.store.save("player_state", self.player_state.__dict__)

    def get_world_state(self) -> dict:
        return {
            "game_time": self.time_system.game_time.to_dict(),
            "is_paused": self.time_system.is_paused,
            "npcs": {
                nid: {
                    "state": {
                        "health": n.state.health,
                        "hunger": n.state.hunger,
                        "fatigue": n.state.fatigue,
                        "mood": n.state.mood,
                    }
                }
                for nid, n in self.npcs.items()
            },
        }
