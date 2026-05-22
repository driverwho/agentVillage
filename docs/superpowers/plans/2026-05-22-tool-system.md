# NPC 工具系统实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 将所有 NPC 行为统一为工具调用，由 LLM function calling 全权决策，五层策略管道约束边界。

**架构：** NPC 每次 turn 经历"工具过滤 → schema 注入 → LLM 决策 → 工具执行 → 结果返回"管道。工具定义为声明式 dataclass，策略管道为可组合的过滤链，LLM Client 扩展 function calling 支持。

**技术栈：** Python 3.11+ / dataclasses / DeepSeek API (OpenAI-compatible function calling) / pytest

---

## 范围

**包含：**
- 工具基类重构 + 所有一次性工具定义（社交/职业/生存）
- 工具注册表 + function calling schema 自动生成
- 五层策略管道（身份门/状态门/关系门/时间门/配额门）
- LLM Client 扩展 function calling 参数
- NPC Turn 执行引擎（过滤 → 调用 → 执行 → 返回）
- 与现有 `NPCAgent` + `routes.py` 集成

**不包含（独立计划）：**
- `DialogueSession` 生命周期（speak 建立持续会话）
- NPCHarness 行为模式抽象
- 叙事引擎三层 (L1/L2/L3) 事件写入
- NPC 间自主交互调度

---

## 文件结构

| 操作 | 文件路径 | 职责 |
|------|---------|------|
| 创建 | `server/tools/registry.py` | 工具注册表 + schema 生成 |
| 创建 | `server/tools/definitions.py` | 所有工具的声明式定义 |
| 创建 | `server/tools/policy.py` | 五层策略管道 |
| 创建 | `server/tools/executor.py` | 工具执行引擎（解析 LLM 响应 → 调用工具） |
| 修改 | `server/tools/base_tool.py` | 重构基类，支持 NPC 工具 |
| 修改 | `server/llm/client.py` | 添加 function calling 参数支持 |
| 修改 | `server/agents/base_agent.py` | NPCAgent 集成工具系统 |
| 修改 | `server/api/routes.py` | 新增 NPC turn 端点 |
| 创建 | `tests/server/test_tool_registry.py` | 注册表 + schema 测试 |
| 创建 | `tests/server/test_tool_policy.py` | 策略管道测试 |
| 创建 | `tests/server/test_tool_executor.py` | 执行引擎测试 |
| 创建 | `tests/server/test_tool_definitions.py` | 工具定义测试 |

---

## 任务 1：重构工具基类

**文件：**
- 修改：`server/tools/base_tool.py`
- 测试：`tests/server/test_tool_definitions.py`

- [ ] **步骤 1：编写失败的测试**

```python
# tests/server/test_tool_definitions.py
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
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd d:/work_ai/agentVillage && python -m pytest tests/server/test_tool_definitions.py -v`
预期：FAIL，ImportError — `NPCTool`, `ToolCategory`, `ToolParam` 未定义

- [ ] **步骤 3：实现重构后的基类**

```python
# server/tools/base_tool.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Tuple


class ToolCategory(Enum):
    SOCIAL = "social"
    PROFESSIONAL = "professional"
    SURVIVAL = "survival"


@dataclass
class ToolParam:
    name: str
    type: str  # "string" | "integer" | "boolean"
    description: str
    required: bool = True
    enum: List[str] | None = None


@dataclass
class ToolResult:
    success: bool
    message: str = ""
    state_changes: Dict[str, Any] = field(default_factory=dict)
    broadcast: bool = False  # 是否需要广播给其他 NPC


class NPCTool(ABC):
    """NPC 工具基类。所有 NPC 行为工具继承此类。"""

    name: str
    category: ToolCategory
    description: str
    params: List[ToolParam] = []

    @abstractmethod
    def execute(self, actor_id: str, params: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        """执行工具。

        Args:
            actor_id: 执行者 NPC ID
            params: LLM 传入的参数
            context: 运行时上下文 (game_time, npc_states, etc.)
        """
        ...

    def to_function_schema(self) -> Dict[str, Any]:
        """生成 OpenAI function calling schema。"""
        properties = {}
        required = []
        for p in self.params:
            prop: Dict[str, Any] = {"type": p.type, "description": p.description}
            if p.enum:
                prop["enum"] = p.enum
            properties[p.name] = prop
            if p.required:
                required.append(p.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }


# 保留旧接口兼容（玩家工具）
class Tool(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def check_preconditions(self, player_state, npc_state=None) -> Tuple[bool, str]: ...

    @abstractmethod
    def execute(self, player_state, npc_state=None) -> Dict[str, Any]: ...
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd d:/work_ai/agentVillage && python -m pytest tests/server/test_tool_definitions.py -v`
预期：3 tests PASS

- [ ] **步骤 5：Commit**

```bash
git add server/tools/base_tool.py tests/server/test_tool_definitions.py
git commit -m "feat(tools): 重构工具基类，支持 NPC 工具 + function calling schema 生成"
```

---

## 任务 2：工具注册表

**文件：**
- 创建：`server/tools/registry.py`
- 测试：`tests/server/test_tool_registry.py`

- [ ] **步骤 1：编写失败的测试**

```python
# tests/server/test_tool_registry.py
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
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd d:/work_ai/agentVillage && python -m pytest tests/server/test_tool_registry.py -v`
预期：FAIL，ImportError — `ToolRegistry` 未定义

- [ ] **步骤 3：实现注册表**

```python
# server/tools/registry.py
from typing import Dict, List, Optional

from server.tools.base_tool import NPCTool, ToolCategory


class ToolRegistry:
    """工具注册表。管理所有已注册的 NPC 工具，生成 function calling schema。"""

    def __init__(self):
        self._tools: Dict[str, NPCTool] = {}

    def register(self, tool: NPCTool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"工具 '{tool.name}' 已注册")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[NPCTool]:
        return self._tools.get(name)

    def get_all(self) -> List[NPCTool]:
        return list(self._tools.values())

    def get_by_category(self, category: ToolCategory) -> List[NPCTool]:
        return [t for t in self._tools.values() if t.category == category]

    def generate_schemas(self, tool_names: List[str]) -> List[dict]:
        """为指定工具名列表生成 OpenAI function calling schemas。"""
        schemas = []
        for name in tool_names:
            tool = self._tools.get(name)
            if tool:
                schemas.append(tool.to_function_schema())
        return schemas
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd d:/work_ai/agentVillage && python -m pytest tests/server/test_tool_registry.py -v`
预期：6 tests PASS

- [ ] **步骤 5：Commit**

```bash
git add server/tools/registry.py tests/server/test_tool_registry.py
git commit -m "feat(tools): 添加工具注册表，支持按类别查询和 schema 批量生成"
```

---

## 任务 3：工具定义（所有一次性工具）

**文件：**
- 创建：`server/tools/definitions.py`
- 追加测试：`tests/server/test_tool_definitions.py`

- [ ] **步骤 1：编写失败的测试**

在 `tests/server/test_tool_definitions.py` 末尾追加：

```python
from server.tools.definitions import (
    EatTool, SleepTool, RestTool, MoveTool,
    FarmNPCTool, BrewTool, PatrolTool, DivineTool, PaintTool,
    GossipTool, TradeTool,
)
from server.tools.base_tool import ToolCategory, ToolResult


def test_eat_tool_restores_hunger():
    tool = EatTool()
    ctx = {"npc_states": {"farmer": _make_state(hunger=30)}}
    result = tool.execute("farmer", {}, ctx)
    assert result.success is True
    assert result.state_changes["hunger"] == 60  # +30


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
    assert result.state_changes["fatigue"] == 40  # -20


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
    """所有工具都能生成合法 schema（不抛异常）"""
    tools = [
        EatTool(), SleepTool(), RestTool(), MoveTool(),
        FarmNPCTool(), BrewTool(), PatrolTool(), DivineTool(), PaintTool(),
        GossipTool(), TradeTool(),
    ]
    for tool in tools:
        schema = tool.to_function_schema()
        assert schema["type"] == "function"
        assert schema["function"]["name"] == tool.name


# --- 辅助 ---

def _make_state(health=100, hunger=100, fatigue=0, mood=50):
    from server.models.npc_state import NPCState
    return NPCState(health=health, hunger=hunger, fatigue=fatigue, mood=mood)
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd d:/work_ai/agentVillage && python -m pytest tests/server/test_tool_definitions.py::test_eat_tool_restores_hunger -v`
预期：FAIL，ImportError — `definitions` 模块不存在

- [ ] **步骤 3：实现所有工具定义**

```python
# server/tools/definitions.py
"""NPC 一次性工具定义。

每个工具是一个无状态类，execute() 接收 actor_id、LLM 传入参数和运行时上下文，
返回 ToolResult。状态变更由调用者根据 state_changes 应用。
"""

from typing import Any, Dict

from server.tools.base_tool import NPCTool, ToolCategory, ToolParam, ToolResult


# ============================================================
# 生存类工具
# ============================================================

class EatTool(NPCTool):
    name = "eat"
    category = ToolCategory.SURVIVAL
    description = "进食以恢复饱食度（+30）"
    params = []

    def execute(self, actor_id: str, params: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        state = context["npc_states"][actor_id]
        new_hunger = min(100, state.hunger + 30)
        state.hunger = new_hunger
        return ToolResult(success=True, message="吃了一顿饭", state_changes={"hunger": new_hunger})


class SleepTool(NPCTool):
    name = "sleep"
    category = ToolCategory.SURVIVAL
    description = "睡觉，完全恢复疲劳值"
    params = []

    def execute(self, actor_id: str, params: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        state = context["npc_states"][actor_id]
        state.fatigue = 0
        return ToolResult(success=True, message="睡了一觉", state_changes={"fatigue": 0})


class RestTool(NPCTool):
    name = "rest"
    category = ToolCategory.SURVIVAL
    description = "休息片刻，减少疲劳值（-20）"
    params = []

    def execute(self, actor_id: str, params: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        state = context["npc_states"][actor_id]
        new_fatigue = max(0, state.fatigue - 20)
        state.fatigue = new_fatigue
        return ToolResult(success=True, message="休息了一会儿", state_changes={"fatigue": new_fatigue})


class MoveTool(NPCTool):
    name = "move"
    category = ToolCategory.SURVIVAL
    description = "移动到指定地点"
    params = [
        ToolParam(
            name="destination",
            type="string",
            description="目的地",
            enum=["field", "tavern", "home", "market", "church", "forest"],
        ),
    ]

    def execute(self, actor_id: str, params: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        dest = params.get("destination", "home")
        context.setdefault("locations", {})[actor_id] = dest
        return ToolResult(
            success=True,
            message=f"前往了{dest}",
            state_changes={"location": dest},
            broadcast=True,
        )


# ============================================================
# 职业类工具
# ============================================================

class FarmNPCTool(NPCTool):
    name = "farm"
    category = ToolCategory.PROFESSIONAL
    description = "耕作田地，消耗体力（+15疲劳），改善心情（+5）"
    params = []

    def execute(self, actor_id: str, params: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        state = context["npc_states"][actor_id]
        state.fatigue = min(100, state.fatigue + 15)
        state.mood = min(100, state.mood + 5)
        return ToolResult(
            success=True,
            message="辛勤耕作了一阵",
            state_changes={"fatigue": state.fatigue, "mood": state.mood},
        )


class BrewTool(NPCTool):
    name = "brew"
    category = ToolCategory.PROFESSIONAL
    description = "酿造酒水，消耗体力（+10疲劳）"
    params = []

    def execute(self, actor_id: str, params: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        state = context["npc_states"][actor_id]
        state.fatigue = min(100, state.fatigue + 10)
        return ToolResult(
            success=True,
            message="酿了一桶新酒",
            state_changes={"fatigue": state.fatigue},
        )


class PatrolTool(NPCTool):
    name = "patrol"
    category = ToolCategory.PROFESSIONAL
    description = "巡逻村庄，消耗体力（+10疲劳）"
    params = []

    def execute(self, actor_id: str, params: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        state = context["npc_states"][actor_id]
        state.fatigue = min(100, state.fatigue + 10)
        return ToolResult(
            success=True,
            message="完成了一轮巡逻",
            state_changes={"fatigue": state.fatigue},
            broadcast=True,
        )


class DivineTool(NPCTool):
    name = "divine"
    category = ToolCategory.PROFESSIONAL
    description = "进行占卜，消耗精力（+10疲劳），可能影响心情"
    params = []

    def execute(self, actor_id: str, params: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        state = context["npc_states"][actor_id]
        state.fatigue = min(100, state.fatigue + 10)
        return ToolResult(
            success=True,
            message="完成了一次占卜",
            state_changes={"fatigue": state.fatigue},
        )


class PaintTool(NPCTool):
    name = "paint"
    category = ToolCategory.PROFESSIONAL
    description = "绘画创作，消耗体力（+10疲劳），提升心情（+10）"
    params = []

    def execute(self, actor_id: str, params: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        state = context["npc_states"][actor_id]
        state.fatigue = min(100, state.fatigue + 10)
        state.mood = min(100, state.mood + 10)
        return ToolResult(
            success=True,
            message="画了一幅画",
            state_changes={"fatigue": state.fatigue, "mood": state.mood},
        )


# ============================================================
# 社交类工具（一次性动作，不含 speak 会话工具）
# ============================================================

class GossipTool(NPCTool):
    name = "gossip"
    category = ToolCategory.SOCIAL
    description = "向另一个 NPC 传播消息或八卦"
    params = [
        ToolParam(name="target", type="string", description="传播对象 NPC ID"),
        ToolParam(name="content", type="string", description="八卦内容"),
    ]

    def execute(self, actor_id: str, params: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        target = params.get("target", "")
        content = params.get("content", "")
        return ToolResult(
            success=True,
            message=f"向{target}说了一些关于'{content[:20]}'的八卦",
            state_changes={"gossip_target": target, "gossip_content": content},
            broadcast=True,
        )


class TradeTool(NPCTool):
    name = "trade"
    category = ToolCategory.SOCIAL
    description = "与另一个 NPC 或玩家进行物品交易"
    params = [
        ToolParam(name="target", type="string", description="交易对象 ID"),
        ToolParam(name="item", type="string", description="交易物品描述"),
        ToolParam(name="action", type="string", description="give 或 request", enum=["give", "request"]),
    ]

    def execute(self, actor_id: str, params: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        target = params.get("target", "")
        item = params.get("item", "")
        action = params.get("action", "give")
        verb = "给了" if action == "give" else "向其请求"
        return ToolResult(
            success=True,
            message=f"与{target}交易：{verb}'{item}'",
            state_changes={"trade_target": target, "trade_item": item, "trade_action": action},
            broadcast=True,
        )
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd d:/work_ai/agentVillage && python -m pytest tests/server/test_tool_definitions.py -v`
预期：全部 PASS（包括任务 1 的 3 个 + 本任务的 11 个 = 14 tests）

- [ ] **步骤 5：Commit**

```bash
git add server/tools/definitions.py tests/server/test_tool_definitions.py
git commit -m "feat(tools): 定义全部 11 个 NPC 一次性工具（生存/职业/社交）"
```

---

## 任务 4：五层策略管道

**文件：**
- 创建：`server/tools/policy.py`
- 测试：`tests/server/test_tool_policy.py`

- [ ] **步骤 1：编写失败的测试**

```python
# tests/server/test_tool_policy.py
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
    result = gate.filter(ALL_TOOLS, ctx)
    names = [t.name for t in result]
    assert "farm" in names
    assert "brew" not in names
    # 非职业类不受影响
    assert "eat" in names
    assert "gossip" in names


def test_identity_gate_bartender_cannot_farm():
    gate = IdentityGate()
    ctx = {"actor_id": "bartender", "allowed_professional": ["brew"]}
    result = gate.filter(ALL_TOOLS, ctx)
    names = [t.name for t in result]
    assert "brew" in names
    assert "farm" not in names


def test_identity_gate_preserves_non_professional():
    """身份门只过滤职业工具，生存和社交保持原样"""
    gate = IdentityGate()
    ctx = {"actor_id": "farmer", "allowed_professional": ["farm"]}
    result = gate.filter(ALL_TOOLS, ctx)
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
    result = gate.filter(ALL_TOOLS, ctx)
    names = [t.name for t in result]
    assert "gossip" not in names
    assert "trade" not in names
    # 生存类保留（休息/吃饭不应被阻止）
    assert "eat" in names
    assert "rest" in names


def test_state_gate_normal_fatigue_allows_all():
    gate = StateGate()
    state = NPCState(fatigue=50)
    ctx = {"npc_state": state}
    result = gate.filter(ALL_TOOLS, ctx)
    assert len(result) == len(ALL_TOOLS)


def test_state_gate_low_mood_blocks_professional():
    """心情极差时不能工作"""
    gate = StateGate()
    state = NPCState(mood=15)
    ctx = {"npc_state": state}
    result = gate.filter(ALL_TOOLS, ctx)
    names = [t.name for t in result]
    assert "farm" not in names
    assert "brew" not in names
    assert "eat" in names


# ============================================================
# 关系门
# ============================================================

def test_relationship_gate_low_trust_blocks_trade():
    gate = RelationshipGate()
    ctx = {"trust_level": 2}  # 0-10 scale, < 3 blocks trade
    result = gate.filter(ALL_TOOLS, ctx)
    names = [t.name for t in result]
    assert "trade" not in names
    assert "gossip" not in names
    assert "eat" in names


def test_relationship_gate_high_trust_allows_all():
    gate = RelationshipGate()
    ctx = {"trust_level": 8}
    result = gate.filter(ALL_TOOLS, ctx)
    assert len(result) == len(ALL_TOOLS)


# ============================================================
# 时间门
# ============================================================

def test_time_gate_night_blocks_professional():
    gate = TimeGate()
    ctx = {"hour": 23}
    result = gate.filter(ALL_TOOLS, ctx)
    names = [t.name for t in result]
    assert "farm" not in names
    assert "brew" not in names
    assert "eat" in names
    assert "rest" in names


def test_time_gate_daytime_allows_all():
    gate = TimeGate()
    ctx = {"hour": 10}
    result = gate.filter(ALL_TOOLS, ctx)
    assert len(result) == len(ALL_TOOLS)


# ============================================================
# 配额门
# ============================================================

def test_quota_gate_exceeded_blocks_tool():
    gate = QuotaGate()
    ctx = {"daily_usage": {"gossip": 5}, "daily_limits": {"gossip": 3}}
    result = gate.filter(ALL_TOOLS, ctx)
    names = [t.name for t in result]
    assert "gossip" not in names
    assert "trade" in names  # trade 无配额限制


def test_quota_gate_within_limit_allows():
    gate = QuotaGate()
    ctx = {"daily_usage": {"gossip": 1}, "daily_limits": {"gossip": 3}}
    result = gate.filter(ALL_TOOLS, ctx)
    names = [t.name for t in result]
    assert "gossip" in names


# ============================================================
# 完整管道
# ============================================================

def test_full_pipeline_composition():
    """五层管道顺序执行，每层结果传给下一层"""
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
    assert "brew" not in names  # 身份门过滤
    assert "eat" in names
    assert "gossip" in names


def test_full_pipeline_multiple_gates_compound():
    """多层共同作用：夜间 + 高疲劳 → 只剩 eat/rest/sleep"""
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
    assert "farm" not in names  # 时间门
    assert "gossip" not in names  # 状态门
    assert "eat" in names
    assert "rest" in names
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd d:/work_ai/agentVillage && python -m pytest tests/server/test_tool_policy.py -v`
预期：FAIL，ImportError — `policy` 模块不存在

- [ ] **步骤 3：实现策略管道**

```python
# server/tools/policy.py
"""工具策略管道 — 五层过滤。

每层是一个 PolicyGate，接收当前可用工具列表 + 上下文，返回过滤后的列表。
ToolPolicyPipeline 按顺序执行所有门，每层结果作为下层输入。
"""

from typing import List, Dict, Any, Protocol

from server.tools.base_tool import NPCTool, ToolCategory


class PolicyGate(Protocol):
    def filter(self, tools: List[NPCTool], context: Dict[str, Any]) -> List[NPCTool]: ...


class IdentityGate:
    """第 1 层：身份门。只允许 NPC 使用其角色对应的职业工具。"""

    def filter(self, tools: List[NPCTool], context: Dict[str, Any]) -> List[NPCTool]:
        allowed_prof = set(context.get("allowed_professional", []))
        result = []
        for tool in tools:
            if tool.category == ToolCategory.PROFESSIONAL:
                if tool.name in allowed_prof:
                    result.append(tool)
            else:
                result.append(tool)
        return result


class StateGate:
    """第 2 层：状态门。根据 NPC 当前状态过滤不适合的工具。"""

    def filter(self, tools: List[NPCTool], context: Dict[str, Any]) -> List[NPCTool]:
        state = context.get("npc_state")
        if state is None:
            return tools

        result = []
        for tool in tools:
            if state.fatigue > 80 and tool.category == ToolCategory.SOCIAL:
                continue
            if state.mood < 20 and tool.category == ToolCategory.PROFESSIONAL:
                continue
            result.append(tool)
        return result


class RelationshipGate:
    """第 3 层：关系门。信任度不足时限制社交工具。"""

    SOCIAL_TRUST_THRESHOLD = 3  # trust < 3 时禁止社交类工具

    def filter(self, tools: List[NPCTool], context: Dict[str, Any]) -> List[NPCTool]:
        trust = context.get("trust_level")
        if trust is None or trust >= self.SOCIAL_TRUST_THRESHOLD:
            return tools

        return [t for t in tools if t.category != ToolCategory.SOCIAL]


class TimeGate:
    """第 4 层：时间门。22:00-06:00 禁止职业工具。"""

    def filter(self, tools: List[NPCTool], context: Dict[str, Any]) -> List[NPCTool]:
        hour = context.get("hour")
        if hour is None:
            return tools

        is_night = hour >= 22 or hour < 6
        if not is_night:
            return tools

        return [t for t in tools if t.category != ToolCategory.PROFESSIONAL]


class QuotaGate:
    """第 5 层：配额门。每日使用次数超限的工具被移除。"""

    def filter(self, tools: List[NPCTool], context: Dict[str, Any]) -> List[NPCTool]:
        daily_usage = context.get("daily_usage", {})
        daily_limits = context.get("daily_limits", {})
        if not daily_limits:
            return tools

        result = []
        for tool in tools:
            limit = daily_limits.get(tool.name)
            if limit is not None:
                used = daily_usage.get(tool.name, 0)
                if used >= limit:
                    continue
            result.append(tool)
        return result


class ToolPolicyPipeline:
    """工具策略管道。顺序执行所有门。"""

    def __init__(self, gates: List[PolicyGate] | None = None):
        self.gates = gates or [
            IdentityGate(),
            StateGate(),
            RelationshipGate(),
            TimeGate(),
            QuotaGate(),
        ]

    def filter(self, tools: List[NPCTool], context: Dict[str, Any]) -> List[NPCTool]:
        result = list(tools)
        for gate in self.gates:
            result = gate.filter(result, context)
        return result
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd d:/work_ai/agentVillage && python -m pytest tests/server/test_tool_policy.py -v`
预期：全部 PASS（14 tests）

- [ ] **步骤 5：Commit**

```bash
git add server/tools/policy.py tests/server/test_tool_policy.py
git commit -m "feat(tools): 实现五层策略管道（身份/状态/关系/时间/配额）"
```

---

## 任务 5：LLM Client 扩展 function calling

**文件：**
- 修改：`server/llm/client.py`
- 测试：`tests/server/test_llm_function_calling.py`

- [ ] **步骤 1：编写失败的测试**

```python
# tests/server/test_llm_function_calling.py
"""测试 LLM Client 的 function calling 参数构建（不实际调用 API）。"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from server.llm.client import LLMClient


@pytest.fixture
def client():
    return LLMClient(api_key="test-key", base_url="http://fake", model="test-model")


def test_chat_with_tools_builds_correct_payload(client):
    """传入 tools 参数时，payload 包含 tools 字段"""
    tools = [
        {
            "type": "function",
            "function": {
                "name": "eat",
                "description": "进食",
                "parameters": {"type": "object", "properties": {}, "required": []},
            },
        }
    ]

    # 验证 payload 构建逻辑
    payload = client._build_payload(
        messages=[{"role": "user", "content": "test"}],
        tools=tools,
    )
    assert "tools" in payload
    assert payload["tools"] == tools
    assert payload["tool_choice"] == "auto"


def test_chat_without_tools_no_tools_field(client):
    """不传 tools 时，payload 不含 tools 字段"""
    payload = client._build_payload(
        messages=[{"role": "user", "content": "test"}],
        tools=None,
    )
    assert "tools" not in payload
    assert "tool_choice" not in payload


def test_parse_tool_call_from_response():
    """从 LLM 响应中解析 tool_calls"""
    response = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": "call_123",
                    "type": "function",
                    "function": {
                        "name": "eat",
                        "arguments": "{}",
                    },
                }],
            },
            "finish_reason": "tool_calls",
        }],
    }
    from server.llm.client import parse_tool_calls
    calls = parse_tool_calls(response)
    assert len(calls) == 1
    assert calls[0]["name"] == "eat"
    assert calls[0]["arguments"] == {}
    assert calls[0]["call_id"] == "call_123"


def test_parse_tool_call_with_arguments():
    """解析带参数的 tool_call"""
    response = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": None,
                "tool_calls": [{
                    "id": "call_456",
                    "type": "function",
                    "function": {
                        "name": "move",
                        "arguments": '{"destination": "tavern"}',
                    },
                }],
            },
            "finish_reason": "tool_calls",
        }],
    }
    from server.llm.client import parse_tool_calls
    calls = parse_tool_calls(response)
    assert calls[0]["name"] == "move"
    assert calls[0]["arguments"] == {"destination": "tavern"}


def test_parse_no_tool_calls_returns_empty():
    """普通文本回复（无 tool_calls）返回空列表"""
    response = {
        "choices": [{
            "message": {
                "role": "assistant",
                "content": "你好，我是农夫。",
            },
            "finish_reason": "stop",
        }],
    }
    from server.llm.client import parse_tool_calls
    calls = parse_tool_calls(response)
    assert calls == []


def test_build_payload_with_tool_choice_none(client):
    """tool_choice='none' 时强制不调用工具"""
    tools = [{"type": "function", "function": {"name": "eat", "description": "x", "parameters": {"type": "object", "properties": {}, "required": []}}}]
    payload = client._build_payload(
        messages=[{"role": "user", "content": "test"}],
        tools=tools,
        tool_choice="none",
    )
    assert payload["tool_choice"] == "none"
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd d:/work_ai/agentVillage && python -m pytest tests/server/test_llm_function_calling.py -v`
预期：FAIL — `_build_payload` 方法和 `parse_tool_calls` 函数不存在

- [ ] **步骤 3：修改 LLM Client**

在 `server/llm/client.py` 中添加 `_build_payload` 方法和 `parse_tool_calls` 辅助函数：

```python
# 在 LLMClient 类中添加方法：

    def _build_payload(
        self,
        messages: List[Dict[str, str]],
        tools: List[Dict[str, Any]] | None = None,
        tool_choice: str | None = None,
        model: str | None = None,
    ) -> Dict[str, Any]:
        """构建 API 请求 payload。支持可选的 function calling 参数。"""
        payload: Dict[str, Any] = {
            "model": model or self.model,
            "messages": messages,
            "temperature": 0.7,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice or "auto"
        return payload

# 修改现有 chat 方法使用 _build_payload：

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str | None = None,
        tools: List[Dict[str, Any]] | None = None,
        tool_choice: str | None = None,
    ) -> Dict[str, Any]:
        payload = self._build_payload(messages, tools=tools, tool_choice=tool_choice, model=model)
        t0 = time.time()
        async with self.semaphore:
            # ... 现有逻辑不变，只是 payload 由 _build_payload 生成 ...

# 在模块末尾添加辅助函数：

def parse_tool_calls(response: Dict[str, Any]) -> List[Dict[str, Any]]:
    """从 LLM 响应中解析 tool_calls。

    Returns:
        List[{"call_id": str, "name": str, "arguments": dict}]
        无 tool_calls 时返回空列表。
    """
    import json as _json
    message = response.get("choices", [{}])[0].get("message", {})
    raw_calls = message.get("tool_calls", [])
    if not raw_calls:
        return []

    parsed = []
    for call in raw_calls:
        func = call.get("function", {})
        args_str = func.get("arguments", "{}")
        try:
            args = _json.loads(args_str) if isinstance(args_str, str) else args_str
        except _json.JSONDecodeError:
            args = {}
        parsed.append({
            "call_id": call.get("id", ""),
            "name": func.get("name", ""),
            "arguments": args,
        })
    return parsed
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd d:/work_ai/agentVillage && python -m pytest tests/server/test_llm_function_calling.py -v`
预期：5 tests PASS

- [ ] **步骤 5：运行现有 LLM 测试确认无回归**

运行：`cd d:/work_ai/agentVillage && python -m pytest tests/server/ -v -k "not test_context_audit"`
预期：全部 PASS

- [ ] **步骤 6：Commit**

```bash
git add server/llm/client.py tests/server/test_llm_function_calling.py
git commit -m "feat(llm): LLM Client 支持 function calling 参数 + tool_calls 解析"
```

---

## 任务 6：工具执行引擎

**文件：**
- 创建：`server/tools/executor.py`
- 测试：`tests/server/test_tool_executor.py`

- [ ] **步骤 1：编写失败的测试**

```python
# tests/server/test_tool_executor.py
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


# ============================================================
# 测试
# ============================================================

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
    """将执行结果转为 LLM 可理解的 tool result messages"""
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
    """单轮最多执行 3 个工具调用，超出的忽略"""
    executor = ToolExecutor(_make_registry(), max_calls_per_turn=2)
    tool_calls = [
        {"call_id": "c1", "name": "eat", "arguments": {}},
        {"call_id": "c2", "name": "eat", "arguments": {}},
        {"call_id": "c3", "name": "eat", "arguments": {}},
    ]
    results = executor.execute_tool_calls("farmer", tool_calls, _make_context(hunger=10))
    assert len(results) == 2
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd d:/work_ai/agentVillage && python -m pytest tests/server/test_tool_executor.py -v`
预期：FAIL，ImportError — `ToolExecutor` 不存在

- [ ] **步骤 3：实现执行引擎**

```python
# server/tools/executor.py
"""工具执行引擎。

接收 LLM 返回的 tool_calls，逐个查找工具并执行，收集结果。
结果可转为 tool role messages 回传给 LLM 做后续推理。
"""

import json
import logging
from typing import Any, Dict, List

from server.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class ToolExecutor:
    def __init__(self, registry: ToolRegistry, max_calls_per_turn: int = 3):
        self.registry = registry
        self.max_calls_per_turn = max_calls_per_turn

    def execute_tool_calls(
        self,
        actor_id: str,
        tool_calls: List[Dict[str, Any]],
        context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """执行一组 tool_calls，返回结果列表。

        每个结果包含: call_id, name, success, message, state_changes
        """
        results = []
        for call in tool_calls[: self.max_calls_per_turn]:
            call_id = call.get("call_id", "")
            name = call.get("name", "")
            arguments = call.get("arguments", {})

            tool = self.registry.get(name)
            if tool is None:
                results.append({
                    "call_id": call_id,
                    "name": name,
                    "success": False,
                    "message": f"未知工具: {name}",
                    "state_changes": {},
                })
                continue

            try:
                result = tool.execute(actor_id, arguments, context)
                results.append({
                    "call_id": call_id,
                    "name": name,
                    "success": result.success,
                    "message": result.message,
                    "state_changes": result.state_changes,
                })
            except Exception as e:
                logger.warning("工具 %s 执行失败: %s", name, e)
                results.append({
                    "call_id": call_id,
                    "name": name,
                    "success": False,
                    "message": f"执行失败: {e}",
                    "state_changes": {},
                })

        return results

    def build_result_messages(self, results: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """将执行结果转为 OpenAI tool role messages，供后续 LLM 调用。"""
        messages = []
        for r in results:
            content = json.dumps(
                {"success": r["success"], "message": r["message"], "state_changes": r["state_changes"]},
                ensure_ascii=False,
            )
            messages.append({
                "role": "tool",
                "tool_call_id": r["call_id"],
                "content": content,
            })
        return messages
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd d:/work_ai/agentVillage && python -m pytest tests/server/test_tool_executor.py -v`
预期：7 tests PASS

- [ ] **步骤 5：Commit**

```bash
git add server/tools/executor.py tests/server/test_tool_executor.py
git commit -m "feat(tools): 工具执行引擎 — 解析 tool_calls、执行、生成 result messages"
```

---

## 任务 7：NPCAgent 集成工具系统

**文件：**
- 修改：`server/agents/base_agent.py`
- 修改：`server/tools/__init__.py`
- 创建：`tests/server/test_npc_turn.py`

- [ ] **步骤 1：编写失败的测试**

```python
# tests/server/test_npc_turn.py
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


@pytest.mark.asyncio
async def test_run_tool_turn_executes_tool(tmp_path):
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
    assert agent.state.hunger == 60  # 30 + 30


@pytest.mark.asyncio
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
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd d:/work_ai/agentVillage && python -m pytest tests/server/test_npc_turn.py::test_get_available_tools_filters_by_identity -v`
预期：FAIL — `get_available_tools` 方法不存在

- [ ] **步骤 3：修改 NPCAgent 添加工具方法**

在 `server/agents/base_agent.py` 中添加：

```python
# server/agents/base_agent.py — 新增内容

from typing import List, Dict, Any, Optional
from server.tools.registry import ToolRegistry
from server.tools.policy import ToolPolicyPipeline
from server.tools.executor import ToolExecutor
from server.llm.client import get_llm_client, parse_tool_calls


class NPCAgent:
    def __init__(self, agent_id: str, background: dict, memory_base: str, budget: TokenBudget):
        # ... 现有初始化代码保持不变 ...

        # 工具系统（延迟注入，由 Orchestrator 初始化时设置）
        self.tool_registry: Optional[ToolRegistry] = None
        self.tool_pipeline: Optional[ToolPolicyPipeline] = None
        self.tool_executor: Optional[ToolExecutor] = None

    # ... 现有方法保持不变 ...

    def get_available_tools(self, context: Dict[str, Any]) -> List:
        """通过策略管道过滤，返回当前可用工具列表。"""
        if not self.tool_registry or not self.tool_pipeline:
            return []
        all_tools = self.tool_registry.get_all()
        return self.tool_pipeline.filter(all_tools, context)

    def generate_tool_schemas(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """为当前可用工具生成 function calling schemas。"""
        available = self.get_available_tools(context)
        return [tool.to_function_schema() for tool in available]

    async def run_tool_turn(
        self,
        context: Dict[str, Any],
        messages: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """执行一次带工具的 NPC turn。

        流程：过滤可用工具 → 生成 schema → 调用 LLM → 解析响应 → 执行工具 → 返回结果

        Returns:
            {
                "tool_used": str | None,
                "tool_result": dict | None,  # ToolExecutor 返回的结果
                "text_reply": str | None,    # 若 LLM 选择文本回复
            }
        """
        schemas = self.generate_tool_schemas(context)
        client = get_llm_client()

        tools_param = schemas if schemas else None
        response = await client.chat(messages, tools=tools_param)

        tool_calls = parse_tool_calls(response)

        if not tool_calls:
            text = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            return {"tool_used": None, "tool_result": None, "text_reply": text}

        results = self.tool_executor.execute_tool_calls(
            self.agent_id, tool_calls, context
        )

        first = results[0] if results else {}
        return {
            "tool_used": first.get("name"),
            "tool_result": first,
            "text_reply": None,
        }
```

- [ ] **步骤 4：更新 `server/tools/__init__.py` 导出**

```python
# server/tools/__init__.py
from server.tools.base_tool import NPCTool, ToolCategory, ToolParam, ToolResult, Tool
from server.tools.registry import ToolRegistry
from server.tools.policy import ToolPolicyPipeline
from server.tools.executor import ToolExecutor
from server.tools.definitions import (
    EatTool, SleepTool, RestTool, MoveTool,
    FarmNPCTool, BrewTool, PatrolTool, DivineTool, PaintTool,
    GossipTool, TradeTool,
)

__all__ = [
    "NPCTool", "ToolCategory", "ToolParam", "ToolResult", "Tool",
    "ToolRegistry", "ToolPolicyPipeline", "ToolExecutor",
    "EatTool", "SleepTool", "RestTool", "MoveTool",
    "FarmNPCTool", "BrewTool", "PatrolTool", "DivineTool", "PaintTool",
    "GossipTool", "TradeTool",
]
```

- [ ] **步骤 5：运行测试验证通过**

运行：`cd d:/work_ai/agentVillage && python -m pytest tests/server/test_npc_turn.py -v`
预期：5 tests PASS

- [ ] **步骤 6：运行全量测试确认无回归**

运行：`cd d:/work_ai/agentVillage && python -m pytest tests/server/ -v`
预期：全部 PASS

- [ ] **步骤 7：Commit**

```bash
git add server/agents/base_agent.py server/tools/__init__.py tests/server/test_npc_turn.py
git commit -m "feat(agents): NPCAgent 集成工具系统 — get_available_tools + run_tool_turn"
```

---

## 任务 8：全局工具注册 + NPC Turn API 端点

**文件：**
- 创建：`server/tools/setup.py`
- 修改：`server/api/routes.py`
- 修改：`server/core/orchestrator.py`（若存在）或在 routes 中直接初始化

- [ ] **步骤 1：创建全局工具注册初始化模块**

```python
# server/tools/setup.py
"""全局工具注册表初始化。

启动时调用 init_tool_system()，为所有 NPC 配置工具系统。
"""

from server.tools.registry import ToolRegistry
from server.tools.policy import ToolPolicyPipeline
from server.tools.executor import ToolExecutor
from server.tools.definitions import (
    EatTool, SleepTool, RestTool, MoveTool,
    FarmNPCTool, BrewTool, PatrolTool, DivineTool, PaintTool,
    GossipTool, TradeTool,
)

# NPC ID → 允许的职业工具名列表
NPC_PROFESSIONAL_TOOLS = {
    "farmer": ["farm"],
    "bartender": ["brew"],
    "sheriff": ["patrol"],
    "fortune_teller": ["divine"],
    "painter": ["paint"],
    "beggar": [],
}

# 每日工具使用上限
DEFAULT_DAILY_LIMITS = {
    "gossip": 5,
    "trade": 3,
}


def create_registry() -> ToolRegistry:
    """创建并注册所有工具的注册表。"""
    reg = ToolRegistry()
    for tool_cls in [
        EatTool, SleepTool, RestTool, MoveTool,
        FarmNPCTool, BrewTool, PatrolTool, DivineTool, PaintTool,
        GossipTool, TradeTool,
    ]:
        reg.register(tool_cls())
    return reg


def init_tool_system(npcs: dict) -> None:
    """为所有 NPC Agent 配置工具系统。

    Args:
        npcs: {npc_id: NPCAgent} 字典
    """
    registry = create_registry()
    pipeline = ToolPolicyPipeline()

    for npc_id, agent in npcs.items():
        agent.tool_registry = registry
        agent.tool_pipeline = pipeline
        agent.tool_executor = ToolExecutor(registry)
        # 从 background yaml 中读取允许的职业工具，fallback 到默认映射
        bg_tools = agent.background.get("tools", [])
        agent._allowed_professional = bg_tools or NPC_PROFESSIONAL_TOOLS.get(npc_id, [])
        agent._daily_limits = dict(DEFAULT_DAILY_LIMITS)
        agent._daily_usage = {}


def build_policy_context(agent, game_time, trust_level: float = 5.0) -> dict:
    """构建策略管道所需的上下文。"""
    return {
        "actor_id": agent.agent_id,
        "allowed_professional": getattr(agent, "_allowed_professional", []),
        "npc_state": agent.state,
        "trust_level": trust_level,
        "hour": game_time.hour,
        "daily_usage": getattr(agent, "_daily_usage", {}),
        "daily_limits": getattr(agent, "_daily_limits", {}),
    }
```

- [ ] **步骤 2：在 routes.py 中添加 NPC Turn 端点**

在 `server/api/routes.py` 末尾添加新端点：

```python
@router.post("/npc/{npc_id}/turn")
async def npc_autonomous_turn(npc_id: str):
    """触发一次 NPC 自主决策 turn（工具系统）。

    NPC 根据当前状态 + 可用工具，由 LLM 决定行为。
    """
    if npc_id not in orch_mod.orch.npcs:
        raise HTTPException(status_code=404, detail="NPC not found")

    npc = orch_mod.orch.npcs[npc_id]

    if not hasattr(npc, "tool_registry") or npc.tool_registry is None:
        raise HTTPException(status_code=500, detail="工具系统未初始化")

    from server.tools.setup import build_policy_context
    from server.llm.context_builder import ContextBuilder, BuildParams

    game_time = orch_mod.orch.time_system.game_time
    policy_ctx = build_policy_context(npc, game_time)

    # 构建 LLM 消息（复用现有 ContextBuilder，但不传玩家输入）
    from server.config import config as game_config
    builder = ContextBuilder.from_config(game_config)
    world_state = {
        "day": game_time.day,
        "hour": game_time.hour,
        "weather": "晴",
        "events": "今日无事",
    }
    params = BuildParams(
        identity=npc.identity,
        npc_state=npc.state,
        world_state=world_state,
        interlocutor={},
        memory_files={"agent_mem.md": npc.memory._read("agent_mem.md")},
        dialogue_history=[],
        current_input="现在轮到你行动了。根据当前状态和时间，选择一个合适的行为。",
        background=npc.background,
    )
    build_result = builder.build(params)
    messages = build_result.messages

    # 执行工具 turn
    policy_ctx["npc_states"] = {npc_id: npc.state}
    try:
        result = await npc.run_tool_turn(context=policy_ctx, messages=messages)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Turn 执行失败: {e}")

    # 更新每日使用计数
    if result.get("tool_used"):
        usage = getattr(npc, "_daily_usage", {})
        tool_name = result["tool_used"]
        usage[tool_name] = usage.get(tool_name, 0) + 1
        npc._daily_usage = usage

    return {
        "npc_id": npc_id,
        "tool_used": result.get("tool_used"),
        "tool_result": result.get("tool_result"),
        "text_reply": result.get("text_reply"),
        "state_after": {
            "health": npc.state.health,
            "hunger": npc.state.hunger,
            "fatigue": npc.state.fatigue,
            "mood": npc.state.mood,
        },
    }
```

- [ ] **步骤 3：在 Orchestrator 启动时调用 init_tool_system**

在 Orchestrator 初始化 NPC 之后调用：

```python
# 在 orch 初始化 npcs 之后添加
from server.tools.setup import init_tool_system
init_tool_system(self.npcs)
```

- [ ] **步骤 4：编写集成测试**

```python
# 追加到 tests/server/test_npc_turn.py

def test_build_policy_context_from_agent():
    """build_policy_context 从 agent 属性正确构建上下文"""
    from server.tools.setup import build_policy_context, init_tool_system
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
```

- [ ] **步骤 5：运行测试验证通过**

运行：`cd d:/work_ai/agentVillage && python -m pytest tests/server/test_npc_turn.py -v`
预期：全部 PASS

- [ ] **步骤 6：Commit**

```bash
git add server/tools/setup.py server/api/routes.py tests/server/test_npc_turn.py
git commit -m "feat(tools): 全局工具初始化 + NPC Turn API 端点 /npc/{npc_id}/turn"
```

---

## 自检

### 1. 规格覆盖度

| 文档需求 | 对应任务 | 状态 |
|----------|---------|------|
| §4.4 所有 NPC 行为统一为工具调用 | 任务 3 定义 + 任务 7 集成 | ✅ |
| §4.4 三类工具（社交/职业/生存） | 任务 3 (11 个工具) | ✅ |
| §4.4 工具策略管道五层过滤 | 任务 4 | ✅ |
| §11.3 NPC 工具选择由 LLM function calling 全权决定 | 任务 5 + 7 | ✅ |
| §11.3 过滤后 schema 注入 LLM 上下文 | 任务 7 `generate_tool_schemas()` | ✅ |
| §4.4 身份门：农夫不能 brew | 任务 4 IdentityGate 测试 | ✅ |
| §4.4 状态门：fatigue>80 不能复杂社交 | 任务 4 StateGate 测试 | ✅ |
| §4.4 关系门：trust<30 对话受限 | 任务 4 RelationshipGate 测试 | ✅ |
| §4.4 时间门：22-06 不能工作 | 任务 4 TimeGate 测试 | ✅ |
| §4.4 配额门：speak 每天有上限 | 任务 4 QuotaGate 测试 | ✅ |
| §4.5 DialogueSession (speak/accept/reject) | 不在本计划范围 | ⏭️ 单独计划 |
| §4.6 NPC 决策时机 | 任务 8 NPC Turn 端点 | ✅ 基础版 |
| Agent 架构参考 §3 Tool Policy Pipeline | 任务 4 | ✅ |

**遗漏修复：** 无。DialogueSession 明确标注为独立计划，不属于本范围。

### 2. 占位符扫描

已检查全文，无 "待定"、"TODO"、"后续实现"、"添加适当的错误处理" 等占位符。

### 3. 类型一致性

| 类型/方法 | 定义位置 | 引用位置 | 一致性 |
|-----------|---------|---------|--------|
| `NPCTool` | 任务 1 base_tool.py | 任务 2-8 所有文件 | ✅ |
| `ToolCategory` | 任务 1 base_tool.py | 任务 3-4 | ✅ |
| `ToolParam` | 任务 1 base_tool.py | 任务 3 definitions.py | ✅ |
| `ToolResult` | 任务 1 base_tool.py | 任务 3, 6 | ✅ |
| `ToolRegistry` | 任务 2 registry.py | 任务 6, 7, 8 | ✅ |
| `ToolPolicyPipeline` | 任务 4 policy.py | 任务 7, 8 | ✅ |
| `ToolExecutor` | 任务 6 executor.py | 任务 7, 8 | ✅ |
| `parse_tool_calls` | 任务 5 client.py | 任务 7 base_agent.py | ✅ |
| `_build_payload` | 任务 5 client.py | 任务 5 测试 | ✅ |
| `get_available_tools` | 任务 7 base_agent.py | 任务 7 测试, 任务 8 | ✅ |
| `run_tool_turn` | 任务 7 base_agent.py | 任务 7 测试, 任务 8 routes | ✅ |
| `build_policy_context` | 任务 8 setup.py | 任务 8 routes | ✅ |
| `init_tool_system` | 任务 8 setup.py | 任务 8 orchestrator | ✅ |

---

## 执行交接

计划已完成并保存到 `docs/superpowers/plans/2026-05-22-tool-system.md`。两种执行方式：

**1. 子代理驱动（推荐）** - 每个任务调度一个新的子代理，任务间进行审查，快速迭代

**2. 内联执行** - 在当前会话中使用 executing-plans 执行任务，批量执行并设有检查点

选哪种方式？
