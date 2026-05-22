from server.tools.base_tool import NPCTool, ToolCategory, ToolParam


def test_npc_tool_has_required_fields():
    """NPCTool 子类必须声明 name/category/description/params"""
    class DummyTool(NPCTool):
        name = "dummy"
        category = ToolCategory.SURVIVAL
        description = "测试工具"
        params = [ToolParam(name="target", type="string", description="目标")]

        def execute(self, actor_id, params, context):
            return {"success": True}

    tool = DummyTool()
    assert tool.name == "dummy"
    assert tool.category == ToolCategory.SURVIVAL
    assert len(tool.params) == 1


def test_npc_tool_to_function_schema():
    """NPCTool 能生成 OpenAI function calling schema"""
    class EatTool(NPCTool):
        name = "eat"
        category = ToolCategory.SURVIVAL
        description = "进食以恢复饱食度"
        params = []

        def execute(self, actor_id, params, context):
            return {"success": True, "hunger_restored": 30}

    schema = EatTool().to_function_schema()
    assert schema["type"] == "function"
    assert schema["function"]["name"] == "eat"
    assert schema["function"]["description"] == "进食以恢复饱食度"
    assert schema["function"]["parameters"]["type"] == "object"


def test_npc_tool_with_params_schema():
    """带参数的工具生成正确的 properties"""
    class GossipTool(NPCTool):
        name = "gossip"
        category = ToolCategory.SOCIAL
        description = "向他人传播消息"
        params = [
            ToolParam(name="target", type="string", description="传播对象 NPC ID"),
            ToolParam(name="content", type="string", description="消息内容"),
        ]

        def execute(self, actor_id, params, context):
            return {"success": True}

    schema = GossipTool().to_function_schema()
    props = schema["function"]["parameters"]["properties"]
    assert "target" in props
    assert props["target"]["type"] == "string"
    assert "content" in props
    required = schema["function"]["parameters"]["required"]
    assert "target" in required
    assert "content" in required


# ============================================================
# 工具定义测试
# ============================================================

from server.tools.definitions import (
    EatTool, SleepTool, RestTool, MoveTool,
    FarmNPCTool, BrewTool, PatrolTool, DivineTool, PaintTool,
    GossipTool, TradeTool,
)
from server.tools.base_tool import ToolResult


def _make_state(health=100, hunger=100, fatigue=0, mood=50):
    from server.models.npc_state import NPCState
    return NPCState(health=health, hunger=hunger, fatigue=fatigue, mood=mood)


def test_eat_tool_restores_hunger():
    tool = EatTool()
    ctx = {"npc_states": {"farmer": _make_state(hunger=30)}}
    result = tool.execute("farmer", {}, ctx)
    assert result.success is True
    assert result.state_changes["hunger"] == 60


def test_eat_tool_caps_at_100():
    tool = EatTool()
    ctx = {"npc_states": {"farmer": _make_state(hunger=90)}}
    result = tool.execute("farmer", {}, ctx)
    assert result.state_changes["hunger"] == 100


def test_sleep_tool_resets_fatigue():
    tool = SleepTool()
    ctx = {"npc_states": {"farmer": _make_state(fatigue=80)}}
    result = tool.execute("farmer", {}, ctx)
    assert result.success is True
    assert result.state_changes["fatigue"] == 0


def test_rest_tool_reduces_fatigue():
    tool = RestTool()
    ctx = {"npc_states": {"farmer": _make_state(fatigue=60)}}
    result = tool.execute("farmer", {}, ctx)
    assert result.state_changes["fatigue"] == 40


def test_move_tool_changes_location():
    tool = MoveTool()
    ctx = {"npc_states": {"farmer": _make_state()}, "locations": {"farmer": "field"}}
    result = tool.execute("farmer", {"destination": "tavern"}, ctx)
    assert result.success is True
    assert result.state_changes["location"] == "tavern"


def test_farm_npc_tool_category():
    tool = FarmNPCTool()
    assert tool.category == ToolCategory.PROFESSIONAL
    assert tool.name == "farm"


def test_brew_tool_category():
    tool = BrewTool()
    assert tool.category == ToolCategory.PROFESSIONAL
    assert tool.name == "brew"


def test_gossip_tool_requires_target_and_content():
    tool = GossipTool()
    assert len(tool.params) == 2
    param_names = [p.name for p in tool.params]
    assert "target" in param_names
    assert "content" in param_names


def test_trade_tool_params():
    tool = TradeTool()
    param_names = [p.name for p in tool.params]
    assert "target" in param_names
    assert "item" in param_names
    assert "action" in param_names


def test_all_tools_generate_valid_schema():
    """所有工具都能生成合法 schema"""
    tools = [
        EatTool(), SleepTool(), RestTool(), MoveTool(),
        FarmNPCTool(), BrewTool(), PatrolTool(), DivineTool(), PaintTool(),
        GossipTool(), TradeTool(),
    ]
    for tool in tools:
        schema = tool.to_function_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == tool.name
