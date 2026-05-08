from typing import List, Dict, Optional
from server.models.npc_state import NPCState
from server.models.messages import DialogueTurn
from server.memory.memory_manager import MemoryManager
from server.llm.token_budget import TokenBudget, BudgetStatus


class NPCAgent:
    def __init__(self, agent_id: str, identity: dict, memory_base: str, budget: TokenBudget):
        self.agent_id = agent_id
        self.identity = identity
        self.state = NPCState()
        self.memory = MemoryManager(memory_base, agent_id)
        self.budget = budget
        self.visibility = identity.get("visibility", ["basic"])
        self.dialogue_history: List[DialogueTurn] = []

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
