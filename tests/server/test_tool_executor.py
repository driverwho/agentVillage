import pytest
from server.tools.executor import ToolExecutor
from server.tools.registry import ToolRegistry
from server.tools.base_tool import NPCTool, ToolCategory, ToolResult, ToolParam
from server.models.npc_state import NPCState


# --- 假工具 ---

class _FakeEat(NPCTool):
    name = "eat"
    category = ToolCategory.SURVIVAL
    description = "吃"
    params = []
    def execute(self, actor_id, params, context):
        state = context["npc_states"][actor_id]
        state.hunger = min(100, state.hunger + 30)
        return ToolResult(success=True, message="吃饱了", state_changes={"hunger": state.hunger})


class _FakeMove(NPCTool):
    name = "move"
    category = ToolCategory.SURVIVAL
    description = "移动"
    params = [ToolParam(name="destination", type="string", description="目的地")]
    def execute(self, actor_id, params, context):
        return ToolResult(success=True, message=f"去了{params['destination']}", state_changes={"location": params["destination"]})


class _FakeBroken(NPCTool):
    name = "broken"
    category = ToolCategory.SURVIVAL
    description = "总是失败的工具"
    params = []
    def execute(self, actor_id, params, context):
        raise RuntimeError("工具执行崩溃")


def _make_registry():
    reg = ToolRegistry()
    reg.register(_FakeEat())
    reg.register(_FakeMove())
    reg.register(_FakeBroken())
    return reg


def _make_context(hunger=50):
    return {
        "npc_states": {"farmer": NPCState(hunger=hunger)},
        "locations": {"farmer": "field"},
    }


def test_execute_single_tool_call():
    executor = ToolExecutor(_make_registry())
    tool_calls = [{"call_id": "c1", "name": "eat", "arguments": {}}]
    results = executor.execute_tool_calls("farmer", tool_calls, _make_context())
    assert len(results) == 1
    assert results[0]["success"] is True
    assert results[0]["name"] == "eat"
    assert "hunger" in results[0]["state_changes"]


def test_execute_tool_with_params():
    executor = ToolExecutor(_make_registry())
    tool_calls = [{"call_id": "c2", "name": "move", "arguments": {"destination": "tavern"}}]
    results = executor.execute_tool_calls("farmer", tool_calls, _make_context())
    assert results[0]["success"] is True
    assert results[0]["state_changes"]["location"] == "tavern"


def test_execute_unknown_tool_returns_error():
    executor = ToolExecutor(_make_registry())
    tool_calls = [{"call_id": "c3", "name": "fly_to_moon", "arguments": {}}]
    results = executor.execute_tool_calls("farmer", tool_calls, _make_context())
    assert results[0]["success"] is False
    assert "未知工具" in results[0]["message"]


def test_execute_tool_exception_returns_error():
    executor = ToolExecutor(_make_registry())
    tool_calls = [{"call_id": "c4", "name": "broken", "arguments": {}}]
    results = executor.execute_tool_calls("farmer", tool_calls, _make_context())
    assert results[0]["success"] is False
    assert "执行失败" in results[0]["message"]


def test_execute_multiple_tool_calls():
    executor = ToolExecutor(_make_registry())
    tool_calls = [
        {"call_id": "c5", "name": "eat", "arguments": {}},
        {"call_id": "c6", "name": "move", "arguments": {"destination": "tavern"}},
    ]
    results = executor.execute_tool_calls("farmer", tool_calls, _make_context())
    assert len(results) == 2
    assert results[0]["name"] == "eat"
    assert results[1]["name"] == "move"


def test_build_tool_result_messages():
    executor = ToolExecutor(_make_registry())
    results = [
        {"call_id": "c1", "name": "eat", "success": True, "message": "吃饱了", "state_changes": {"hunger": 80}},
    ]
    messages = executor.build_result_messages(results)
    assert len(messages) == 1
    assert messages[0]["role"] == "tool"
    assert messages[0]["tool_call_id"] == "c1"
    assert "吃饱了" in messages[0]["content"]


def test_execute_respects_max_calls_limit():
    executor = ToolExecutor(_make_registry(), max_calls_per_turn=2)
    tool_calls = [
        {"call_id": "c1", "name": "eat", "arguments": {}},
        {"call_id": "c2", "name": "eat", "arguments": {}},
        {"call_id": "c3", "name": "eat", "arguments": {}},
    ]
    results = executor.execute_tool_calls("farmer", tool_calls, _make_context(hunger=10))
    assert len(results) == 2
