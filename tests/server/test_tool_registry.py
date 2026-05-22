import pytest
from server.tools.registry import ToolRegistry
from server.tools.base_tool import NPCTool, ToolCategory, ToolParam, ToolResult


class _FakeFarm(NPCTool):
    name = "farm"
    category = ToolCategory.PROFESSIONAL
    description = "耕作"
    params = []

    def execute(self, actor_id, params, context):
        return ToolResult(success=True, message="耕作完成")


class _FakeEat(NPCTool):
    name = "eat"
    category = ToolCategory.SURVIVAL
    description = "进食"
    params = []

    def execute(self, actor_id, params, context):
        return ToolResult(success=True, message="吃饱了")


class _FakeGossip(NPCTool):
    name = "gossip"
    category = ToolCategory.SOCIAL
    description = "八卦"
    params = [ToolParam(name="target", type="string", description="对象")]

    def execute(self, actor_id, params, context):
        return ToolResult(success=True, message="传播了消息")


def test_register_and_get():
    reg = ToolRegistry()
    reg.register(_FakeFarm())
    reg.register(_FakeEat())
    assert reg.get("farm") is not None
    assert reg.get("eat") is not None
    assert reg.get("nonexist") is None


def test_get_all_returns_all_registered():
    reg = ToolRegistry()
    reg.register(_FakeFarm())
    reg.register(_FakeEat())
    reg.register(_FakeGossip())
    assert len(reg.get_all()) == 3


def test_get_by_category():
    reg = ToolRegistry()
    reg.register(_FakeFarm())
    reg.register(_FakeEat())
    reg.register(_FakeGossip())
    survival = reg.get_by_category(ToolCategory.SURVIVAL)
    assert len(survival) == 1
    assert survival[0].name == "eat"


def test_generate_schemas():
    reg = ToolRegistry()
    reg.register(_FakeFarm())
    reg.register(_FakeEat())
    schemas = reg.generate_schemas(["farm", "eat"])
    assert len(schemas) == 2
    assert schemas[0]["function"]["name"] == "farm"
    assert schemas[1]["function"]["name"] == "eat"


def test_generate_schemas_subset():
    """只为指定工具名列表生成 schema"""
    reg = ToolRegistry()
    reg.register(_FakeFarm())
    reg.register(_FakeEat())
    reg.register(_FakeGossip())
    schemas = reg.generate_schemas(["eat"])
    assert len(schemas) == 1
    assert schemas[0]["function"]["name"] == "eat"


def test_duplicate_register_raises():
    reg = ToolRegistry()
    reg.register(_FakeFarm())
    with pytest.raises(ValueError, match="已注册"):
        reg.register(_FakeFarm())
