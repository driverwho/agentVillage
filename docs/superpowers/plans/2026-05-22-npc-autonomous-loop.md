# NPC 自主活动循环实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** NPC 随游戏时间自动运行，通过决策点触发 + 空闲自动触发 + 事件中断形成自然的日常行为循环。

**架构：** 新增 ActivityState 数据模型和 ActivityManager 管理状态转换。Orchestrator tick 循环改造为：更新状态 → 检查中断 → 检查完成 → 检查决策点 → 对 idle NPC 调用 LLM 决策。所有工具新增 duration_hours 属性。

**技术栈：** Python 3.11+ / dataclasses / pytest / pytest-asyncio

---

## 文件结构

| 操作 | 文件路径 | 职责 |
|------|---------|------|
| 创建 | `server/core/activity_manager.py` | ActivityState 模型 + 中断/完成检查 + 状态转换 |
| 修改 | `server/tools/base_tool.py` | NPCTool 新增 `duration_hours` 属性 |
| 修改 | `server/tools/definitions.py` | 所有工具设置 duration_hours 值 |
| 修改 | `server/agents/base_agent.py` | 新增 activity_state + location 属性 |
| 修改 | `server/core/orchestrator.py` | tick 循环改造，集成 ActivityManager |
| 修改 | `server/tools/setup.py` | 新增 `build_autonomous_context()` |
| 创建 | `tests/server/test_activity_manager.py` | ActivityManager 测试 |
| 创建 | `tests/server/test_autonomous_loop.py` | 完整循环集成测试 |

---

## 任务 1：ActivityState 数据模型 + ActivityManager

**文件：**
- 创建：`server/core/activity_manager.py`
- 测试：`tests/server/test_activity_manager.py`

- [ ] **步骤 1：编写失败的测试**

```python
# tests/server/test_activity_manager.py
import pytest
from server.core.activity_manager import ActivityState, ActivityManager
from server.models.npc_state import NPCState
from server.models.game_time import GameTime


# ============================================================
# ActivityState 基础
# ============================================================

def test_activity_state_default_is_idle():
    state = ActivityState()
    assert state.status == "idle"
    assert state.current_tool is None
    assert state.end_hour is None
    assert state.end_day is None
    assert state.idle_reason is None


def test_activity_state_set_active():
    state = ActivityState()
    state.status = "active"
    state.current_tool = "farm"
    state.end_day = 1
    state.end_hour = 12
    assert state.status == "active"
    assert state.current_tool == "farm"


# ============================================================
# ActivityManager — 活动完成检查
# ============================================================

def test_check_completion_not_done():
    mgr = ActivityManager()
    activity = ActivityState(status="active", current_tool="farm", end_day=1, end_hour=12)
    game_time = GameTime(day=1, hour=10, minute=0)
    assert mgr.check_completion(activity, game_time) is False


def test_check_completion_done():
    mgr = ActivityManager()
    activity = ActivityState(status="active", current_tool="farm", end_day=1, end_hour=12)
    game_time = GameTime(day=1, hour=12, minute=0)
    assert mgr.check_completion(activity, game_time) is True


def test_check_completion_past_due():
    mgr = ActivityManager()
    activity = ActivityState(status="active", current_tool="farm", end_day=1, end_hour=12)
    game_time = GameTime(day=1, hour=14, minute=0)
    assert mgr.check_completion(activity, game_time) is True


def test_check_completion_cross_day():
    """sleep 跨天：day=1 hour=22 开始，end_day=2 end_hour=6"""
    mgr = ActivityManager()
    activity = ActivityState(status="active", current_tool="sleep", end_day=2, end_hour=6)
    assert mgr.check_completion(activity, GameTime(day=1, hour=23, minute=0)) is False
    assert mgr.check_completion(activity, GameTime(day=2, hour=5, minute=0)) is False
    assert mgr.check_completion(activity, GameTime(day=2, hour=6, minute=0)) is True


def test_check_completion_idle_returns_false():
    mgr = ActivityManager()
    activity = ActivityState(status="idle")
    assert mgr.check_completion(activity, GameTime(day=1, hour=10, minute=0)) is False


# ============================================================
# ActivityManager — 中断检查
# ============================================================

def test_check_interrupts_hunger():
    mgr = ActivityManager()
    npc_state = NPCState(hunger=15)
    activity = ActivityState(status="active", current_tool="farm")
    result = mgr.check_interrupts(activity, npc_state)
    assert result is not None
    assert "饥饿" in result


def test_check_interrupts_fatigue():
    mgr = ActivityManager()
    npc_state = NPCState(fatigue=95)
    activity = ActivityState(status="active", current_tool="farm")
    result = mgr.check_interrupts(activity, npc_state)
    assert result is not None
    assert "疲惫" in result


def test_check_interrupts_health():
    mgr = ActivityManager()
    npc_state = NPCState(health=15)
    activity = ActivityState(status="active", current_tool="farm")
    result = mgr.check_interrupts(activity, npc_state)
    assert result is not None
    assert "虚弱" in result


def test_check_interrupts_none_when_ok():
    mgr = ActivityManager()
    npc_state = NPCState(hunger=50, fatigue=50, health=80)
    activity = ActivityState(status="active", current_tool="farm")
    result = mgr.check_interrupts(activity, npc_state)
    assert result is None


def test_check_interrupts_idle_returns_none():
    """idle 状态不检查中断"""
    mgr = ActivityManager()
    npc_state = NPCState(hunger=5)
    activity = ActivityState(status="idle")
    result = mgr.check_interrupts(activity, npc_state)
    assert result is None


# ============================================================
# ActivityManager — 决策点检查
# ============================================================

def test_is_decision_point_true():
    mgr = ActivityManager()
    assert mgr.is_decision_point(6) is True
    assert mgr.is_decision_point(12) is True
    assert mgr.is_decision_point(18) is True
    assert mgr.is_decision_point(20) is True


def test_is_decision_point_false():
    mgr = ActivityManager()
    assert mgr.is_decision_point(7) is False
    assert mgr.is_decision_point(0) is False
    assert mgr.is_decision_point(15) is False


# ============================================================
# ActivityManager — 状态转换
# ============================================================

def test_transition_to_idle():
    mgr = ActivityManager()
    activity = ActivityState(status="active", current_tool="farm", end_day=1, end_hour=12)
    mgr.transition_to_idle(activity, reason="完成了farm")
    assert activity.status == "idle"
    assert activity.idle_reason == "完成了farm"
    assert activity.current_tool is None
    assert activity.end_hour is None
    assert activity.end_day is None


def test_transition_to_active():
    mgr = ActivityManager()
    activity = ActivityState(status="idle")
    game_time = GameTime(day=1, hour=8, minute=0)
    mgr.transition_to_active(activity, tool_name="farm", duration_hours=4, game_time=game_time)
    assert activity.status == "active"
    assert activity.current_tool == "farm"
    assert activity.end_day == 1
    assert activity.end_hour == 12
    assert activity.idle_reason is None


def test_transition_to_active_cross_day():
    """22:00 开始 sleep 8小时 → end_day=2, end_hour=6"""
    mgr = ActivityManager()
    activity = ActivityState(status="idle")
    game_time = GameTime(day=1, hour=22, minute=0)
    mgr.transition_to_active(activity, tool_name="sleep", duration_hours=8, game_time=game_time)
    assert activity.end_day == 2
    assert activity.end_hour == 6


# ============================================================
# ActivityManager — sleep 时长计算
# ============================================================

def test_calculate_sleep_duration():
    mgr = ActivityManager()
    assert mgr.calculate_sleep_duration(22) == 8   # 22→6 = 8h
    assert mgr.calculate_sleep_duration(23) == 7   # 23→6 = 7h
    assert mgr.calculate_sleep_duration(0) == 6    # 0→6 = 6h
    assert mgr.calculate_sleep_duration(20) == 10  # 20→6 = 10h
    assert mgr.calculate_sleep_duration(3) == 6    # 3→6 = 3h, 但最少6h
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd d:/work_ai/agentVillage && python -m pytest tests/server/test_activity_manager.py -v`
预期：FAIL，ImportError — `activity_manager` 模块不存在

- [ ] **步骤 3：实现 ActivityManager**

```python
# server/core/activity_manager.py
"""NPC 活动状态管理。

管理 NPC 的 IDLE/ACTIVE 状态转换、活动完成检查、事件中断检查。
"""

from dataclasses import dataclass
from typing import Literal

from server.models.game_time import GameTime
from server.models.npc_state import NPCState

DECISION_POINTS = [6, 12, 18, 20]

INTERRUPT_CONDITIONS = [
    ("hunger", lambda s: s.hunger < 20, "饥饿难耐"),
    ("fatigue", lambda s: s.fatigue > 90, "极度疲惫"),
    ("health", lambda s: s.health < 20, "身体虚弱"),
]

MIN_SLEEP_HOURS = 6
WAKE_HOUR = 6


@dataclass
class ActivityState:
    status: Literal["idle", "active"] = "idle"
    current_tool: str | None = None
    end_hour: int | None = None
    end_day: int | None = None
    idle_reason: str | None = None


class ActivityManager:
    """管理 NPC 活动状态转换。"""

    def check_completion(self, activity: ActivityState, game_time: GameTime) -> bool:
        """检查当前活动是否已完成（时间到达）。"""
        if activity.status != "active":
            return False
        if activity.end_day is None or activity.end_hour is None:
            return False
        current_abs = game_time.day * 24 + game_time.hour
        end_abs = activity.end_day * 24 + activity.end_hour
        return current_abs >= end_abs

    def check_interrupts(self, activity: ActivityState, npc_state: NPCState) -> str | None:
        """检查是否有中断条件触发。返回中断原因字符串，无中断返回 None。"""
        if activity.status != "active":
            return None
        for _name, condition, reason in INTERRUPT_CONDITIONS:
            if condition(npc_state):
                return reason
        return None

    def is_decision_point(self, hour: int) -> bool:
        """当前小时是否为决策点。"""
        return hour in DECISION_POINTS

    def transition_to_idle(self, activity: ActivityState, reason: str) -> None:
        """将活动状态转为 idle。"""
        activity.status = "idle"
        activity.idle_reason = reason
        activity.current_tool = None
        activity.end_hour = None
        activity.end_day = None

    def transition_to_active(
        self, activity: ActivityState, tool_name: str, duration_hours: int, game_time: GameTime
    ) -> None:
        """将活动状态转为 active，计算结束时间。"""
        end_abs_hour = game_time.hour + duration_hours
        end_day = game_time.day + end_abs_hour // 24
        end_hour = end_abs_hour % 24
        activity.status = "active"
        activity.current_tool = tool_name
        activity.end_day = end_day
        activity.end_hour = end_hour
        activity.idle_reason = None

    def calculate_sleep_duration(self, current_hour: int) -> int:
        """计算从当前小时到次日 WAKE_HOUR 的睡眠时长，最少 MIN_SLEEP_HOURS。"""
        hours_until_wake = (WAKE_HOUR - current_hour) % 24
        if hours_until_wake == 0:
            hours_until_wake = 24
        return max(MIN_SLEEP_HOURS, hours_until_wake)
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd d:/work_ai/agentVillage && python -m pytest tests/server/test_activity_manager.py -v`
预期：全部 PASS（18 tests）

- [ ] **步骤 5：Commit**

```bash
git add server/core/activity_manager.py tests/server/test_activity_manager.py
git commit -m "feat(core): ActivityState 模型 + ActivityManager 状态管理"
```

---

## 任务 2：NPCTool 新增 duration_hours + 工具定义更新

**文件：**
- 修改：`server/tools/base_tool.py`
- 修改：`server/tools/definitions.py`
- 测试：`tests/server/test_tool_definitions.py`

- [ ] **步骤 1：编写失败的测试**

在 `tests/server/test_tool_definitions.py` 末尾追加：

```python
# ============================================================
# 工具时长测试
# ============================================================

def test_all_tools_have_duration():
    """所有 NPCTool 必须声明 duration_hours"""
    from server.tools.definitions import (
        EatTool, SleepTool, RestTool, MoveTool,
        FarmNPCTool, BrewTool, PatrolTool, DivineTool, PaintTool,
        GossipTool, TradeTool,
    )
    tools = [
        EatTool(), SleepTool(), RestTool(), MoveTool(),
        FarmNPCTool(), BrewTool(), PatrolTool(), DivineTool(), PaintTool(),
        GossipTool(), TradeTool(),
    ]
    for tool in tools:
        assert hasattr(tool, "duration_hours"), f"{tool.name} 缺少 duration_hours"
        assert isinstance(tool.duration_hours, int), f"{tool.name} duration_hours 应为 int"
        assert tool.duration_hours >= 0, f"{tool.name} duration_hours 不应为负"


def test_specific_tool_durations():
    """验证关键工具的时长设置"""
    from server.tools.definitions import (
        EatTool, SleepTool, RestTool, MoveTool, FarmNPCTool, BrewTool,
    )
    assert EatTool().duration_hours == 1
    assert SleepTool().duration_hours == -1  # 动态计算，用 -1 标记
    assert RestTool().duration_hours == 2
    assert MoveTool().duration_hours == 1
    assert FarmNPCTool().duration_hours == 4
    assert BrewTool().duration_hours == 3
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd d:/work_ai/agentVillage && python -m pytest tests/server/test_tool_definitions.py::test_all_tools_have_duration -v`
预期：FAIL — AttributeError: 'EatTool' has no attribute 'duration_hours'

- [ ] **步骤 3：修改 NPCTool 基类添加 duration_hours**

在 `server/tools/base_tool.py` 的 `NPCTool` 类中，`params` 下方添加：

```python
class NPCTool(ABC):
    """NPC 工具基类。所有 NPC 行为工具继承此类。"""

    name: str
    category: ToolCategory
    description: str
    params: List[ToolParam] = []
    duration_hours: int = 1  # 执行时长（游戏小时），-1 表示动态计算
```

- [ ] **步骤 4：修改 definitions.py 所有工具设置 duration_hours**

```python
# 在每个工具类中添加 duration_hours 类属性：

class EatTool(NPCTool):
    name = "eat"
    category = ToolCategory.SURVIVAL
    description = "进食以恢复饱食度（+30）"
    params = []
    duration_hours = 1

class SleepTool(NPCTool):
    name = "sleep"
    category = ToolCategory.SURVIVAL
    description = "睡觉，完全恢复疲劳值"
    params = []
    duration_hours = -1  # 动态计算：到次日 6:00

class RestTool(NPCTool):
    name = "rest"
    category = ToolCategory.SURVIVAL
    description = "休息片刻，减少疲劳值（-20）"
    params = []
    duration_hours = 2

class MoveTool(NPCTool):
    name = "move"
    category = ToolCategory.SURVIVAL
    description = "移动到指定地点"
    params = [...]
    duration_hours = 1

class FarmNPCTool(NPCTool):
    name = "farm"
    category = ToolCategory.PROFESSIONAL
    description = "耕作田地，消耗体力（+15疲劳），改善心情（+5）"
    params = []
    duration_hours = 4

class BrewTool(NPCTool):
    name = "brew"
    category = ToolCategory.PROFESSIONAL
    description = "酿造酒水，消耗体力（+10疲劳）"
    params = []
    duration_hours = 3

class PatrolTool(NPCTool):
    name = "patrol"
    category = ToolCategory.PROFESSIONAL
    description = "巡逻村庄，消耗体力（+10疲劳）"
    params = []
    duration_hours = 3

class DivineTool(NPCTool):
    name = "divine"
    category = ToolCategory.PROFESSIONAL
    description = "进行占卜，消耗精力（+10疲劳），可能影响心情"
    params = []
    duration_hours = 2

class PaintTool(NPCTool):
    name = "paint"
    category = ToolCategory.PROFESSIONAL
    description = "绘画创作，消耗体力（+10疲劳），提升心情（+10）"
    params = []
    duration_hours = 3

class GossipTool(NPCTool):
    name = "gossip"
    category = ToolCategory.SOCIAL
    description = "向另一个 NPC 传播消息或八卦"
    params = [...]
    duration_hours = 1

class TradeTool(NPCTool):
    name = "trade"
    category = ToolCategory.SOCIAL
    description = "与另一个 NPC 或玩家进行物品交易"
    params = [...]
    duration_hours = 1
```

- [ ] **步骤 5：运行测试验证通过**

运行：`cd d:/work_ai/agentVillage && python -m pytest tests/server/test_tool_definitions.py -v`
预期：全部 PASS（15 tests）

- [ ] **步骤 6：Commit**

```bash
git add server/tools/base_tool.py server/tools/definitions.py tests/server/test_tool_definitions.py
git commit -m "feat(tools): 所有 NPCTool 新增 duration_hours 属性"
```

---

## 任务 3：NPCAgent 集成 activity_state + location

**文件：**
- 修改：`server/agents/base_agent.py`
- 测试：`tests/server/test_npc_turn.py`（追加）

- [ ] **步骤 1：编写失败的测试**

在 `tests/server/test_npc_turn.py` 末尾追加：

```python
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
    from server.tools.registry import ToolRegistry
    from server.tools.definitions import EatTool
    from server.llm.token_budget import TokenBudget

    reg = ToolRegistry()
    reg.register(EatTool())
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
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd d:/work_ai/agentVillage && python -m pytest tests/server/test_npc_turn.py::test_agent_has_activity_state -v`
预期：FAIL — AttributeError: 'NPCAgent' has no attribute 'activity_state'

- [ ] **步骤 3：修改 NPCAgent**

在 `server/agents/base_agent.py` 的 `__init__` 中，工具系统属性之后添加：

```python
from server.core.activity_manager import ActivityState

class NPCAgent:
    def __init__(self, agent_id: str, background: dict, memory_base: str, budget: TokenBudget):
        # ... 现有代码 ...

        # 工具系统（延迟注入）
        self.tool_registry: Optional[Any] = None
        self.tool_pipeline: Optional[Any] = None
        self.tool_executor: Optional[Any] = None

        # 活动状态
        self.activity_state = ActivityState()
        self.location: str = background.get("default_location", "home")
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd d:/work_ai/agentVillage && python -m pytest tests/server/test_npc_turn.py -v`
预期：全部 PASS（9 tests）

- [ ] **步骤 5：Commit**

```bash
git add server/agents/base_agent.py tests/server/test_npc_turn.py
git commit -m "feat(agents): NPCAgent 新增 activity_state + location 属性"
```

---

## 任务 4：自主决策上下文构建

**文件：**
- 修改：`server/tools/setup.py`
- 测试：`tests/server/test_autonomous_loop.py`

- [ ] **步骤 1：编写失败的测试**

```python
# tests/server/test_autonomous_loop.py
"""NPC 自主活动循环集成测试。"""
import pytest
from unittest.mock import AsyncMock, patch
from server.tools.setup import build_autonomous_context
from server.core.activity_manager import ActivityState
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


def test_build_autonomous_context_first_decision():
    """第一次决策（无上一个活动）"""
    agent = _make_test_agent()
    game_time = GameTime(day=1, hour=6, minute=0)
    ctx = build_autonomous_context(agent, game_time)
    assert "Day 1" in ctx
    assert "6:00" in ctx
    assert "家" in ctx or "home" in ctx
    assert "刚起床" in ctx or "空闲" in ctx


def test_build_autonomous_context_after_activity():
    """完成活动后的上下文"""
    agent = _make_test_agent()
    agent.activity_state.idle_reason = "完成了farm"
    agent.location = "field"
    game_time = GameTime(day=1, hour=12, minute=0)
    ctx = build_autonomous_context(agent, game_time)
    assert "Day 1" in ctx
    assert "12:00" in ctx
    assert "field" in ctx
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
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd d:/work_ai/agentVillage && python -m pytest tests/server/test_autonomous_loop.py::test_build_autonomous_context_first_decision -v`
预期：FAIL — ImportError: cannot import name 'build_autonomous_context'

- [ ] **步骤 3：在 setup.py 中添加 build_autonomous_context**

在 `server/tools/setup.py` 末尾添加：

```python
# 位置 ID → 中文名映射
LOCATION_NAMES = {
    "home": "家",
    "field": "田地",
    "tavern": "酒馆",
    "market": "市场",
    "church": "教堂",
    "forest": "森林",
}


def build_autonomous_context(agent, game_time) -> str:
    """构建 NPC 自主决策时的 current_input 文本。"""
    location_cn = LOCATION_NAMES.get(agent.location, agent.location)
    idle_reason = agent.activity_state.idle_reason

    if idle_reason is None:
        status_text = "刚起床" if game_time.hour == 6 else "空闲"
        last_activity_text = ""
    else:
        status_text = "空闲"
        last_activity_text = f"\n上一个活动：{idle_reason}"

    return (
        f"【行动指令】\n"
        f"当前时间：Day {game_time.day}, {game_time.hour}:00\n"
        f"你的位置：{location_cn}\n"
        f"你的状态：{status_text}"
        f"{last_activity_text}\n"
        f"请从可用工具中选择你接下来要做的事情。"
    )
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd d:/work_ai/agentVillage && python -m pytest tests/server/test_autonomous_loop.py -v`
预期：3 tests PASS

- [ ] **步骤 5：Commit**

```bash
git add server/tools/setup.py tests/server/test_autonomous_loop.py
git commit -m "feat(tools): build_autonomous_context 自主决策上下文构建"
```

---

## 任务 5：Orchestrator tick 循环改造

**文件：**
- 修改：`server/core/orchestrator.py`
- 追加测试：`tests/server/test_autonomous_loop.py`

- [ ] **步骤 1：编写失败的测试**

在 `tests/server/test_autonomous_loop.py` 末尾追加：

```python
# ============================================================
# Orchestrator tick 集成测试
# ============================================================

from server.core.activity_manager import ActivityManager


def test_tick_completes_activity():
    """活动到时间后 NPC 进入 idle"""
    agent = _make_test_agent()
    mgr = ActivityManager()
    game_time = GameTime(day=1, hour=8, minute=0)
    mgr.transition_to_active(agent.activity_state, "farm", 4, game_time)
    assert agent.activity_state.status == "active"

    # 模拟时间到 12:00
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
    mgr.transition_to_active(agent.activity_state, "farm", 6, game_time)  # 到14:00

    # 12:00 是决策点
    assert mgr.is_decision_point(12) is True
    # 强制中断
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

        from server.tools.setup import build_policy_context, build_autonomous_context
        game_time = GameTime(day=1, hour=8, minute=0)
        policy_ctx = build_policy_context(agent, game_time)
        policy_ctx["npc_states"] = {"farmer": agent.state}

        result = await agent.run_tool_turn(
            context=policy_ctx,
            messages=[{"role": "system", "content": "你是农夫"},
                      {"role": "user", "content": build_autonomous_context(agent, game_time)}],
        )

    assert result["tool_used"] == "farm"

    # Orchestrator 负责在 run_tool_turn 后设置 activity_state
    mgr = ActivityManager()
    duration = 4  # farm 的 duration_hours
    mgr.transition_to_active(agent.activity_state, "farm", duration, game_time)
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

        from server.tools.setup import build_policy_context, build_autonomous_context
        game_time = GameTime(day=1, hour=10, minute=0)
        policy_ctx = build_policy_context(agent, game_time)
        policy_ctx["npc_states"] = {"farmer": agent.state}

        result = await agent.run_tool_turn(
            context=policy_ctx,
            messages=[{"role": "system", "content": "你是农夫"},
                      {"role": "user", "content": build_autonomous_context(agent, game_time)}],
        )

    assert result["tool_used"] is None

    # Orchestrator 设置默认闲逛 1 小时
    mgr = ActivityManager()
    mgr.transition_to_active(agent.activity_state, "_idle_wander", 1, game_time)
    assert agent.activity_state.status == "active"
    assert agent.activity_state.end_hour == 11
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd d:/work_ai/agentVillage && python -m pytest tests/server/test_autonomous_loop.py -v`
预期：前 3 个 PASS（任务 4），后 5 个 PASS（纯逻辑测试 + mock LLM）

实际上这些测试应该全部通过，因为它们使用已实现的组件。验证：

运行：`cd d:/work_ai/agentVillage && python -m pytest tests/server/test_autonomous_loop.py -v`
预期：8 tests PASS

- [ ] **步骤 3：改造 Orchestrator tick 循环**

修改 `server/core/orchestrator.py`：

```python
from typing import Dict, Any
import asyncio
from server.core.time_system import TimeSystem
from server.core.message_bus import MessageBus
from server.core.state_store import JsonStore
from server.core.activity_manager import ActivityManager
from server.models.player_state import PlayerState
from server.agents.farmer import FarmerAgent
from server.agents.bartender import BartenderAgent
from server.llm.token_budget import TokenBudget

orch: "Orchestrator | None" = None

AUTO_TICK_INTERVAL = 10


class Orchestrator:
    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.time_system = TimeSystem()
        self.message_bus = MessageBus()
        self.store = JsonStore(base_path=f"data/users/{user_id}")
        self.npcs: Dict[str, Any] = {}
        self.player_state = PlayerState(name="玩家")
        self.activity_manager = ActivityManager()
        self._auto_tick_task: asyncio.Task | None = None
        self._init_npcs()

    def _init_npcs(self) -> None:
        from server.core.background_manager import BackgroundManager

        agent_cls = {
            "farmer": FarmerAgent,
            "bartender": BartenderAgent,
        }
        memory_base = f"data/users/{self.user_id}/memory"
        for npc_id, cls in agent_cls.items():
            bg = BackgroundManager.get(npc_id)
            self.npcs[npc_id] = cls(
                background=bg,
                memory_base=memory_base,
                budget=TokenBudget(daily_limit=5000),
            )

        from server.tools.setup import init_tool_system
        init_tool_system(self.npcs)

    def advance_time(self, minutes: int = 60) -> None:
        if self.time_system.is_paused:
            self.time_system.is_paused = False
        is_hour = self.time_system.tick(minutes)
        if is_hour:
            self._on_hour_tick()
        self._auto_save()

    def _on_hour_tick(self) -> None:
        """每小时 tick 的核心逻辑。"""
        game_time = self.time_system.game_time
        hour = game_time.hour

        # 步骤 1: 更新所有 NPC 状态值
        for npc in self.npcs.values():
            npc.on_hour_tick(game_time)

        # 步骤 2: 检查事件中断
        for npc_id, npc in self.npcs.items():
            if npc.activity_state.status != "active":
                continue
            reason = self.activity_manager.check_interrupts(npc.activity_state, npc.state)
            if reason:
                tool = npc.activity_state.current_tool
                self.activity_manager.transition_to_idle(
                    npc.activity_state, f"因为{reason}中断了{tool}"
                )
                print(f"[AutoTick] {npc_id} 被中断: {reason}")

        # 步骤 3: 检查活动完成
        for npc_id, npc in self.npcs.items():
            if npc.activity_state.status != "active":
                continue
            if self.activity_manager.check_completion(npc.activity_state, game_time):
                tool = npc.activity_state.current_tool
                self.activity_manager.transition_to_idle(
                    npc.activity_state, f"完成了{tool}"
                )
                print(f"[AutoTick] {npc_id} 完成活动: {tool}")

        # 步骤 4: 检查决策点
        if self.activity_manager.is_decision_point(hour):
            for npc_id, npc in self.npcs.items():
                if npc.activity_state.status == "active":
                    tool = npc.activity_state.current_tool
                    self.activity_manager.transition_to_idle(
                        npc.activity_state, f"到了{hour}:00决策时间"
                    )
                    print(f"[AutoTick] {npc_id} 决策点中断: {hour}:00")

        # 步骤 5: 对所有 idle NPC 触发自主决策
        idle_npcs = [
            (npc_id, npc) for npc_id, npc in self.npcs.items()
            if npc.activity_state.status == "idle"
        ]
        if idle_npcs:
            asyncio.create_task(self._run_autonomous_turns(idle_npcs))

    async def _run_autonomous_turns(self, idle_npcs: list) -> None:
        """并发对所有 idle NPC 执行自主决策。"""
        from server.tools.setup import build_policy_context, build_autonomous_context
        from server.llm.context_builder import ContextBuilder, BuildParams
        from server.config import config as game_config

        game_time = self.time_system.game_time
        tasks = []

        for npc_id, npc in idle_npcs:
            # Token 耗尽时跳过 LLM，默认 rest
            if npc.budget.status.value == "exhausted":
                print(f"[AutoTick] {npc_id} token 耗尽，默认 rest")
                self.activity_manager.transition_to_active(
                    npc.activity_state, "rest", 2, game_time
                )
                continue

            tasks.append(self._single_autonomous_turn(npc_id, npc, game_time, game_config))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _single_autonomous_turn(self, npc_id, npc, game_time, game_config) -> None:
        """单个 NPC 的自主决策 turn。"""
        from server.tools.setup import build_policy_context, build_autonomous_context
        from server.llm.context_builder import ContextBuilder, BuildParams
        from server.core.activity_manager import ActivityManager

        try:
            builder = ContextBuilder.from_config(game_config)
            world_state = {
                "day": game_time.day,
                "hour": game_time.hour,
                "weather": "晴",
                "events": "今日无事",
            }
            autonomous_input = build_autonomous_context(npc, game_time)
            params = BuildParams(
                identity=npc.identity,
                npc_state=npc.state,
                world_state=world_state,
                interlocutor={},
                memory_files={"agent_mem.md": npc.memory._read("agent_mem.md")},
                dialogue_history=[],
                current_input=autonomous_input,
                background=npc.background,
            )
            build_result = builder.build(params)
            messages = build_result.messages

            policy_ctx = build_policy_context(npc, game_time)
            policy_ctx["npc_states"] = {npc_id: npc.state}

            result = await npc.run_tool_turn(context=policy_ctx, messages=messages)

            # 根据结果设置 activity_state
            tool_name = result.get("tool_used")
            if tool_name:
                tool = npc.tool_registry.get(tool_name)
                duration = tool.duration_hours if tool else 1
                # sleep 动态计算
                if duration == -1:
                    duration = self.activity_manager.calculate_sleep_duration(game_time.hour)
                self.activity_manager.transition_to_active(
                    npc.activity_state, tool_name, duration, game_time
                )
                # 如果工具是 move，更新位置
                if tool_name == "move" and result.get("tool_result"):
                    new_loc = result["tool_result"].get("state_changes", {}).get("location")
                    if new_loc:
                        npc.location = new_loc
            else:
                # LLM 未调用工具 → 默认闲逛 1 小时
                self.activity_manager.transition_to_active(
                    npc.activity_state, "_idle_wander", 1, game_time
                )

            print(f"[AutoTick] {npc_id} 决策完成: {npc.activity_state.current_tool} "
                  f"(到 Day{npc.activity_state.end_day} {npc.activity_state.end_hour}:00)")

        except Exception as e:
            print(f"[AutoTick] {npc_id} 自主决策失败: {e}")
            # 失败时默认 rest 2 小时
            self.activity_manager.transition_to_active(
                npc.activity_state, "rest", 2, game_time
            )

    def _auto_save(self) -> None:
        self.store.save("world_state", {
            "game_time": self.time_system.game_time.to_dict(),
            "is_paused": self.time_system.is_paused,
        })
        self.store.save("player_state", self.player_state.__dict__)

    async def _auto_tick_loop(self) -> None:
        while True:
            await asyncio.sleep(AUTO_TICK_INTERVAL)
            if not self.time_system.is_paused:
                self.advance_time(60)

    def start_auto_tick(self) -> None:
        if self._auto_tick_task is None:
            self._auto_tick_task = asyncio.create_task(self._auto_tick_loop())

    def stop_auto_tick(self) -> None:
        if self._auto_tick_task:
            self._auto_tick_task.cancel()
            self._auto_tick_task = None

    def get_world_state(self) -> dict:
        return {
            "game_time": self.time_system.game_time.to_dict(),
            "is_paused": self.time_system.is_paused,
            "npcs": {
                nid: {
                    "state": {
                        "health": n.state.health,
                        "hunger": n.state.hunger,
                        "fatigue": n.state.fatigue,
                        "mood": n.state.mood,
                    },
                    "activity": {
                        "status": n.activity_state.status,
                        "current_tool": n.activity_state.current_tool,
                        "location": n.location,
                    },
                }
                for nid, n in self.npcs.items()
            },
        }
```

- [ ] **步骤 4：运行全量测试**

运行：`cd d:/work_ai/agentVillage && python -m pytest tests/server/ --ignore=tests/server/test_context_audit.py -v`
预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add server/core/orchestrator.py tests/server/test_autonomous_loop.py
git commit -m "feat(core): Orchestrator tick 改造 — 中断/完成/决策点/自主 LLM 调用"
```

---

## 自检

### 1. 规格覆盖度

| 规格章节 | 对应任务 | 状态 |
|----------|---------|------|
| §1 ActivityState 数据模型 | 任务 1 | ✅ |
| §2 工具时长 (duration_hours) | 任务 2 | ✅ |
| §3 触发条件（决策点/完成/中断） | 任务 1 + 5 | ✅ |
| §4 Orchestrator tick 改造（步骤1-6） | 任务 5 | ✅ |
| §5 LLM 上下文增强 | 任务 4 | ✅ |
| §6 工具执行后设置 ActivityState | 任务 5 `_single_autonomous_turn` | ✅ |
| §7 中断条件 (hunger/fatigue/health) | 任务 1 `INTERRUPT_CONDITIONS` | ✅ |
| §8 NPC 位置追踪 | 任务 3 + 5 (move 更新) | ✅ |
| §9 Token 预算（耗尽时默认 rest） | 任务 5 `_run_autonomous_turns` | ✅ |
| §11 get_world_state 返回活动信息 | 任务 5 `get_world_state` 改造 | ✅ |

**遗漏：** 无。sleep 动态时长计算在任务 1 `calculate_sleep_duration` + 任务 5 调用处覆盖。

### 2. 占位符扫描

全文无 "待定"、"TODO"、"后续实现" 等占位符。

### 3. 类型一致性

| 类型/方法 | 定义位置 | 引用位置 | 一致性 |
|-----------|---------|---------|--------|
| `ActivityState` | 任务 1 activity_manager.py | 任务 3 base_agent.py, 任务 5 orchestrator.py | ✅ |
| `ActivityManager` | 任务 1 activity_manager.py | 任务 5 orchestrator.py, 测试文件 | ✅ |
| `check_completion()` | 任务 1 | 任务 5 步骤 3 | ✅ |
| `check_interrupts()` | 任务 1 | 任务 5 步骤 2 | ✅ |
| `is_decision_point()` | 任务 1 | 任务 5 步骤 4 | ✅ |
| `transition_to_idle()` | 任务 1 | 任务 5 | ✅ |
| `transition_to_active()` | 任务 1 | 任务 5 | ✅ |
| `calculate_sleep_duration()` | 任务 1 | 任务 5 `_single_autonomous_turn` | ✅ |
| `duration_hours` | 任务 2 base_tool.py | 任务 5 `_single_autonomous_turn` | ✅ |
| `build_autonomous_context()` | 任务 4 setup.py | 任务 5 orchestrator.py | ✅ |
| `agent.activity_state` | 任务 3 base_agent.py | 任务 1 测试, 任务 5 | ✅ |
| `agent.location` | 任务 3 base_agent.py | 任务 4, 任务 5 | ✅ |

---

## 执行交接

计划已完成并保存到 `docs/superpowers/plans/2026-05-22-npc-autonomous-loop.md`。两种执行方式：

**1. 子代理驱动（推荐）** - 每个任务调度一个新的子代理，任务间进行审查，快速迭代

**2. 内联执行** - 在当前会话中使用 executing-plans 执行任务，批量执行并设有检查点

选哪种方式？
