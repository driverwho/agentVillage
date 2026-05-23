import pytest
from server.tools.policy import (
    ToolPolicyPipeline,
    IdentityGate,
    StateGate,
    RelationshipGate,
    TimeGate,
    QuotaGate,
)
from server.tools.base_tool import NPCTool, ToolCategory, ToolResult, ToolParam
from server.models.npc_state import NPCState


# --- 假工具 ---

class _Farm(NPCTool):
    name = "farm"
    category = ToolCategory.PROFESSIONAL
    description = "耕作"
    params = []
    def execute(self, actor_id, params, context):
        return ToolResult(success=True)

class _Brew(NPCTool):
    name = "brew"
    category = ToolCategory.PROFESSIONAL
    description = "酿酒"
    params = []
    def execute(self, actor_id, params, context):
        return ToolResult(success=True)

class _Eat(NPCTool):
    name = "eat"
    category = ToolCategory.SURVIVAL
    description = "吃"
    params = []
    def execute(self, actor_id, params, context):
        return ToolResult(success=True)

class _Rest(NPCTool):
    name = "rest"
    category = ToolCategory.SURVIVAL
    description = "休息"
    params = []
    def execute(self, actor_id, params, context):
        return ToolResult(success=True)

class _Gossip(NPCTool):
    name = "gossip"
    category = ToolCategory.SOCIAL
    description = "八卦"
    params = [ToolParam(name="target", type="string", description="对象")]
    def execute(self, actor_id, params, context):
        return ToolResult(success=True)

class _Trade(NPCTool):
    name = "trade"
    category = ToolCategory.SOCIAL
    description = "交易"
    params = [ToolParam(name="target", type="string", description="对象")]
    def execute(self, actor_id, params, context):
        return ToolResult(success=True)


ALL_TOOLS = [_Farm(), _Brew(), _Eat(), _Rest(), _Gossip(), _Trade()]


# ============================================================
# 身份门
# ============================================================

def test_identity_gate_farmer_cannot_brew():
    gate = IdentityGate()
    ctx = {"actor_id": "farmer", "allowed_professional": ["farm"]}
    result, removed = gate.filter(ALL_TOOLS, ctx)
    names = [t.name for t in result]
    assert "farm" in names
    assert "brew" not in names
    assert "eat" in names
    assert "gossip" in names


def test_identity_gate_bartender_cannot_farm():
    gate = IdentityGate()
    ctx = {"actor_id": "bartender", "allowed_professional": ["brew"]}
    result, removed = gate.filter(ALL_TOOLS, ctx)
    names = [t.name for t in result]
    assert "brew" in names
    assert "farm" not in names


def test_identity_gate_preserves_non_professional():
    gate = IdentityGate()
    ctx = {"actor_id": "farmer", "allowed_professional": ["farm"]}
    result, removed = gate.filter(ALL_TOOLS, ctx)
    names = [t.name for t in result]
    assert "eat" in names
    assert "rest" in names
    assert "gossip" in names
    assert "trade" in names


# ============================================================
# 状态门
# ============================================================

def test_state_gate_high_fatigue_blocks_social():
    gate = StateGate()
    state = NPCState(fatigue=85)
    ctx = {"npc_state": state}
    result, _ = gate.filter(ALL_TOOLS, ctx)
    names = [t.name for t in result]
    assert "gossip" not in names
    assert "trade" not in names
    assert "eat" in names
    assert "rest" in names


def test_state_gate_normal_fatigue_allows_all():
    gate = StateGate()
    state = NPCState(fatigue=50)
    ctx = {"npc_state": state}
    result, _ = gate.filter(ALL_TOOLS, ctx)
    assert len(result) == len(ALL_TOOLS)


def test_state_gate_low_mood_blocks_professional():
    gate = StateGate()
    state = NPCState(mood=-1)
    ctx = {"npc_state": state}
    result, _ = gate.filter(ALL_TOOLS, ctx)
    names = [t.name for t in result]
    assert "farm" not in names
    assert "brew" not in names
    assert "eat" in names


# ============================================================
# 关系门
# ============================================================

def test_relationship_gate_low_trust_blocks_trade():
    gate = RelationshipGate()
    ctx = {"trust_level": 2}
    result, _ = gate.filter(ALL_TOOLS, ctx)
    names = [t.name for t in result]
    assert "trade" not in names
    assert "gossip" not in names
    assert "eat" in names


def test_relationship_gate_high_trust_allows_all():
    gate = RelationshipGate()
    ctx = {"trust_level": 8}
    result, _ = gate.filter(ALL_TOOLS, ctx)
    assert len(result) == len(ALL_TOOLS)


# ============================================================
# 时间门
# ============================================================

def test_time_gate_night_blocks_professional():
    gate = TimeGate()
    ctx = {"hour": 23}
    result, _ = gate.filter(ALL_TOOLS, ctx)
    names = [t.name for t in result]
    assert "farm" not in names
    assert "brew" not in names
    assert "eat" in names
    assert "rest" in names


def test_time_gate_daytime_allows_all():
    gate = TimeGate()
    ctx = {"hour": 10}
    result, _ = gate.filter(ALL_TOOLS, ctx)
    assert len(result) == len(ALL_TOOLS)


# ============================================================
# 配额门
# ============================================================

def test_quota_gate_exceeded_blocks_tool():
    gate = QuotaGate()
    ctx = {"daily_usage": {"gossip": 5}, "daily_limits": {"gossip": 3}}
    result, _ = gate.filter(ALL_TOOLS, ctx)
    names = [t.name for t in result]
    assert "gossip" not in names
    assert "trade" in names


def test_quota_gate_within_limit_allows():
    gate = QuotaGate()
    ctx = {"daily_usage": {"gossip": 1}, "daily_limits": {"gossip": 3}}
    result, _ = gate.filter(ALL_TOOLS, ctx)
    names = [t.name for t in result]
    assert "gossip" in names


# ============================================================
# 完整管道
# ============================================================

def test_full_pipeline_composition():
    pipeline = ToolPolicyPipeline([
        IdentityGate(),
        StateGate(),
        RelationshipGate(),
        TimeGate(),
        QuotaGate(),
    ])
    ctx = {
        "actor_id": "farmer",
        "allowed_professional": ["farm"],
        "npc_state": NPCState(fatigue=50, mood=50),
        "trust_level": 8,
        "hour": 10,
        "daily_usage": {},
        "daily_limits": {"gossip": 3},
    }
    result = pipeline.filter(ALL_TOOLS, ctx)
    names = [t.name for t in result]
    assert "farm" in names
    assert "brew" not in names
    assert "eat" in names
    assert "gossip" in names


def test_full_pipeline_multiple_gates_compound():
    pipeline = ToolPolicyPipeline([
        IdentityGate(),
        StateGate(),
        TimeGate(),
    ])
    ctx = {
        "actor_id": "farmer",
        "allowed_professional": ["farm"],
        "npc_state": NPCState(fatigue=90, mood=50),
        "hour": 23,
    }
    result = pipeline.filter(ALL_TOOLS, ctx)
    names = [t.name for t in result]
    assert "farm" not in names
    assert "gossip" not in names
    assert "eat" in names
    assert "rest" in names
