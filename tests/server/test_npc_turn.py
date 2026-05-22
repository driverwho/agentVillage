"""测试 NPCAgent 的工具感知 turn 流程（不调用真实 LLM）。"""
import pytest
from unittest.mock import AsyncMock, patch
from server.agents.base_agent import NPCAgent
from server.tools.registry import ToolRegistry
from server.tools.definitions import EatTool, FarmNPCTool, BrewTool, RestTool, MoveTool, GossipTool
from server.tools.policy import ToolPolicyPipeline
from server.tools.executor import ToolExecutor
from server.llm.token_budget import TokenBudget
from server.models.npc_state import NPCState


def _make_farmer_agent(registry: ToolRegistry) -> NPCAgent:
    background = {
        "id": "farmer",
        "name": "农夫",
        "daily_habits": "日出而作",
        "core_motivation": "耕作",
        "secret": "曾经是拳王",
        "speaking_style": "慢条斯理",
        "visibility": ["basic"],
        "tools": ["farm"],
    }
    budget = TokenBudget(daily_limit=10000)
    agent = NPCAgent(
        agent_id="farmer",
        background=background,
        memory_base="data/users/test/memory",
        budget=budget,
    )
    agent.tool_registry = registry
    agent.tool_executor = ToolExecutor(registry)
    agent.tool_pipeline = ToolPolicyPipeline()
    return agent


def _make_registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(EatTool())
    reg.register(FarmNPCTool())
    reg.register(BrewTool())
    reg.register(RestTool())
    reg.register(MoveTool())
    reg.register(GossipTool())
    return reg


def test_get_available_tools_filters_by_identity():
    """农夫只能看到 farm，看不到 brew"""
    reg = _make_registry()
    agent = _make_farmer_agent(reg)
    ctx = {
        "actor_id": "farmer",
        "allowed_professional": ["farm"],
        "npc_state": agent.state,
        "trust_level": 5,
        "hour": 10,
        "daily_usage": {},
        "daily_limits": {"gossip": 3},
    }
    available = agent.get_available_tools(ctx)
    names = [t.name for t in available]
    assert "farm" in names
    assert "brew" not in names
    assert "eat" in names


def test_get_available_tools_night_blocks_professional():
    """夜间农夫不能 farm"""
    reg = _make_registry()
    agent = _make_farmer_agent(reg)
    ctx = {
        "actor_id": "farmer",
        "allowed_professional": ["farm"],
        "npc_state": agent.state,
        "trust_level": 5,
        "hour": 23,
        "daily_usage": {},
        "daily_limits": {},
    }
    available = agent.get_available_tools(ctx)
    names = [t.name for t in available]
    assert "farm" not in names
    assert "eat" in names


def test_generate_tool_schemas():
    """agent 能为可用工具生成 function calling schemas"""
    reg = _make_registry()
    agent = _make_farmer_agent(reg)
    ctx = {
        "actor_id": "farmer",
        "allowed_professional": ["farm"],
        "npc_state": agent.state,
        "trust_level": 5,
        "hour": 10,
        "daily_usage": {},
        "daily_limits": {},
    }
    schemas = agent.generate_tool_schemas(ctx)
    names = [s["function"]["name"] for s in schemas]
    assert "farm" in names
    assert "eat" in names
    assert "brew" not in names


@pytest.mark.asyncio(loop_scope="function")
async def test_run_tool_turn_executes_tool():
    """完整的 tool turn: LLM 返回 tool_call → 执行 → 返回结果"""
    reg = _make_registry()
    agent = _make_farmer_agent(reg)
    agent.state.hunger = 30

    fake_llm_response = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": "call_001",
                    "type": "function",
                    "function": {"name": "eat", "arguments": "{}"},
                }],
            },
            "finish_reason": "tool_calls",
        }],
        "usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
    }

    with patch("server.llm.client.get_llm_client") as mock_get:
        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(return_value=fake_llm_response)
        mock_client.model = "test"
        mock_get.return_value = mock_client

        result = await agent.run_tool_turn(
            context={
                "npc_states": {"farmer": agent.state},
                "actor_id": "farmer",
                "allowed_professional": ["farm"],
                "trust_level": 5,
                "hour": 10,
                "daily_usage": {},
                "daily_limits": {},
            },
            messages=[{"role": "system", "content": "你是农夫"}],
        )

    assert result["tool_used"] == "eat"
    assert result["tool_result"]["success"] is True
    assert agent.state.hunger == 60


@pytest.mark.asyncio(loop_scope="function")
async def test_run_tool_turn_no_tool_call():
    """LLM 选择不调用工具（直接文本回复）→ 返回文本"""
    reg = _make_registry()
    agent = _make_farmer_agent(reg)

    fake_llm_response = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": "今天天气不错，适合干活。",
            },
            "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": 100, "completion_tokens": 20, "total_tokens": 120},
    }

    with patch("server.llm.client.get_llm_client") as mock_get:
        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(return_value=fake_llm_response)
        mock_client.model = "test"
        mock_get.return_value = mock_client

        result = await agent.run_tool_turn(
            context={
                "npc_states": {"farmer": agent.state},
                "actor_id": "farmer",
                "allowed_professional": ["farm"],
                "trust_level": 5,
                "hour": 10,
                "daily_usage": {},
                "daily_limits": {},
            },
            messages=[{"role": "system", "content": "你是农夫"}],
        )

    assert result["tool_used"] is None
    assert result["text_reply"] == "今天天气不错，适合干活。"


def test_build_policy_context_from_agent():
    """build_policy_context 从 agent 属性正确构建上下文"""
    from server.tools.setup import build_policy_context
    from server.models.game_time import GameTime

    reg = _make_registry()
    agent = _make_farmer_agent(reg)
    agent._allowed_professional = ["farm"]
    agent._daily_limits = {"gossip": 3}
    agent._daily_usage = {"gossip": 1}

    game_time = GameTime(day=1, hour=10, minute=0)
    ctx = build_policy_context(agent, game_time, trust_level=7.0)

    assert ctx["actor_id"] == "farmer"
    assert ctx["allowed_professional"] == ["farm"]
    assert ctx["hour"] == 10
    assert ctx["trust_level"] == 7.0
    assert ctx["daily_usage"] == {"gossip": 1}


# ============================================================
# activity_state + location 测试
# ============================================================

def test_agent_has_activity_state():
    reg = _make_registry()
    agent = _make_farmer_agent(reg)
    assert hasattr(agent, "activity_state")
    assert agent.activity_state.status == "idle"


def test_agent_has_location():
    reg = _make_registry()
    agent = _make_farmer_agent(reg)
    assert hasattr(agent, "location")
    assert agent.location == "home"


def test_agent_location_from_background():
    """如果 background 指定了 default_location，使用它"""
    background = {
        "id": "bartender",
        "name": "酒保",
        "daily_habits": "",
        "core_motivation": "",
        "secret": "",
        "speaking_style": "",
        "visibility": ["basic"],
        "tools": ["brew"],
        "default_location": "tavern",
    }
    budget = TokenBudget(daily_limit=10000)
    agent = NPCAgent(
        agent_id="bartender",
        background=background,
        memory_base="data/users/test/memory",
        budget=budget,
    )
    assert agent.location == "tavern"
