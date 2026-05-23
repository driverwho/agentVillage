# 事件引擎 + NPC 交互系统 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 为 NPC 村庄引入规则驱动的事件生成系统和基于 Hook 的 NPC 交互系统，打破 NPC 行为的固定循环。

**架构：** EventEngine 每 tick 根据概率表生成事件注入 world_state；LocationRegistry 全局管理 NPC 位置；HookRegistry 在工具执行后触发扩展逻辑；InteractionHook 在 NPC 到达新地点后检测共处 NPC 并发起多轮对话。

**技术栈：** Python 3.11 / FastAPI / Vue 3 + Pinia / PyYAML / pytest

**规格文档：** `docs/superpowers/specs/2026-05-23-event-engine-npc-interaction-design.md`

---

## 文件结构

### 新增文件

| 文件 | 职责 |
|------|------|
| `server/core/event_engine.py` | EventDef, ActiveEvent, EventState, EventEngine |
| `server/core/location_registry.py` | LocationRegistry |
| `server/hooks/__init__.py` | HookRegistry |
| `server/hooks/base.py` | Hook 基类 |
| `server/hooks/interaction_hook.py` | InteractionHook + should_interact + InteractionCounter |
| `server/core/interaction_runner.py` | InteractionRunner + ConversationResult |
| `server/data/events/weather.yaml` | 天气事件定义 |
| `server/data/events/visitor.yaml` | 访客事件定义 |
| `server/data/events/discovery.yaml` | 发现事件定义 |
| `server/data/events/npc_trigger.yaml` | NPC 触发事件定义 |
| `tests/server/test_event_engine.py` | EventEngine 单元测试 |
| `tests/server/test_location_registry.py` | LocationRegistry 单元测试 |
| `tests/server/test_hook_registry.py` | HookRegistry 单元测试 |
| `tests/server/test_interaction_hook.py` | InteractionHook 单元测试 |

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `server/core/orchestrator.py` | 初始化新模块；tick 中调用 event_engine；move 后 fire hook；auto_save 扩展 |
| `server/tools/setup.py` | `build_autonomous_context` 增加环境和社交字段 |
| `server/llm/context_builder.py` | NPC_INTERACTION 场景的 Layer 3 构建 |
| `server/api/routes.py` | `get_npcs_status` 返回 active events |
| `client/src/stores/observeStore.ts` | 新增 worldEvents 状态 |
| `client/src/pages/ObservePage.vue` | 新增事件 banner |

---

## 任务 1：EventEngine 核心逻辑

**文件：**
- 创建：`server/core/event_engine.py`
- 测试：`tests/server/test_event_engine.py`

- [ ] **步骤 1：编写 EventEngine 测试**

```python
# tests/server/test_event_engine.py
import pytest
from unittest.mock import patch
from server.core.event_engine import EventDef, ActiveEvent, EventState, EventEngine
from server.models.game_time import GameTime


def _make_event(id="rain", probability=1.0, duration=4, category="weather",
                conditions=None):
    return EventDef(
        id=id, name="测试事件", category=category,
        probability=probability, duration_hours=duration,
        conditions=conditions or {}, description="测试描述",
    )


def test_tick_generates_event_when_probability_is_1():
    engine = EventEngine(event_defs=[_make_event()], state=EventState())
    game_time = GameTime(day=1, hour=8)
    active = engine.tick(game_time)
    assert len(active) == 1
    assert active[0].id == "rain"


def test_tick_respects_cooldown():
    state = EventState(cooldowns={"rain": 3})
    engine = EventEngine(event_defs=[_make_event()], state=state)
    game_time = GameTime(day=2, hour=8)
    active = engine.tick(game_time)
    assert len(active) == 0


def test_tick_removes_expired_events():
    expired = ActiveEvent(
        id="rain", name="雨", description="下雨",
        started_day=1, started_hour=6, expires_day=1, expires_hour=10,
    )
    state = EventState(active_events=[expired])
    engine = EventEngine(event_defs=[], state=state)
    game_time = GameTime(day=1, hour=10)
    active = engine.tick(game_time)
    assert len(active) == 0


def test_tick_respects_min_day():
    engine = EventEngine(
        event_defs=[_make_event(conditions={"min_day": 3})],
        state=EventState(),
    )
    active = engine.tick(GameTime(day=2, hour=8))
    assert len(active) == 0


def test_tick_respects_hour_range():
    engine = EventEngine(
        event_defs=[_make_event(conditions={"hour_range": [6, 10]})],
        state=EventState(),
    )
    assert len(engine.tick(GameTime(day=1, hour=8))) == 1
    engine2 = EventEngine(
        event_defs=[_make_event(conditions={"hour_range": [6, 10]})],
        state=EventState(),
    )
    assert len(engine2.tick(GameTime(day=1, hour=12))) == 0


def test_tick_respects_max_active_events():
    events = [_make_event(id=f"e{i}", conditions={"max_active_events": 2})
              for i in range(5)]
    engine = EventEngine(event_defs=events, state=EventState())
    active = engine.tick(GameTime(day=1, hour=8))
    assert len(active) <= 2


def test_get_current_weather_default():
    engine = EventEngine(event_defs=[], state=EventState())
    assert engine.get_current_weather() == "晴"


def test_get_current_weather_with_event():
    state = EventState(active_events=[
        ActiveEvent(id="rain", name="暴雨", description="倾盆大雨",
                    started_day=1, started_hour=6, expires_day=1, expires_hour=14),
    ])
    engine = EventEngine(event_defs=[], state=state)
    assert engine.get_current_weather() == "暴雨"


def test_get_world_events_text_empty():
    engine = EventEngine(event_defs=[], state=EventState())
    assert engine.get_world_events_text() == "今日无事"


def test_get_world_events_text_with_events():
    state = EventState(active_events=[
        ActiveEvent(id="merchant", name="商人", description="旅行商人在市场",
                    started_day=1, started_hour=8, expires_day=1, expires_hour=16),
    ])
    engine = EventEngine(event_defs=[], state=state)
    text = engine.get_world_events_text()
    assert "旅行商人在市场" in text
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest tests/server/test_event_engine.py -v`
预期：FAIL，ModuleNotFoundError: No module named 'server.core.event_engine'

- [ ] **步骤 3：实现 EventEngine**

```python
# server/core/event_engine.py
from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List
from server.models.game_time import GameTime


@dataclass
class EventDef:
    id: str
    name: str
    category: str
    probability: float
    duration_hours: int
    conditions: Dict[str, Any]
    description: str


@dataclass
class ActiveEvent:
    id: str
    name: str
    description: str
    started_day: int
    started_hour: int
    expires_day: int
    expires_hour: int


@dataclass
class EventState:
    active_events: List[ActiveEvent] = field(default_factory=list)
    cooldowns: Dict[str, int] = field(default_factory=dict)


class EventEngine:
    def __init__(self, event_defs: List[EventDef], state: EventState):
        self.event_defs = event_defs
        self.state = state

    def tick(self, game_time: GameTime) -> List[ActiveEvent]:
        self._expire_events(game_time)
        self._try_generate(game_time)
        return list(self.state.active_events)

    def _expire_events(self, game_time: GameTime) -> None:
        self.state.active_events = [
            e for e in self.state.active_events
            if not self._is_expired(e, game_time)
        ]

    def _is_expired(self, event: ActiveEvent, game_time: GameTime) -> bool:
        if game_time.day > event.expires_day:
            return True
        if game_time.day == event.expires_day and game_time.hour >= event.expires_hour:
            return True
        return False

    def _try_generate(self, game_time: GameTime) -> None:
        active_ids = {e.id for e in self.state.active_events}
        for event_def in self.event_defs:
            if event_def.id in active_ids:
                continue
            if not self._check_conditions(event_def, game_time):
                continue
            if random.random() < event_def.probability:
                self._activate(event_def, game_time)
                active_ids.add(event_def.id)

    def _check_conditions(self, event_def: EventDef, game_time: GameTime) -> bool:
        cond = event_def.conditions
        if game_time.day < cond.get("min_day", 1):
            return False
        if event_def.id in self.state.cooldowns:
            if game_time.day < self.state.cooldowns[event_def.id]:
                return False
        hour_range = cond.get("hour_range")
        if hour_range and not (hour_range[0] <= game_time.hour < hour_range[1]):
            return False
        max_active = cond.get("max_active_events", 3)
        if len(self.state.active_events) >= max_active:
            return False
        required = cond.get("required_event")
        if required:
            active_ids = {e.id for e in self.state.active_events}
            if required not in active_ids:
                return False
        return True

    def _activate(self, event_def: EventDef, game_time: GameTime) -> None:
        expires_hour = game_time.hour + event_def.duration_hours
        expires_day = game_time.day
        while expires_hour >= 24:
            expires_hour -= 24
            expires_day += 1
        active = ActiveEvent(
            id=event_def.id, name=event_def.name, description=event_def.description,
            started_day=game_time.day, started_hour=game_time.hour,
            expires_day=expires_day, expires_hour=expires_hour,
        )
        self.state.active_events.append(active)
        cooldown_days = event_def.conditions.get("cooldown_days", 0)
        if cooldown_days:
            self.state.cooldowns[event_def.id] = game_time.day + cooldown_days

    def get_current_weather(self) -> str:
        for event in self.state.active_events:
            if event.id in _WEATHER_IDS:
                return event.name
        return "晴"

    def get_world_events_text(self) -> str:
        non_weather = [e for e in self.state.active_events if e.id not in _WEATHER_IDS]
        if not non_weather:
            return "今日无事"
        return "；".join(e.description for e in non_weather)


_WEATHER_IDS = {"heavy_rain", "fog", "scorching_heat", "strong_wind"}
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest tests/server/test_event_engine.py -v`
预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add server/core/event_engine.py tests/server/test_event_engine.py
git commit -m "feat: EventEngine 核心逻辑——规则驱动的事件生成引擎"
```

---

## 任务 2：事件 YAML 定义文件

**文件：**
- 创建：`server/data/events/weather.yaml`
- 创建：`server/data/events/visitor.yaml`
- 创建：`server/data/events/discovery.yaml`
- 创建：`server/data/events/npc_trigger.yaml`

- [ ] **步骤 1：创建 weather.yaml**

```yaml
# server/data/events/weather.yaml
category: weather
events:
  - id: heavy_rain
    name: "暴雨"
    probability: 0.12
    duration_hours: 8
    conditions:
      min_day: 2
      cooldown_days: 2
    description: "乌云密布，暴雨倾盆，田间泥泞难行。"

  - id: fog
    name: "浓雾"
    probability: 0.10
    duration_hours: 4
    conditions:
      hour_range: [6, 10]
      cooldown_days: 2
    description: "晨雾弥漫，五步之外不见人影。"

  - id: scorching_heat
    name: "酷暑"
    probability: 0.10
    duration_hours: 6
    conditions:
      hour_range: [10, 18]
      cooldown_days: 3
    description: "烈日当空，热浪灼人，户外劳作格外辛苦。"

  - id: strong_wind
    name: "大风"
    probability: 0.08
    duration_hours: 5
    conditions:
      cooldown_days: 2
    description: "狂风呼啸，树枝摇曳，屋顶瓦片似乎在松动。"
```

- [ ] **步骤 2：创建 visitor.yaml**

```yaml
# server/data/events/visitor.yaml
category: visitor
events:
  - id: merchant_visit
    name: "旅行商人"
    probability: 0.08
    duration_hours: 10
    conditions:
      min_day: 2
      cooldown_days: 4
    description: "一个背着大包的旅行商人在市场摆起了摊位，兜售各地的稀罕物件。"

  - id: wandering_poet
    name: "流浪诗人"
    probability: 0.06
    duration_hours: 8
    conditions:
      min_day: 3
      cooldown_days: 5
    description: "一位衣衫褴褛但气质不凡的流浪诗人来到村里，在酒馆吟诵诗歌换取食宿。"

  - id: mysterious_messenger
    name: "神秘信使"
    probability: 0.05
    duration_hours: 4
    conditions:
      min_day: 5
      cooldown_days: 7
    description: "一个戴着兜帽的信使骑马经过村庄，在村口短暂停留后匆匆离去。"
```

- [ ] **步骤 3：创建 discovery.yaml**

```yaml
# server/data/events/discovery.yaml
category: discovery
events:
  - id: old_relic
    name: "旧物出土"
    probability: 0.06
    duration_hours: 24
    conditions:
      min_day: 3
      cooldown_days: 7
    description: "有人在田里翻出了一件锈迹斑斑的古老物件，看起来年代久远。"

  - id: well_discolor
    name: "井水变色"
    probability: 0.04
    duration_hours: 12
    conditions:
      min_day: 4
      cooldown_days: 10
    description: "村中水井的水变成了淡淡的铁锈色，喝起来有股金属味。"

  - id: strange_plant
    name: "异常植物"
    probability: 0.05
    duration_hours: 48
    conditions:
      min_day: 3
      cooldown_days: 8
    description: "田地边缘长出了一株从未见过的植物，叶片在夜间隐隐发光。"

  - id: distant_smoke
    name: "远处浓烟"
    probability: 0.07
    duration_hours: 6
    conditions:
      min_day: 2
      cooldown_days: 5
    description: "远处山头升起了浓烟，不像是普通的炊烟，但也不像森林大火。"
```

- [ ] **步骤 4：创建 npc_trigger.yaml**

```yaml
# server/data/events/npc_trigger.yaml
category: npc_trigger
events:
  - id: son_letter
    name: "儿子来信"
    probability: 0.05
    duration_hours: 24
    conditions:
      min_day: 4
      cooldown_days: 10
    description: "乔治收到了城里儿子寄来的一封信，信封上的字迹有些潦草。"

  - id: suspicious_footprints
    name: "可疑脚印"
    probability: 0.06
    duration_hours: 12
    conditions:
      min_day: 3
      cooldown_days: 6
    description: "Gus 在酒馆后门发现了一串可疑的脚印，似乎有人在夜里徘徊过。"

  - id: stray_dog_injured
    name: "流浪狗受伤"
    probability: 0.07
    duration_hours: 24
    conditions:
      min_day: 2
      cooldown_days: 7
    description: "村里的流浪狗瘸着一条腿回来了，身上有被什么东西咬过的痕迹。"

  - id: tavern_leak
    name: "酒馆漏雨"
    probability: 0.06
    duration_hours: 12
    conditions:
      min_day: 2
      cooldown_days: 8
      required_event: "heavy_rain"
    description: "酒馆屋顶开始漏雨，Gus 不得不用水桶接水，酒馆里弥漫着潮湿的气味。"
```

- [ ] **步骤 5：添加 YAML 加载函数到 EventEngine**

在 `server/core/event_engine.py` 末尾添加：

```python
def load_event_defs(events_dir: str) -> List[EventDef]:
    """从指定目录加载所有事件 YAML 定义。"""
    import yaml
    from pathlib import Path

    defs = []
    events_path = Path(events_dir)
    if not events_path.exists():
        return defs
    for yaml_file in events_path.glob("*.yaml"):
        with open(yaml_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        category = data.get("category", "unknown")
        for item in data.get("events", []):
            defs.append(EventDef(
                id=item["id"],
                name=item["name"],
                category=category,
                probability=item["probability"],
                duration_hours=item["duration_hours"],
                conditions=item.get("conditions", {}),
                description=item["description"],
            ))
    return defs
```

- [ ] **步骤 6：编写加载函数测试**

在 `tests/server/test_event_engine.py` 追加：

```python
def test_load_event_defs(tmp_path):
    import yaml
    yaml_content = {
        "category": "weather",
        "events": [
            {"id": "rain", "name": "雨", "probability": 0.1,
             "duration_hours": 4, "conditions": {}, "description": "下雨了"}
        ]
    }
    (tmp_path / "weather.yaml").write_text(
        yaml.dump(yaml_content, allow_unicode=True), encoding="utf-8"
    )
    from server.core.event_engine import load_event_defs
    defs = load_event_defs(str(tmp_path))
    assert len(defs) == 1
    assert defs[0].id == "rain"
    assert defs[0].category == "weather"
```

- [ ] **步骤 7：运行测试验证通过**

运行：`pytest tests/server/test_event_engine.py -v`
预期：全部 PASS

- [ ] **步骤 8：Commit**

```bash
git add server/data/events/ server/core/event_engine.py tests/server/test_event_engine.py
git commit -m "feat: 事件 YAML 定义（4类15个事件）+ 加载函数"
```

---

## 任务 3：LocationRegistry

**文件：**
- 创建：`server/core/location_registry.py`
- 测试：`tests/server/test_location_registry.py`

- [ ] **步骤 1：编写测试**

```python
# tests/server/test_location_registry.py
from server.core.location_registry import LocationRegistry


def test_initial_empty():
    reg = LocationRegistry()
    assert reg.get_npcs_at("tavern") == set()


def test_initial_from_dict():
    reg = LocationRegistry(initial={"tavern": ["bartender"], "field": ["farmer"]})
    assert reg.get_npcs_at("tavern") == {"bartender"}
    assert reg.get_npcs_at("field") == {"farmer"}


def test_move_adds_to_new_location():
    reg = LocationRegistry()
    reg.move("farmer", None, "field")
    assert reg.get_npcs_at("field") == {"farmer"}


def test_move_removes_from_old_location():
    reg = LocationRegistry(initial={"field": ["farmer"]})
    reg.move("farmer", "field", "tavern")
    assert reg.get_npcs_at("field") == set()
    assert reg.get_npcs_at("tavern") == {"farmer"}


def test_get_location():
    reg = LocationRegistry(initial={"tavern": ["bartender"]})
    assert reg.get_location("bartender") == "tavern"
    assert reg.get_location("unknown") is None


def test_to_dict():
    reg = LocationRegistry(initial={"tavern": ["bartender", "farmer"]})
    d = reg.to_dict()
    assert d == {"tavern": ["bartender", "farmer"]}


def test_to_dict_excludes_empty():
    reg = LocationRegistry(initial={"tavern": ["bartender"], "field": []})
    d = reg.to_dict()
    assert "field" not in d
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest tests/server/test_location_registry.py -v`
预期：FAIL，ModuleNotFoundError

- [ ] **步骤 3：实现 LocationRegistry**

```python
# server/core/location_registry.py
from __future__ import annotations
from collections import defaultdict
from typing import Dict, List, Set


class LocationRegistry:
    def __init__(self, initial: Dict[str, List[str]] | None = None):
        self._map: Dict[str, Set[str]] = defaultdict(set)
        if initial:
            for loc, npcs in initial.items():
                self._map[loc] = set(npcs)

    def move(self, npc_id: str, from_loc: str | None, to_loc: str) -> None:
        if from_loc:
            self._map[from_loc].discard(npc_id)
        self._map[to_loc].add(npc_id)

    def get_npcs_at(self, location: str) -> Set[str]:
        return self._map[location].copy()

    def get_location(self, npc_id: str) -> str | None:
        for loc, npcs in self._map.items():
            if npc_id in npcs:
                return loc
        return None

    def to_dict(self) -> Dict[str, List[str]]:
        return {loc: sorted(npcs) for loc, npcs in self._map.items() if npcs}
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest tests/server/test_location_registry.py -v`
预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add server/core/location_registry.py tests/server/test_location_registry.py
git commit -m "feat: LocationRegistry 全局地点管理"
```

---

## 任务 4：Hook 系统基础

**文件：**
- 创建：`server/hooks/__init__.py`
- 创建：`server/hooks/base.py`
- 测试：`tests/server/test_hook_registry.py`

- [ ] **步骤 1：编写测试**

```python
# tests/server/test_hook_registry.py
import pytest
import asyncio
from server.hooks import HookRegistry
from server.hooks.base import Hook


class FakeHook(Hook):
    event = "post_move"

    def __init__(self):
        self.calls = []

    async def execute(self, context):
        self.calls.append(context)


class AnotherHook(Hook):
    event = "post_sleep"

    def __init__(self):
        self.calls = []

    async def execute(self, context):
        self.calls.append(context)


@pytest.mark.asyncio
async def test_register_and_fire():
    registry = HookRegistry()
    hook = FakeHook()
    registry.register(hook)
    await registry.fire("post_move", {"actor_id": "farmer", "location": "tavern"})
    assert len(hook.calls) == 1
    assert hook.calls[0]["actor_id"] == "farmer"


@pytest.mark.asyncio
async def test_fire_only_matching_event():
    registry = HookRegistry()
    move_hook = FakeHook()
    sleep_hook = AnotherHook()
    registry.register(move_hook)
    registry.register(sleep_hook)
    await registry.fire("post_move", {"actor_id": "farmer"})
    assert len(move_hook.calls) == 1
    assert len(sleep_hook.calls) == 0


@pytest.mark.asyncio
async def test_fire_no_hooks_registered():
    registry = HookRegistry()
    await registry.fire("post_move", {"actor_id": "farmer"})


@pytest.mark.asyncio
async def test_multiple_hooks_same_event():
    registry = HookRegistry()
    h1 = FakeHook()
    h2 = FakeHook()
    registry.register(h1)
    registry.register(h2)
    await registry.fire("post_move", {"x": 1})
    assert len(h1.calls) == 1
    assert len(h2.calls) == 1
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest tests/server/test_hook_registry.py -v`
预期：FAIL，ModuleNotFoundError

- [ ] **步骤 3：实现 Hook 基类和 HookRegistry**

```python
# server/hooks/base.py
from typing import Any, Dict


class Hook:
    event: str = ""

    async def execute(self, context: Dict[str, Any]) -> None:
        raise NotImplementedError
```

```python
# server/hooks/__init__.py
from collections import defaultdict
from typing import Any, Dict, List
from server.hooks.base import Hook


class HookRegistry:
    def __init__(self):
        self._hooks: Dict[str, List[Hook]] = defaultdict(list)

    def register(self, hook: Hook) -> None:
        self._hooks[hook.event].append(hook)

    async def fire(self, event: str, context: Dict[str, Any]) -> None:
        for hook in self._hooks.get(event, []):
            await hook.execute(context)
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest tests/server/test_hook_registry.py -v`
预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add server/hooks/__init__.py server/hooks/base.py tests/server/test_hook_registry.py
git commit -m "feat: Hook 系统基础——Hook 基类 + HookRegistry"
```

---

## 任务 5：InteractionHook + InteractionCounter

**文件：**
- 创建：`server/hooks/interaction_hook.py`
- 测试：`tests/server/test_interaction_hook.py`

- [ ] **步骤 1：编写测试**

```python
# tests/server/test_interaction_hook.py
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from server.hooks.interaction_hook import InteractionHook, InteractionCounter, should_interact
from server.models.game_time import GameTime
from server.core.location_registry import LocationRegistry


def _make_npc(npc_id, location="home", status="idle", relationships=None):
    npc = MagicMock()
    npc.id = npc_id
    npc.agent_id = npc_id
    npc.location = location
    npc.activity_state = MagicMock()
    npc.activity_state.status = status
    npc.background = {"relationships": relationships or {}}
    return npc


def test_interaction_counter_initial_zero():
    counter = InteractionCounter()
    pair = ("bartender", "farmer")
    assert counter.get_today_count(pair, day=1) == 0


def test_interaction_counter_increment():
    counter = InteractionCounter()
    pair = ("bartender", "farmer")
    counter.increment(pair, day=1)
    assert counter.get_today_count(pair, day=1) == 1
    counter.increment(pair, day=1)
    assert counter.get_today_count(pair, day=1) == 2


def test_interaction_counter_different_day():
    counter = InteractionCounter()
    pair = ("bartender", "farmer")
    counter.increment(pair, day=1)
    assert counter.get_today_count(pair, day=2) == 0


def test_should_interact_no_relationship():
    initiator = _make_npc("farmer", relationships={})
    target = _make_npc("bartender")
    counter = InteractionCounter()
    assert should_interact(initiator, target, GameTime(day=1, hour=12), counter) is False


def test_should_interact_low_trust():
    initiator = _make_npc("farmer", relationships={
        "bartender": {"trust_level": 3, "attitude": "neutral"}
    })
    target = _make_npc("bartender")
    counter = InteractionCounter()
    assert should_interact(initiator, target, GameTime(day=1, hour=12), counter) is False


def test_should_interact_passes():
    initiator = _make_npc("farmer", relationships={
        "bartender": {"trust_level": 8, "attitude": "friendly"}
    })
    target = _make_npc("bartender")
    counter = InteractionCounter()
    assert should_interact(initiator, target, GameTime(day=1, hour=12), counter) is True


def test_should_interact_exceeds_daily_limit():
    initiator = _make_npc("farmer", relationships={
        "bartender": {"trust_level": 8, "attitude": "friendly"}
    })
    target = _make_npc("bartender")
    counter = InteractionCounter()
    counter.increment(("bartender", "farmer"), day=1)
    counter.increment(("bartender", "farmer"), day=1)
    assert should_interact(initiator, target, GameTime(day=1, hour=12), counter) is False


def test_should_interact_target_not_idle():
    initiator = _make_npc("farmer", relationships={
        "bartender": {"trust_level": 8, "attitude": "friendly"}
    })
    target = _make_npc("bartender", status="active")
    counter = InteractionCounter()
    assert should_interact(initiator, target, GameTime(day=1, hour=12), counter) is False


@pytest.mark.asyncio
async def test_interaction_hook_execute_triggers_conversation():
    loc_reg = LocationRegistry(initial={"tavern": ["bartender"]})
    farmer = _make_npc("farmer", relationships={
        "bartender": {"trust_level": 8, "attitude": "friendly"}
    })
    bartender = _make_npc("bartender")
    npc_registry = {"farmer": farmer, "bartender": bartender}

    runner = AsyncMock()
    runner.run_conversation = AsyncMock()

    hook = InteractionHook(
        npc_registry=npc_registry,
        location_registry=loc_reg,
        interaction_runner=runner,
    )
    await hook.execute({
        "actor_id": "farmer",
        "location": "tavern",
        "game_time": GameTime(day=1, hour=12),
    })
    runner.run_conversation.assert_called_once()
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest tests/server/test_interaction_hook.py -v`
预期：FAIL，ModuleNotFoundError

- [ ] **步骤 3：实现 InteractionHook**

```python
# server/hooks/interaction_hook.py
from __future__ import annotations
from typing import Any, Dict, Tuple
from server.hooks.base import Hook
from server.models.game_time import GameTime
from server.core.location_registry import LocationRegistry


class InteractionCounter:
    def __init__(self):
        self._counts: Dict[Tuple, int] = {}

    def get_today_count(self, pair_key: Tuple[str, str], day: int) -> int:
        return self._counts.get((pair_key, day), 0)

    def increment(self, pair_key: Tuple[str, str], day: int) -> None:
        key = (pair_key, day)
        self._counts[key] = self._counts.get(key, 0) + 1


def should_interact(initiator, target, game_time: GameTime,
                    counter: InteractionCounter) -> bool:
    relationships = initiator.background.get("relationships", {})
    rel = relationships.get(target.id) if hasattr(target, 'id') else relationships.get(target.agent_id)
    if not rel:
        return False
    if not isinstance(rel, dict):
        return False
    if rel.get("trust_level", 0) < 4:
        return False
    pair_key = tuple(sorted([initiator.id, target.id]))
    if counter.get_today_count(pair_key, game_time.day) >= 2:
        return False
    if target.activity_state.status != "idle":
        return False
    return True


class InteractionHook(Hook):
    event = "post_move"

    def __init__(self, npc_registry: dict, location_registry: LocationRegistry,
                 interaction_runner):
        self.npc_registry = npc_registry
        self.location_registry = location_registry
        self.interaction_runner = interaction_runner
        self.counter = InteractionCounter()

    async def execute(self, context: Dict[str, Any]) -> None:
        actor_id = context["actor_id"]
        location = context["location"]
        game_time = context["game_time"]

        colocated_ids = self.location_registry.get_npcs_at(location) - {actor_id}
        initiator = self.npc_registry[actor_id]

        for target_id in colocated_ids:
            target = self.npc_registry.get(target_id)
            if not target:
                continue
            if should_interact(initiator, target, game_time, self.counter):
                await self.interaction_runner.run_conversation(
                    initiator=initiator,
                    target=target,
                    location=location,
                    game_time=game_time,
                )
                pair_key = tuple(sorted([actor_id, target_id]))
                self.counter.increment(pair_key, game_time.day)
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest tests/server/test_interaction_hook.py -v`
预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add server/hooks/interaction_hook.py tests/server/test_interaction_hook.py
git commit -m "feat: InteractionHook——NPC 到达地点后触发交互检测"
```

---

## 任务 6：InteractionRunner 多轮对话执行器

**文件：**
- 创建：`server/core/interaction_runner.py`

- [ ] **步骤 1：实现 InteractionRunner**

```python
# server/core/interaction_runner.py
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple
from server.models.game_time import GameTime
from server.llm.context_builder import ContextBuilder, BuildParams, ScenarioType


@dataclass
class ConversationResult:
    participants: Tuple[str, str]
    location: str
    dialogue: List[Dict[str, str]]
    summary: str
    game_time: GameTime


class InteractionRunner:
    def __init__(self, context_builder: ContextBuilder, llm_client):
        self.context_builder = context_builder
        self.llm_client = llm_client

    async def run_conversation(self, initiator, target,
                               location: str, game_time: GameTime) -> ConversationResult:
        from server.core.activity_manager import ActivityManager

        activity_mgr = ActivityManager()
        activity_mgr.transition_to_active(initiator.activity_state, "socializing", 1, game_time)
        activity_mgr.transition_to_active(target.activity_state, "socializing", 1, game_time)

        dialogue: List[Dict[str, str]] = []
        speakers = [initiator, target, initiator, target]

        for i, speaker in enumerate(speakers):
            listener = target if speaker is initiator else initiator
            is_last_turn = (i == 3)
            prompt = self._build_interaction_prompt(speaker, listener, dialogue, i, is_last_turn)

            rel = speaker.background.get("relationships", {}).get(listener.id, {})
            params = BuildParams(
                scenario=ScenarioType.NPC_INTERACTION,
                identity=speaker.identity,
                npc_state=speaker.state,
                world_state={"day": game_time.day, "hour": game_time.hour, "weather": "晴"},
                interlocutor={
                    "id": listener.id if hasattr(listener, 'id') else listener.agent_id,
                    "name": listener.identity.get("name", "某人"),
                    "summary": rel.get("shared_history", ""),
                },
                memory_files={
                    "agent_mem.md": speaker.memory._read("agent_mem.md"),
                },
                dialogue_history=[{"role": "assistant" if d["speaker"] == speaker.id else "user",
                                   "content": d["content"]} for d in dialogue],
                current_input=prompt,
                background=speaker.background,
            )
            build_result = self.context_builder.build(params)
            response = await self.llm_client.chat(build_result.messages)
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "...")

            if is_last_turn and "\n" in content:
                parts = content.rsplit("\n", 1)
                dialogue.append({"speaker": speaker.id, "content": parts[0].strip()})
                summary = parts[-1].strip()
            else:
                dialogue.append({"speaker": speaker.id, "content": content.strip()})
                summary = ""

        if not summary:
            summary = f"{initiator.identity.get('name', '')}和{listener.identity.get('name', '')}聊了几句。"

        self._write_results(initiator, target, dialogue, summary, game_time, location)

        return ConversationResult(
            participants=(initiator.id, target.id),
            location=location,
            dialogue=dialogue,
            summary=summary,
            game_time=game_time,
        )

    def _build_interaction_prompt(self, speaker, listener, dialogue, turn_index, is_last) -> str:
        listener_name = listener.identity.get("name", "某人")
        if turn_index == 0:
            base = f"你在当前地点遇到了{listener_name}。请自然地打个招呼或开启一段对话。只说一两句话。"
        elif turn_index % 2 == 0:
            base = f"继续和{listener_name}的对话。只说一两句话。"
        else:
            base = f"{speaker.identity.get('name', '你')}，{listener_name}对你说了话，请自然地回应。只说一两句话。"

        if is_last:
            base += "\n\n在你的回复最后另起一行，用一句话总结这次对话的要点（格式：[总结] ...）。"
        return base

    def _write_results(self, initiator, target, dialogue, summary, game_time, location) -> None:
        log_entry = f"{game_time.hour}:00 socializing — 在{location}与"
        for npc in [initiator, target]:
            other = target if npc is initiator else initiator
            other_name = other.identity.get("name", other.id)
            entry = f"{log_entry}{other_name}交谈：{summary}"
            npc.activity_log.append(entry)
            if not hasattr(npc, "recent_social"):
                npc.recent_social = []
            npc.recent_social.append({
                "day": game_time.day,
                "hour": game_time.hour,
                "partner": other_name,
                "summary": summary,
            })
```

- [ ] **步骤 2：Commit**

```bash
git add server/core/interaction_runner.py
git commit -m "feat: InteractionRunner 多轮 NPC 对话执行器"
```

---

## 任务 7：Orchestrator 集成

**文件：**
- 修改：`server/core/orchestrator.py`

- [ ] **步骤 1：在 __init__ 中初始化新模块**

在 `orchestrator.py` 的 `__init__` 方法中，`self._init_npcs()` 之后添加：

```python
# 在 self._init_npcs() 之后
self._init_event_system()
self._init_location_registry()
self._init_hooks()
```

并添加对应方法：

```python
def _init_event_system(self) -> None:
    from server.core.event_engine import EventEngine, EventState, load_event_defs

    saved = self.store.load("event_state")
    if saved:
        from server.core.event_engine import ActiveEvent
        state = EventState(
            active_events=[ActiveEvent(**e) for e in saved.get("active_events", [])],
            cooldowns=saved.get("cooldowns", {}),
        )
    else:
        state = EventState()
    event_defs = load_event_defs("server/data/events")
    self.event_engine = EventEngine(event_defs=event_defs, state=state)

def _init_location_registry(self) -> None:
    from server.core.location_registry import LocationRegistry

    saved = self.store.load("locations")
    if saved:
        self.location_registry = LocationRegistry(initial=saved)
    else:
        initial = {npc.location: [npc_id] for npc_id, npc in self.npcs.items()}
        merged = {}
        for npc_id, npc in self.npcs.items():
            merged.setdefault(npc.location, []).append(npc_id)
        self.location_registry = LocationRegistry(initial=merged)

def _init_hooks(self) -> None:
    from server.hooks import HookRegistry
    from server.hooks.interaction_hook import InteractionHook
    from server.core.interaction_runner import InteractionRunner
    from server.llm.context_builder import ContextBuilder
    from server.llm.client import get_llm_client
    from server.config import config as game_config

    self.hook_registry = HookRegistry()
    builder = ContextBuilder.from_config(game_config)
    runner = InteractionRunner(context_builder=builder, llm_client=get_llm_client())
    interaction_hook = InteractionHook(
        npc_registry=self.npcs,
        location_registry=self.location_registry,
        interaction_runner=runner,
    )
    self.hook_registry.register(interaction_hook)
```

- [ ] **步骤 2：在 _on_hour_tick 中调用 event_engine**

在 `_on_hour_tick` 的"步骤 0"广播时间之后，添加事件引擎 tick：

```python
# 步骤 0.5: 事件引擎 tick
prev_events = [e.id for e in self.event_engine.state.active_events]
self.event_engine.tick(game_time)
curr_events = [e.id for e in self.event_engine.state.active_events]
if prev_events != curr_events:
    _broadcast({
        "type": "world_events_update",
        "events": [
            {"id": e.id, "name": e.name, "description": e.description,
             "started_hour": e.started_hour}
            for e in self.event_engine.state.active_events
        ],
    })
```

- [ ] **步骤 3：修改 _single_autonomous_turn 中的 world_state 构建**

替换硬编码的 world_state：

```python
# 替换原有的 world_state 硬编码
world_state = {
    "day": game_time.day,
    "hour": game_time.hour,
    "weather": self.event_engine.get_current_weather(),
    "events": self.event_engine.get_world_events_text(),
}
```

- [ ] **步骤 4：修改 move 处理逻辑**

在 `_single_autonomous_turn` 中，将 move 后的处理替换为：

```python
if tool_name == "move" and result.get("tool_result"):
    new_loc = result["tool_result"].get("state_changes", {}).get("location")
    if new_loc:
        old_loc = self.location_registry.get_location(npc_id)
        self.location_registry.move(npc_id, old_loc, new_loc)
        npc.location = new_loc
        await self.hook_registry.fire("post_move", {
            "actor_id": npc_id,
            "location": new_loc,
            "game_time": game_time,
        })
```

- [ ] **步骤 5：扩展 _auto_save**

```python
def _auto_save(self) -> None:
    self.store.save("world_state", {
        "game_time": self.time_system.game_time.to_dict(),
        "is_paused": self.time_system.is_paused,
    })
    self.store.save("player_state", self.player_state.__dict__)
    self.store.save("locations", self.location_registry.to_dict())
    self.store.save("event_state", {
        "active_events": [
            {"id": e.id, "name": e.name, "description": e.description,
             "started_day": e.started_day, "started_hour": e.started_hour,
             "expires_day": e.expires_day, "expires_hour": e.expires_hour}
            for e in self.event_engine.state.active_events
        ],
        "cooldowns": self.event_engine.state.cooldowns,
    })
```

- [ ] **步骤 6：同步修改 routes.py 中的 world_state 构建**

在 `server/api/routes.py` 的 `_build_messages` 函数中，替换硬编码：

```python
world_state = {
    "day": orch_mod.orch.time_system.game_time.day,
    "hour": orch_mod.orch.time_system.game_time.hour,
    "weather": orch_mod.orch.event_engine.get_current_weather(),
    "events": orch_mod.orch.event_engine.get_world_events_text(),
}
```

- [ ] **步骤 7：运行现有测试确保无回归**

运行：`pytest tests/ -v --timeout=30`
预期：全部 PASS（或跳过需要 LLM 的集成测试）

- [ ] **步骤 8：Commit**

```bash
git add server/core/orchestrator.py server/api/routes.py
git commit -m "feat: Orchestrator 集成 EventEngine + LocationRegistry + HookRegistry"
```

---

## 任务 8：Prompt 注入变化

**文件：**
- 修改：`server/tools/setup.py`

- [ ] **步骤 1：修改 build_autonomous_context 函数**

在 `server/tools/setup.py` 中，替换 `build_autonomous_context` 函数为：

```python
def build_autonomous_context(agent, game_time, location_registry=None, event_engine=None) -> str:
    """构建 NPC 自主决策时的 current_input 文本。"""
    location_cn = LOCATION_NAMES.get(agent.location, agent.location)
    idle_reason = agent.activity_state.idle_reason

    if idle_reason is None:
        status_text = "刚起床" if game_time.hour == 6 else "空闲"
        last_activity_text = ""
    else:
        status_text = "空闲"
        last_activity_text = f"\n上一个活动：{idle_reason}"

    # 今日活动日志
    if agent.activity_log:
        today_log = "\n【今日已完成】\n" + "\n".join(agent.activity_log)
    else:
        today_log = "\n【今日已完成】\n（刚开始新的一天）"

    # 近日回顾（最近2天的 daily_summary）
    recent = agent.memory.read_recent_summaries(game_time.day, count=2)
    recent_section = f"\n【近日回顾】\n{recent}" if recent else ""

    # 当前环境
    env_parts = []
    if event_engine:
        weather = event_engine.get_current_weather()
        events_text = event_engine.get_world_events_text()
        env_parts.append(f"天气：{weather}")
        if events_text != "今日无事":
            env_parts.append(f"今日事件：{events_text}")
    env_parts.append(f"当前地点：{location_cn}")
    if location_registry:
        colocated = location_registry.get_npcs_at(agent.location) - {agent.agent_id}
        if colocated:
            names = [_get_npc_name(nid) for nid in colocated]
            env_parts.append(f"同处此地的人：{'、'.join(names)}")
    env_section = "\n【当前环境】\n" + "\n".join(env_parts)

    # 近期社交
    social_section = ""
    if hasattr(agent, "recent_social") and agent.recent_social:
        social_lines = []
        for s in agent.recent_social[-3:]:
            social_lines.append(f"Day {s['day']} {s['hour']}:00 — 与{s['partner']}交谈：{s['summary']}")
        social_section = "\n【近期社交】\n" + "\n".join(social_lines)

    return (
        f"【行动指令】\n"
        f"当前时间：Day {game_time.day}, {game_time.hour}:00\n"
        f"你的状态：{status_text}"
        f"{last_activity_text}"
        f"{env_section}"
        f"{today_log}"
        f"{recent_section}"
        f"{social_section}\n"
        f"你正在独自思考接下来做什么，不需要说话或与任何人对话。"
        f"请直接调用一个工具，不要生成对话文本。"
    )


# NPC ID → 中文名映射（用于社交信息）
_NPC_NAMES = {
    "farmer": "农夫·乔治",
    "bartender": "酒馆老板·Gus",
}


def _get_npc_name(npc_id: str) -> str:
    return _NPC_NAMES.get(npc_id, npc_id)
```

- [ ] **步骤 2：更新 orchestrator 中的调用**

在 `orchestrator.py` 的 `_single_autonomous_turn` 中，将：
```python
autonomous_input = build_autonomous_context(npc, game_time)
```
替换为：
```python
autonomous_input = build_autonomous_context(
    npc, game_time,
    location_registry=self.location_registry,
    event_engine=self.event_engine,
)
```

- [ ] **步骤 3：运行测试**

运行：`pytest tests/ -v --timeout=30`
预期：全部 PASS

- [ ] **步骤 4：Commit**

```bash
git add server/tools/setup.py server/core/orchestrator.py
git commit -m "feat: 自主决策 prompt 注入环境信息和近期社交"
```

---

## 任务 9：前端事件展示

**文件：**
- 修改：`client/src/stores/observeStore.ts`
- 修改：`client/src/pages/ObservePage.vue`
- 修改：`server/api/routes.py`

- [ ] **步骤 1：修改 observeStore.ts**

在 `observeStore.ts` 中添加 worldEvents 状态和处理：

在 `export interface` 区域后添加：
```typescript
export interface WorldEvent {
  id: string
  name: string
  description: string
  started_hour: number
}
```

在 store 函数体中，`const gameTime` 之后添加：
```typescript
const worldEvents = ref<WorldEvent[]>([])
```

在 `fetchInitialStatus` 中，`gameTime.value = data.game_time` 之后添加：
```typescript
if (data.world_events) {
  worldEvents.value = data.world_events
}
```

在 `handleMessage` 函数的 `game_time_update` case 之后添加：
```typescript
if (msg.type === 'world_events_update') {
  worldEvents.value = msg.events || []
  return
}
```

在 return 中添加 `worldEvents`：
```typescript
return { npcs, gameTime, wsConnected, worldEvents, fetchInitialStatus, connectWebSocket, disconnect }
```

- [ ] **步骤 2：修改 ObservePage.vue 模板**

在 `</header>` 和 `<div class="observe-grid">` 之间插入：

```html
<div class="event-banner">
  <span class="event-banner-title">当前事件</span>
  <div class="event-tags">
    <span v-if="worldEvents.length === 0" class="event-tag event-tag--empty">今日无事</span>
    <span v-for="evt in worldEvents" :key="evt.id" class="event-tag">
      {{ evt.name }}（{{ evt.started_hour }}:00 起）
    </span>
  </div>
</div>
```

在 `<script setup>` 中，从 store 解构添加 `worldEvents`：
```typescript
const { npcs, gameTime, wsConnected, worldEvents } = storeToRefs(store)
```

- [ ] **步骤 3：添加 event-banner 样式**

在 `<style scoped>` 中添加：

```css
.event-banner {
  background: var(--color-panel);
  border: 2px solid var(--color-border);
  padding: var(--gap-sm) var(--gap-md);
  margin-bottom: var(--gap-md);
  display: flex;
  align-items: center;
  gap: var(--gap-md);
}

.event-banner-title {
  font-family: var(--font-pixel);
  font-size: var(--font-size-xs);
  color: var(--color-text);
  white-space: nowrap;
}

.event-tags {
  display: flex;
  flex-wrap: wrap;
  gap: var(--gap-sm);
}

.event-tag {
  font-family: var(--font-pixel);
  font-size: 10px;
  padding: 2px 8px;
  border: 1px solid var(--color-accent);
  color: var(--color-accent);
}

.event-tag--empty {
  border-color: var(--color-border);
  color: var(--color-border);
}
```

- [ ] **步骤 4：修改 API 响应包含 active events**

在 `server/api/routes.py` 的 `get_npcs_status` 函数中，return 前添加 world_events：

```python
@router.get("/npcs/status")
def get_npcs_status():
    """返回所有 NPC 的当前快照（供观察页面使用）。"""
    game_time = orch_mod.orch.time_system.game_time
    npcs_data = {}
    for npc_id, npc in orch_mod.orch.npcs.items():
        npcs_data[npc_id] = {
            "name": npc.identity.get("name", npc_id),
            "location": npc.location,
            "activity": {
                "status": npc.activity_state.status,
                "current_tool": npc.activity_state.current_tool,
                "end_day": npc.activity_state.end_day,
                "end_hour": npc.activity_state.end_hour,
                "idle_reason": npc.activity_state.idle_reason,
            },
            "state": {
                "health": npc.state.health,
                "hunger": npc.state.hunger,
                "fatigue": npc.state.fatigue,
                "mood": npc.state.mood,
            },
            "llm_status": "idle",
            "history": [],
        }

    world_events = [
        {"id": e.id, "name": e.name, "description": e.description, "started_hour": e.started_hour}
        for e in orch_mod.orch.event_engine.state.active_events
    ]

    return {
        "npcs": npcs_data,
        "game_time": game_time.to_dict(),
        "world_events": world_events,
    }
```

- [ ] **步骤 5：启动前后端验证**

运行后端：`python -m uvicorn server.main:app --reload`
运行前端：`cd client && npm run dev`
在浏览器打开观察页面，确认事件 banner 显示正常。

- [ ] **步骤 6：Commit**

```bash
git add client/src/stores/observeStore.ts client/src/pages/ObservePage.vue server/api/routes.py
git commit -m "feat: 前端观察面板展示全局事件 banner"
```

---

## 任务 10：端到端验证

- [ ] **步骤 1：运行全部测试**

```bash
pytest tests/ -v --timeout=30
```

预期：全部 PASS

- [ ] **步骤 2：手动验证事件生成**

启动服务后快进时间到 Day 2+，观察：
- 控制台是否打印事件激活信息
- 观察面板是否显示事件 banner
- NPC 决策 prompt 中是否包含天气和事件信息

- [ ] **步骤 3：手动验证 NPC 交互**

使 NPC 移动到相同地点（可通过快进等待 NPC 自行移动，或临时提高 move 概率），观察：
- 控制台是否打印交互触发信息
- 双方 activity_log 是否包含社交记录
- 后续决策 prompt 是否包含"近期社交"

- [ ] **步骤 4：最终 Commit**

```bash
git add -A
git commit -m "feat: 事件引擎 + NPC 交互系统完整实现"
```
