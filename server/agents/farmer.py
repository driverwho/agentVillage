from server.agents.base_agent import NPCAgent
from server.llm.token_budget import TokenBudget


class FarmerAgent(NPCAgent):
    def __init__(self, background: dict, memory_base: str, budget: TokenBudget):
        super().__init__("farmer", background, memory_base, budget)
