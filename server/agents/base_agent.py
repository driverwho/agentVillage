from typing import List
from server.models.npc_state import NPCState
from server.models.messages import DialogueTurn
from server.memory.memory_manager import MemoryManager
from server.llm.token_budget import TokenBudget


class NPCAgent:
    def __init__(self, agent_id: str, background: dict, memory_base: str, budget: TokenBudget):
        self.agent_id = agent_id
        self.background = background

        # 从 background 派生 identity（向后兼容 ContextBuilder）
        self.identity = {
            "id": background.get("id", agent_id),
            "name": background.get("name", agent_id),
            "daily_habits": background.get("daily_habits", ""),
            "core_motivation": background.get("core_motivation", ""),
            "secret": background.get("secret", ""),
            "speaking_style": background.get("speaking_style", ""),
            "visibility": tuple(background.get("visibility", ["basic"])),
        }

        self.state = NPCState()
        self.memory = MemoryManager(memory_base, agent_id)
        self.budget = budget
        self.visibility = list(self.identity.get("visibility", ("basic",)))
        self.dialogue_history: List[DialogueTurn] = []

        self.memory.seed_if_empty(background)

    def get_visible_state(self, player_state) -> dict:
        return player_state.get_visible_state(self.visibility)

    def can_interact(self, current_time) -> bool:
        hour = current_time.hour
        if hour >= 22 or hour < 6:
            return False
        return True

    def on_hour_tick(self, game_time) -> None:
        self.state.hunger = max(0, self.state.hunger - 5)
        self.state.fatigue = min(100, self.state.fatigue + 5)
        if game_time.hour == 0:
            self.budget.reset()
