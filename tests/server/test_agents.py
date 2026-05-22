from server.agents.farmer import FarmerAgent
from server.agents.bartender import BartenderAgent
from server.llm.token_budget import TokenBudget


def _minimal_bg(npc_id: str) -> dict:
    return {"id": npc_id, "name": npc_id, "daily_habits": "", "core_motivation": "",
            "secret": "", "speaking_style": ""}


def test_farmer_init():
    agent = FarmerAgent(_minimal_bg("farmer"), "data/test_memory", TokenBudget(daily_limit=1000))
    assert agent.agent_id == "farmer"
    assert "basic" in agent.visibility


def test_bartender_visibility():
    bg = _minimal_bg("bartender")
    bg["visibility"] = ["basic", "social"]
    agent = BartenderAgent(bg, "data/test_memory", TokenBudget(daily_limit=1000))
    assert "basic" in agent.visibility
    assert "social" in agent.visibility


def test_farmer_tick():
    from server.models.game_time import GameTime
    agent = FarmerAgent(_minimal_bg("farmer"), "data/test_memory", TokenBudget(daily_limit=1000))
    initial_hunger = agent.state.hunger
    agent.on_hour_tick(GameTime(day=1, hour=12, minute=0))
    assert agent.state.hunger < initial_hunger
