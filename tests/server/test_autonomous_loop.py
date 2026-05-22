"""NPC 自主活动循环集成测试。"""
import pytest
from unittest.mock import AsyncMock, patch
from server.tools.setup import build_autonomous_context, build_policy_context
from server.core.activity_manager import ActivityState, ActivityManager
from server.models.game_time import GameTime
from server.models.npc_state import NPCState


def _make_test_agent():
    """创建一个用于测试的 farmer agent"""
    from server.agents.base_agent import NPCAgent
    from server.tools.registry import ToolRegistry
    from server.tools.definitions import EatTool, FarmNPCTool, RestTool, SleepTool, MoveTool
    from server.tools.policy import ToolPolicyPipeline
    from server.tools.executor import ToolExecutor
    from server.llm.token_budget import TokenBudget

    reg = ToolRegistry()
    for cls in [EatTool, FarmNPCTool, RestTool, SleepTool, MoveTool]:
        reg.register(cls())

    background = {
        "id": "farmer",
        "name": "农夫",
        "daily_habits": "日出而作",
        "core_motivation": "耕作",
        "secret": "曾经是拳王",
        "speaking_style": "慢条斯理",
        "visibility": ["basic"],
        "tools": ["farm"],
        "default_location": "home",
    }
    agent = NPCAgent(
        agent_id="farmer",
        background=background,
        memory_base="data/users/test/memory",
        budget=TokenBudget(daily_limit=10000),
    )
    agent.tool_registry = reg
    agent.tool_pipeline = ToolPolicyPipeline()
    agent.tool_executor = ToolExecutor(reg)
    agent._allowed_professional = ["farm"]
    agent._daily_limits = {}
    agent._daily_usage = {}
    return agent


# ============================================================
# build_autonomous_context 测试
# ============================================================

def test_build_autonomous_context_first_decision():
    """第一次决策（无上一个活动）"""
    agent = _make_test_agent()
    game_time = GameTime(day=1, hour=6, minute=0)
    ctx = build_autonomous_context(agent, game_time)
    assert "Day 1" in ctx
    assert "6:00" in ctx
    assert "家" in ctx
    assert "刚起床" in ctx


def test_build_autonomous_context_after_activity():
    """完成活动后的上下文"""
    agent = _make_test_agent()
    agent.activity_state.idle_reason = "完成了farm"
    agent.location = "field"
    game_time = GameTime(day=1, hour=12, minute=0)
    ctx = build_autonomous_context(agent, game_time)
    assert "Day 1" in ctx
    assert "12:00" in ctx
    assert "田地" in ctx
    assert "farm" in ctx


def test_build_autonomous_context_after_interrupt():
    """中断后的上下文包含中断原因"""
    agent = _make_test_agent()
    agent.activity_state.idle_reason = "因为饥饿难耐中断了farm"
    agent.location = "field"
    game_time = GameTime(day=1, hour=10, minute=0)
    ctx = build_autonomous_context(agent, game_time)
    assert "饥饿" in ctx
    assert "farm" in ctx


# ============================================================
# ActivityManager 集成测试
# ============================================================

def test_tick_completes_activity():
    """活动到时间后 NPC 进入 idle"""
    agent = _make_test_agent()
    mgr = ActivityManager()
    game_time = GameTime(day=1, hour=8, minute=0)
    mgr.transition_to_active(agent.activity_state, "farm", 4, game_time)
    assert agent.activity_state.status == "active"

    later = GameTime(day=1, hour=12, minute=0)
    completed = mgr.check_completion(agent.activity_state, later)
    assert completed is True
    mgr.transition_to_idle(agent.activity_state, "完成了farm")
    assert agent.activity_state.status == "idle"
    assert agent.activity_state.idle_reason == "完成了farm"


def test_tick_interrupts_on_hunger():
    """hunger < 20 中断活动"""
    agent = _make_test_agent()
    mgr = ActivityManager()
    game_time = GameTime(day=1, hour=8, minute=0)
    mgr.transition_to_active(agent.activity_state, "farm", 4, game_time)
    agent.state.hunger = 15

    reason = mgr.check_interrupts(agent.activity_state, agent.state)
    assert reason is not None
    mgr.transition_to_idle(agent.activity_state, f"因为{reason}中断了farm")
    assert "饥饿" in agent.activity_state.idle_reason


def test_tick_decision_point_interrupts():
    """决策点到达时中断 ACTIVE NPC"""
    agent = _make_test_agent()
    mgr = ActivityManager()
    game_time = GameTime(day=1, hour=8, minute=0)
    mgr.transition_to_active(agent.activity_state, "farm", 6, game_time)

    assert mgr.is_decision_point(12) is True
    mgr.transition_to_idle(agent.activity_state, "到了12:00决策时间")
    assert agent.activity_state.status == "idle"


@pytest.mark.asyncio(loop_scope="function")
async def test_autonomous_turn_sets_active():
    """自主 turn 后 NPC 从 idle 变为 active"""
    agent = _make_test_agent()
    assert agent.activity_state.status == "idle"

    fake_llm_response = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": "call_auto_1",
                    "type": "function",
                    "function": {"name": "farm", "arguments": "{}"},
                }],
            },
            "finish_reason": "tool_calls",
        }],
        "usage": {"prompt_tokens": 200, "completion_tokens": 30, "total_tokens": 230},
    }

    with patch("server.llm.client.get_llm_client") as mock_get:
        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(return_value=fake_llm_response)
        mock_client.model = "test"
        mock_get.return_value = mock_client

        game_time = GameTime(day=1, hour=8, minute=0)
        policy_ctx = build_policy_context(agent, game_time)
        policy_ctx["npc_states"] = {"farmer": agent.state}

        result = await agent.run_tool_turn(
            context=policy_ctx,
            messages=[{"role": "system", "content": "你是农夫"},
                      {"role": "user", "content": build_autonomous_context(agent, game_time)}],
        )

    assert result["tool_used"] == "farm"

    mgr = ActivityManager()
    mgr.transition_to_active(agent.activity_state, "farm", 4, game_time)
    assert agent.activity_state.status == "active"
    assert agent.activity_state.end_hour == 12


@pytest.mark.asyncio(loop_scope="function")
async def test_autonomous_turn_no_tool_defaults_to_idle_1h():
    """LLM 返回纯文本（未调用工具）→ 默认闲逛 1 小时"""
    agent = _make_test_agent()

    fake_llm_response = {
        "choices": [{
            "message": {"role": "assistant", "content": "今天先歇会儿吧。"},
            "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": 200, "completion_tokens": 20, "total_tokens": 220},
    }

    with patch("server.llm.client.get_llm_client") as mock_get:
        mock_client = AsyncMock()
        mock_client.chat = AsyncMock(return_value=fake_llm_response)
        mock_client.model = "test"
        mock_get.return_value = mock_client

        game_time = GameTime(day=1, hour=10, minute=0)
        policy_ctx = build_policy_context(agent, game_time)
        policy_ctx["npc_states"] = {"farmer": agent.state}

        result = await agent.run_tool_turn(
            context=policy_ctx,
            messages=[{"role": "system", "content": "你是农夫"},
                      {"role": "user", "content": build_autonomous_context(agent, game_time)}],
        )

    assert result["tool_used"] is None

    mgr = ActivityManager()
    mgr.transition_to_active(agent.activity_state, "_idle_wander", 1, game_time)
    assert agent.activity_state.status == "active"
    assert agent.activity_state.end_hour == 11
