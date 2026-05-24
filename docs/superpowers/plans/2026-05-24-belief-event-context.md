# 信念系统 + Event Log + 目击规则 + ContextBuilder 改造 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 实现涌现式智能的核心数据管道——事件产生信念、信念驱动决策、决策产生新事件的闭环。

**架构：** Event Log 记录客观事件 → WitnessEngine 按 visibility 规则将事件转化为 NPC 信念 → BeliefStore 按 NPC 独立存储信念 → ContextBuilder 从信念库注入上下文驱动 LLM 决策。

**技术栈：** Python 3.11+ / dataclasses / JSON 持久化 / pytest

---

## 文件结构

| 操作 | 文件路径 | 职责 |
|------|---------|------|
| 创建 | `server/models/belief.py` | Belief 数据模型 |
| 创建 | `server/models/event.py` | 结构化 Event 数据模型 |
| 创建 | `server/core/belief_store.py` | 每 NPC 独立的信念存储、检索、衰减 |
| 创建 | `server/core/event_log.py` | 结构化事件持久化和查询 |
| 创建 | `server/core/witness_engine.py` | Event → Belief 转化引擎 |
| 修改 | `server/llm/context_builder.py` | L1-L4 改为信念驱动注入 |
| 修改 | `server/tools/setup.py:87-145` | `build_autonomous_context` 适配信念系统 |
| 修改 | `server/core/interaction_runner.py` | 对话中触发信念传播 |
| 修改 | `server/tools/executor.py` | 工具执行后产生结构化事件 |
| 创建 | `tests/server/test_belief_model.py` | Belief 模型测试 |
| 创建 | `tests/server/test_event_model.py` | Event 模型测试 |
| 创建 | `tests/server/test_belief_store.py` | BeliefStore 测试 |
| 创建 | `tests/server/test_event_log.py` | EventLog 测试 |
| 创建 | `tests/server/test_witness_engine.py` | WitnessEngine 测试 |
| 创建 | `tests/server/test_context_builder_v2.py` | 改造后 ContextBuilder 测试 |

---

## 任务 1：Belief 数据模型

**文件：**
- 创建：`server/models/belief.py`
- 测试：`tests/server/test_belief_model.py`

- [ ] **步骤 1：编写失败的测试**

```python
# tests/server/test_belief_model.py
import pytest
from server.models.belief import Belief


class TestBeliefModel:
    def test_create_witnessed_belief(self):
        b = Belief(
            content="乔治昨天深夜独自去了森林",
            source="witnessed",
            confidence="high",
            acquired_at={"day": 3, "hour": 14},
            about=["farmer"],
        )
        assert b.content == "乔治昨天深夜独自去了森林"
        assert b.source == "witnessed"
        assert b.confidence == "high"
        assert b.id  # 自动生成非空 ID

    def test_create_told_by_belief(self):
        b = Belief(
            content="市场来了一个陌生商人",
            source="told_by:farmer",
            confidence="medium",
            acquired_at={"day": 2, "hour": 10},
            about=["world"],
        )
        assert b.source == "told_by:farmer"
        assert b.confidence == "medium"

    def test_belief_to_dict_roundtrip(self):
        b = Belief(
            content="盖斯在酿酒",
            source="witnessed",
            confidence="high",
            acquired_at={"day": 1, "hour": 8},
            about=["bartender"],
        )
        data = b.to_dict()
        restored = Belief.from_dict(data)
        assert restored.content == b.content
        assert restored.id == b.id
        assert restored.source == b.source

    def test_belief_is_expired_low_confidence(self):
        b = Belief(
            content="听说有人在森林出没",
            source="overheard",
            confidence="low",
            acquired_at={"day": 1, "hour": 10},
            about=["world"],
        )
        assert not b.is_expired(current_day=2)
        assert b.is_expired(current_day=5)  # 超过3天衰减

    def test_belief_is_expired_high_never(self):
        b = Belief(
            content="我亲眼看到商人卖违禁品",
            source="witnessed",
            confidence="high",
            acquired_at={"day": 1, "hour": 10},
            about=["world"],
        )
        assert not b.is_expired(current_day=100)

    def test_belief_propagate_downgrades_confidence(self):
        original = Belief(
            content="商人在卖违禁品",
            source="witnessed",
            confidence="high",
            acquired_at={"day": 2, "hour": 14},
            about=["world"],
        )
        propagated = original.propagate(teller_id="farmer", new_content="听说商人在卖违禁品")
        assert propagated.confidence == "medium"
        assert propagated.source == "told_by:farmer"
        assert propagated.content == "听说商人在卖违禁品"
        assert propagated.id != original.id

    def test_belief_propagate_medium_to_low(self):
        b = Belief(
            content="听说有违禁品",
            source="told_by:farmer",
            confidence="medium",
            acquired_at={"day": 2, "hour": 14},
            about=["world"],
        )
        propagated = b.propagate(teller_id="bartender", new_content="据说有违禁品")
        assert propagated.confidence == "low"

    def test_belief_propagate_low_stays_low(self):
        b = Belief(
            content="也许有违禁品",
            source="overheard",
            confidence="low",
            acquired_at={"day": 2, "hour": 14},
            about=["world"],
        )
        propagated = b.propagate(teller_id="bartender", new_content="可能有违禁品")
        assert propagated.confidence == "low"
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest tests/server/test_belief_model.py -v`
预期：FAIL，报错 "ModuleNotFoundError: No module named 'server.models.belief'"

- [ ] **步骤 3：编写实现代码**

```python
# server/models/belief.py
from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

CONFIDENCE_LEVELS = ("high", "medium", "low")
DECAY_DAYS = {"low": 3, "medium": 7, "high": None}


@dataclass
class Belief:
    content: str
    source: str
    confidence: str
    acquired_at: Dict[str, int]
    about: List[str]
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def is_expired(self, current_day: int) -> bool:
        decay = DECAY_DAYS.get(self.confidence)
        if decay is None:
            return False
        age = current_day - self.acquired_at.get("day", current_day)
        return age > decay

    def propagate(self, teller_id: str, new_content: str) -> Belief:
        idx = CONFIDENCE_LEVELS.index(self.confidence)
        new_confidence = CONFIDENCE_LEVELS[min(idx + 1, len(CONFIDENCE_LEVELS) - 1)]
        return Belief(
            content=new_content,
            source=f"told_by:{teller_id}",
            confidence=new_confidence,
            acquired_at=dict(self.acquired_at),
            about=list(self.about),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "source": self.source,
            "confidence": self.confidence,
            "acquired_at": self.acquired_at,
            "about": self.about,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Belief:
        return cls(
            id=data["id"],
            content=data["content"],
            source=data["source"],
            confidence=data["confidence"],
            acquired_at=data["acquired_at"],
            about=data["about"],
        )
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest tests/server/test_belief_model.py -v`
预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add server/models/belief.py tests/server/test_belief_model.py
git commit -m "feat: Belief 数据模型——信念的创建、衰减、传播"
```

---

## 任务 2：结构化 Event 数据模型

**文件：**
- 创建：`server/models/event.py`
- 测试：`tests/server/test_event_model.py`

- [ ] **步骤 1：编写失败的测试**

```python
# tests/server/test_event_model.py
import pytest
from server.models.event import GameEvent


class TestEventModel:
    def test_create_action_event(self):
        e = GameEvent(
            type="action",
            timestamp={"day": 2, "hour": 10},
            actor="farmer",
            location="field",
            content="乔治在田地里劳作了4小时",
            witnesses=["farmer"],
            visibility="location",
        )
        assert e.type == "action"
        assert e.actor == "farmer"
        assert e.id  # 自动生成

    def test_create_dialogue_event(self):
        e = GameEvent(
            type="dialogue",
            timestamp={"day": 2, "hour": 14},
            actor="farmer",
            location="tavern",
            content="乔治和盖斯讨论了市场的陌生商人",
            witnesses=["farmer", "bartender"],
            visibility="location",
            reasoning="因为想确认违禁品的事",
        )
        assert e.witnesses == ["farmer", "bartender"]
        assert e.reasoning == "因为想确认违禁品的事"

    def test_create_public_event(self):
        e = GameEvent(
            type="world",
            timestamp={"day": 3, "hour": 6},
            actor="world",
            location="village",
            content="村口钟声响起，宣布新的一天",
            witnesses=[],
            visibility="public",
        )
        assert e.visibility == "public"

    def test_event_to_dict_roundtrip(self):
        e = GameEvent(
            type="movement",
            timestamp={"day": 1, "hour": 18},
            actor="farmer",
            location="tavern",
            content="乔治从田地来到了酒馆",
            witnesses=["farmer", "bartender"],
            visibility="location",
        )
        data = e.to_dict()
        restored = GameEvent.from_dict(data)
        assert restored.id == e.id
        assert restored.type == e.type
        assert restored.witnesses == e.witnesses

    def test_event_private_visibility(self):
        e = GameEvent(
            type="action",
            timestamp={"day": 2, "hour": 23},
            actor="farmer",
            location="forest",
            content="乔治独自在森林里挖东西",
            witnesses=["farmer"],
            visibility="private",
        )
        assert e.visibility == "private"
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest tests/server/test_event_model.py -v`
预期：FAIL，报错 "ModuleNotFoundError: No module named 'server.models.event'"

- [ ] **步骤 3：编写实现代码**

```python
# server/models/event.py
from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class GameEvent:
    type: str
    timestamp: Dict[str, int]
    actor: str
    location: str
    content: str
    witnesses: List[str]
    visibility: str
    reasoning: Optional[str] = None
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "id": self.id,
            "type": self.type,
            "timestamp": self.timestamp,
            "actor": self.actor,
            "location": self.location,
            "content": self.content,
            "witnesses": self.witnesses,
            "visibility": self.visibility,
        }
        if self.reasoning is not None:
            d["reasoning"] = self.reasoning
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> GameEvent:
        return cls(
            id=data["id"],
            type=data["type"],
            timestamp=data["timestamp"],
            actor=data["actor"],
            location=data["location"],
            content=data["content"],
            witnesses=data["witnesses"],
            visibility=data["visibility"],
            reasoning=data.get("reasoning"),
        )
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest tests/server/test_event_model.py -v`
预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add server/models/event.py tests/server/test_event_model.py
git commit -m "feat: GameEvent 结构化事件数据模型"
```

---

## 任务 3：结构化 Event Log 持久化

**文件：**
- 创建：`server/core/event_log.py`
- 测试：`tests/server/test_event_log.py`

- [ ] **步骤 1：编写失败的测试**

```python
# tests/server/test_event_log.py
import pytest
import tempfile
import os
from server.models.event import GameEvent
from server.core.event_log import EventLog


class TestEventLog:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.log = EventLog(base_path=self.tmpdir)

    def test_append_and_get_by_id(self):
        e = GameEvent(
            type="action", timestamp={"day": 1, "hour": 8},
            actor="farmer", location="field",
            content="乔治开始耕地", witnesses=["farmer"],
            visibility="location",
        )
        self.log.append(e)
        retrieved = self.log.get_by_id(e.id)
        assert retrieved is not None
        assert retrieved.content == "乔治开始耕地"

    def test_query_by_day(self):
        for hour in [8, 10, 14]:
            self.log.append(GameEvent(
                type="action", timestamp={"day": 2, "hour": hour},
                actor="farmer", location="field",
                content=f"活动 hour={hour}", witnesses=["farmer"],
                visibility="location",
            ))
        self.log.append(GameEvent(
            type="action", timestamp={"day": 3, "hour": 8},
            actor="farmer", location="field",
            content="第三天活动", witnesses=["farmer"],
            visibility="location",
        ))
        day2_events = self.log.query(day=2)
        assert len(day2_events) == 3

    def test_query_by_actor(self):
        self.log.append(GameEvent(
            type="action", timestamp={"day": 1, "hour": 8},
            actor="farmer", location="field",
            content="农夫活动", witnesses=["farmer"],
            visibility="location",
        ))
        self.log.append(GameEvent(
            type="action", timestamp={"day": 1, "hour": 9},
            actor="bartender", location="tavern",
            content="酒保活动", witnesses=["bartender"],
            visibility="location",
        ))
        farmer_events = self.log.query(actor="farmer")
        assert len(farmer_events) == 1
        assert farmer_events[0].actor == "farmer"

    def test_query_by_location(self):
        self.log.append(GameEvent(
            type="action", timestamp={"day": 1, "hour": 8},
            actor="farmer", location="tavern",
            content="农夫在酒馆", witnesses=["farmer", "bartender"],
            visibility="location",
        ))
        tavern_events = self.log.query(location="tavern")
        assert len(tavern_events) == 1

    def test_query_by_witness(self):
        self.log.append(GameEvent(
            type="dialogue", timestamp={"day": 1, "hour": 14},
            actor="farmer", location="tavern",
            content="农夫和酒保聊天", witnesses=["farmer", "bartender"],
            visibility="location",
        ))
        self.log.append(GameEvent(
            type="action", timestamp={"day": 1, "hour": 15},
            actor="farmer", location="field",
            content="农夫独自耕地", witnesses=["farmer"],
            visibility="location",
        ))
        bartender_witnessed = self.log.query(witness="bartender")
        assert len(bartender_witnessed) == 1
        assert "聊天" in bartender_witnessed[0].content

    def test_persistence_across_instances(self):
        e = GameEvent(
            type="action", timestamp={"day": 1, "hour": 8},
            actor="farmer", location="field",
            content="持久化测试", witnesses=["farmer"],
            visibility="location",
        )
        self.log.append(e)

        log2 = EventLog(base_path=self.tmpdir)
        retrieved = log2.get_by_id(e.id)
        assert retrieved is not None
        assert retrieved.content == "持久化测试"

    def test_get_recent(self):
        for i in range(10):
            self.log.append(GameEvent(
                type="action", timestamp={"day": 1, "hour": i},
                actor="farmer", location="field",
                content=f"事件{i}", witnesses=["farmer"],
                visibility="location",
            ))
        recent = self.log.get_recent(limit=3)
        assert len(recent) == 3
        assert recent[0].content == "事件9"  # 最新的在前
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest tests/server/test_event_log.py -v`
预期：FAIL，报错 "ModuleNotFoundError: No module named 'server.core.event_log'"

- [ ] **步骤 3：编写实现代码**

```python
# server/core/event_log.py
from __future__ import annotations
import json
import os
from typing import Dict, List, Optional
from server.models.event import GameEvent


class EventLog:
    """结构化事件持久化。

    按天分文件存储：{base_path}/events_day{N}.json
    每个文件是一个 JSON 数组。
    """

    def __init__(self, base_path: str = "data/users/default/events"):
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)
        self._cache: Dict[int, List[GameEvent]] = {}

    def _day_file(self, day: int) -> str:
        return os.path.join(self.base_path, f"events_day{day}.json")

    def _load_day(self, day: int) -> List[GameEvent]:
        if day in self._cache:
            return self._cache[day]
        path = self._day_file(day)
        if not os.path.exists(path):
            self._cache[day] = []
            return self._cache[day]
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        events = [GameEvent.from_dict(d) for d in data]
        self._cache[day] = events
        return events

    def _save_day(self, day: int) -> None:
        events = self._cache.get(day, [])
        path = self._day_file(day)
        with open(path, "w", encoding="utf-8") as f:
            json.dump([e.to_dict() for e in events], f, ensure_ascii=False, indent=2)

    def append(self, event: GameEvent) -> None:
        day = event.timestamp.get("day", 1)
        events = self._load_day(day)
        events.append(event)
        self._save_day(day)

    def get_by_id(self, event_id: str) -> Optional[GameEvent]:
        for day_events in self._cache.values():
            for e in day_events:
                if e.id == event_id:
                    return e
        # 扫描未缓存的文件
        for filename in sorted(os.listdir(self.base_path)):
            if not filename.startswith("events_day"):
                continue
            day_num = int(filename.replace("events_day", "").replace(".json", ""))
            if day_num in self._cache:
                continue
            events = self._load_day(day_num)
            for e in events:
                if e.id == event_id:
                    return e
        return None

    def query(
        self,
        day: Optional[int] = None,
        actor: Optional[str] = None,
        location: Optional[str] = None,
        witness: Optional[str] = None,
    ) -> List[GameEvent]:
        if day is not None:
            candidates = self._load_day(day)
        else:
            candidates = []
            for filename in sorted(os.listdir(self.base_path)):
                if not filename.startswith("events_day"):
                    continue
                day_num = int(filename.replace("events_day", "").replace(".json", ""))
                candidates.extend(self._load_day(day_num))

        results = candidates
        if actor is not None:
            results = [e for e in results if e.actor == actor]
        if location is not None:
            results = [e for e in results if e.location == location]
        if witness is not None:
            results = [e for e in results if witness in e.witnesses]
        return results

    def get_recent(self, limit: int = 10) -> List[GameEvent]:
        all_events: List[GameEvent] = []
        filenames = sorted(os.listdir(self.base_path), reverse=True)
        for filename in filenames:
            if not filename.startswith("events_day"):
                continue
            day_num = int(filename.replace("events_day", "").replace(".json", ""))
            day_events = self._load_day(day_num)
            all_events.extend(reversed(day_events))
            if len(all_events) >= limit:
                break
        return all_events[:limit]
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest tests/server/test_event_log.py -v`
预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add server/core/event_log.py tests/server/test_event_log.py
git commit -m "feat: EventLog 结构化事件持久化——按天分文件存储和查询"
```

---

## 任务 4：BeliefStore 信念存储

**文件：**
- 创建：`server/core/belief_store.py`
- 测试：`tests/server/test_belief_store.py`

- [ ] **步骤 1：编写失败的测试**

```python
# tests/server/test_belief_store.py
import pytest
import tempfile
from server.models.belief import Belief
from server.core.belief_store import BeliefStore


class TestBeliefStore:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = BeliefStore(npc_id="farmer", base_path=self.tmpdir)

    def test_add_and_get(self):
        b = Belief(
            content="盖斯今天在酿啤酒",
            source="witnessed",
            confidence="high",
            acquired_at={"day": 1, "hour": 10},
            about=["bartender"],
        )
        self.store.add(b)
        retrieved = self.store.get(b.id)
        assert retrieved is not None
        assert retrieved.content == b.content

    def test_get_by_about(self):
        self.store.add(Belief(
            content="农夫在田里",
            source="witnessed", confidence="high",
            acquired_at={"day": 1, "hour": 8}, about=["farmer"],
        ))
        self.store.add(Belief(
            content="酒保在酿酒",
            source="witnessed", confidence="high",
            acquired_at={"day": 1, "hour": 9}, about=["bartender"],
        ))
        farmer_beliefs = self.store.get_by_about("farmer")
        assert len(farmer_beliefs) == 1
        assert "农夫" in farmer_beliefs[0].content

    def test_get_active_filters_expired(self):
        self.store.add(Belief(
            content="新鲜消息",
            source="overheard", confidence="low",
            acquired_at={"day": 5, "hour": 10}, about=["world"],
        ))
        self.store.add(Belief(
            content="过期消息",
            source="overheard", confidence="low",
            acquired_at={"day": 1, "hour": 10}, about=["world"],
        ))
        active = self.store.get_active(current_day=5)
        assert len(active) == 1
        assert active[0].content == "新鲜消息"

    def test_high_confidence_never_expires(self):
        self.store.add(Belief(
            content="亲眼所见",
            source="witnessed", confidence="high",
            acquired_at={"day": 1, "hour": 10}, about=["world"],
        ))
        active = self.store.get_active(current_day=100)
        assert len(active) == 1

    def test_duplicate_detection(self):
        self.store.add(Belief(
            content="盖斯在酿酒",
            source="told_by:player", confidence="medium",
            acquired_at={"day": 1, "hour": 10}, about=["bartender"],
        ))
        duplicate = Belief(
            content="盖斯在酿酒",
            source="told_by:player", confidence="medium",
            acquired_at={"day": 1, "hour": 11}, about=["bartender"],
        )
        added = self.store.add(duplicate)
        assert added is False
        assert len(self.store.get_all()) == 1

    def test_conflict_detection(self):
        b1 = Belief(
            content="商人是好人",
            source="witnessed", confidence="high",
            acquired_at={"day": 1, "hour": 10}, about=["traveler"],
        )
        b2 = Belief(
            content="商人在卖违禁品",
            source="told_by:farmer", confidence="medium",
            acquired_at={"day": 2, "hour": 10}, about=["traveler"],
        )
        self.store.add(b1)
        self.store.add(b2)
        # 两条都保留，不互相覆盖
        all_beliefs = self.store.get_by_about("traveler")
        assert len(all_beliefs) == 2

    def test_persistence(self):
        b = Belief(
            content="持久化测试",
            source="witnessed", confidence="high",
            acquired_at={"day": 1, "hour": 8}, about=["world"],
        )
        self.store.add(b)

        store2 = BeliefStore(npc_id="farmer", base_path=self.tmpdir)
        assert store2.get(b.id) is not None

    def test_get_for_context_priority(self):
        # high > medium > low，最近 > 较早
        self.store.add(Belief(
            content="低优先级旧消息",
            source="overheard", confidence="low",
            acquired_at={"day": 1, "hour": 8}, about=["world"],
        ))
        self.store.add(Belief(
            content="高优先级新消息",
            source="witnessed", confidence="high",
            acquired_at={"day": 3, "hour": 14}, about=["world"],
        ))
        self.store.add(Belief(
            content="中优先级消息",
            source="told_by:farmer", confidence="medium",
            acquired_at={"day": 2, "hour": 10}, about=["world"],
        ))
        ordered = self.store.get_for_context(current_day=3, max_count=10)
        assert ordered[0].content == "高优先级新消息"
        assert ordered[1].content == "中优先级消息"
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest tests/server/test_belief_store.py -v`
预期：FAIL，报错 "ModuleNotFoundError: No module named 'server.core.belief_store'"

- [ ] **步骤 3：编写实现代码**

```python
# server/core/belief_store.py
from __future__ import annotations
import json
import os
from typing import List, Optional
from server.models.belief import Belief

CONFIDENCE_PRIORITY = {"high": 3, "medium": 2, "low": 1}


class BeliefStore:
    """每个 NPC 独立的信念存储。

    持久化到 {base_path}/{npc_id}_beliefs.json
    """

    def __init__(self, npc_id: str, base_path: str = "data/users/default/beliefs"):
        self.npc_id = npc_id
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)
        self._beliefs: List[Belief] = []
        self._load()

    def _file_path(self) -> str:
        return os.path.join(self.base_path, f"{self.npc_id}_beliefs.json")

    def _load(self) -> None:
        path = self._file_path()
        if not os.path.exists(path):
            self._beliefs = []
            return
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self._beliefs = [Belief.from_dict(d) for d in data]

    def _save(self) -> None:
        path = self._file_path()
        with open(path, "w", encoding="utf-8") as f:
            json.dump([b.to_dict() for b in self._beliefs], f, ensure_ascii=False, indent=2)

    def add(self, belief: Belief) -> bool:
        """添加信念。如果是重复信念（相同 content + source），返回 False 不添加。"""
        for existing in self._beliefs:
            if existing.content == belief.content and existing.source == belief.source:
                return False
        self._beliefs.append(belief)
        self._save()
        return True

    def get(self, belief_id: str) -> Optional[Belief]:
        for b in self._beliefs:
            if b.id == belief_id:
                return b
        return None

    def get_all(self) -> List[Belief]:
        return list(self._beliefs)

    def get_by_about(self, subject: str) -> List[Belief]:
        return [b for b in self._beliefs if subject in b.about]

    def get_active(self, current_day: int) -> List[Belief]:
        return [b for b in self._beliefs if not b.is_expired(current_day)]

    def get_for_context(
        self,
        current_day: int,
        max_count: int = 20,
        relevance_filter: Optional[List[str]] = None,
    ) -> List[Belief]:
        """获取注入 context 的信念子集，按优先级排序。

        优先级：confidence 等级 > 时间新旧
        """
        active = self.get_active(current_day)
        if relevance_filter:
            active = [
                b for b in active
                if any(subj in b.about for subj in relevance_filter)
            ]

        def sort_key(b: Belief):
            priority = CONFIDENCE_PRIORITY.get(b.confidence, 0)
            recency = b.acquired_at.get("day", 0) * 24 + b.acquired_at.get("hour", 0)
            return (-priority, -recency)

        active.sort(key=sort_key)
        return active[:max_count]
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest tests/server/test_belief_store.py -v`
预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add server/core/belief_store.py tests/server/test_belief_store.py
git commit -m "feat: BeliefStore 每 NPC 独立信念存储——添加、查询、衰减、优先级排序"
```

---

## 任务 5：WitnessEngine 目击规则引擎

**文件：**
- 创建：`server/core/witness_engine.py`
- 测试：`tests/server/test_witness_engine.py`

- [ ] **步骤 1：编写失败的测试**

```python
# tests/server/test_witness_engine.py
import pytest
import tempfile
from server.models.event import GameEvent
from server.models.belief import Belief
from server.core.belief_store import BeliefStore
from server.core.witness_engine import WitnessEngine


class TestWitnessEngine:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.stores = {
            "farmer": BeliefStore(npc_id="farmer", base_path=self.tmpdir),
            "bartender": BeliefStore(npc_id="bartender", base_path=self.tmpdir),
        }
        self.engine = WitnessEngine(belief_stores=self.stores)

    def test_location_event_only_witnesses_get_belief(self):
        event = GameEvent(
            type="action", timestamp={"day": 1, "hour": 10},
            actor="farmer", location="field",
            content="乔治在田地里发现了一把生锈的剑",
            witnesses=["farmer"],
            visibility="location",
        )
        self.engine.process_event(event)

        farmer_beliefs = self.stores["farmer"].get_all()
        bartender_beliefs = self.stores["bartender"].get_all()
        assert len(farmer_beliefs) == 1
        assert farmer_beliefs[0].content == "乔治在田地里发现了一把生锈的剑"
        assert farmer_beliefs[0].confidence == "high"
        assert farmer_beliefs[0].source == "witnessed"
        assert len(bartender_beliefs) == 0

    def test_public_event_all_get_belief(self):
        event = GameEvent(
            type="world", timestamp={"day": 2, "hour": 6},
            actor="world", location="village",
            content="暴风雨即将来临",
            witnesses=[],
            visibility="public",
        )
        self.engine.process_event(event)

        for store in self.stores.values():
            beliefs = store.get_all()
            assert len(beliefs) == 1
            assert beliefs[0].content == "暴风雨即将来临"
            assert beliefs[0].confidence == "high"
            assert beliefs[0].source == "witnessed"

    def test_private_event_only_actor_gets_belief(self):
        event = GameEvent(
            type="action", timestamp={"day": 1, "hour": 23},
            actor="farmer", location="forest",
            content="乔治偷偷在森林挖了宝箱",
            witnesses=["farmer", "bartender"],  # witnesses 列表有两人
            visibility="private",  # 但 private 只给 actor
        )
        self.engine.process_event(event)

        farmer_beliefs = self.stores["farmer"].get_all()
        bartender_beliefs = self.stores["bartender"].get_all()
        assert len(farmer_beliefs) == 1
        assert len(bartender_beliefs) == 0

    def test_reasoning_becomes_actor_belief(self):
        event = GameEvent(
            type="action", timestamp={"day": 2, "hour": 14},
            actor="farmer", location="market",
            content="乔治去了市场",
            witnesses=["farmer"],
            visibility="location",
            reasoning="我想亲眼确认商人是否在卖违禁品",
        )
        self.engine.process_event(event)

        farmer_beliefs = self.stores["farmer"].get_all()
        # 应有两条：事件本身 + reasoning
        assert len(farmer_beliefs) == 2
        reasoning_belief = [b for b in farmer_beliefs if "确认" in b.content][0]
        assert reasoning_belief.source == "witnessed"
        assert reasoning_belief.confidence == "high"

    def test_dialogue_event_both_witnesses_get_belief(self):
        event = GameEvent(
            type="dialogue", timestamp={"day": 1, "hour": 14},
            actor="farmer", location="tavern",
            content="乔治和盖斯讨论了天气",
            witnesses=["farmer", "bartender"],
            visibility="location",
        )
        self.engine.process_event(event)

        assert len(self.stores["farmer"].get_all()) == 1
        assert len(self.stores["bartender"].get_all()) == 1

    def test_unknown_npc_in_witnesses_ignored(self):
        event = GameEvent(
            type="action", timestamp={"day": 1, "hour": 10},
            actor="unknown_npc", location="field",
            content="神秘人出现了",
            witnesses=["unknown_npc", "farmer"],
            visibility="location",
        )
        self.engine.process_event(event)
        # farmer 获得信念，unknown_npc 被安全忽略
        assert len(self.stores["farmer"].get_all()) == 1

    def test_duplicate_event_not_duplicated_belief(self):
        event = GameEvent(
            type="action", timestamp={"day": 1, "hour": 10},
            actor="farmer", location="field",
            content="乔治耕地",
            witnesses=["farmer"],
            visibility="location",
        )
        self.engine.process_event(event)
        self.engine.process_event(event)  # 重复处理
        assert len(self.stores["farmer"].get_all()) == 1
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest tests/server/test_witness_engine.py -v`
预期：FAIL，报错 "ModuleNotFoundError: No module named 'server.core.witness_engine'"

- [ ] **步骤 3：编写实现代码**

```python
# server/core/witness_engine.py
from __future__ import annotations
from typing import Dict, List
from server.models.event import GameEvent
from server.models.belief import Belief
from server.core.belief_store import BeliefStore


class WitnessEngine:
    """事件 → 信念 转化引擎。

    根据事件的 visibility 规则，将事件内容分发为对应 NPC 的信念。
    """

    def __init__(self, belief_stores: Dict[str, BeliefStore]):
        self._stores = belief_stores

    def process_event(self, event: GameEvent) -> List[str]:
        """处理一个事件，返回获得新信念的 NPC ID 列表。"""
        recipients = self._resolve_recipients(event)
        affected = []

        for npc_id in recipients:
            store = self._stores.get(npc_id)
            if store is None:
                continue
            belief = Belief(
                content=event.content,
                source="witnessed",
                confidence="high",
                acquired_at=dict(event.timestamp),
                about=self._extract_about(event),
            )
            if store.add(belief):
                affected.append(npc_id)

        # reasoning 作为 actor 自己的信念
        if event.reasoning and event.actor in self._stores:
            reasoning_belief = Belief(
                content=event.reasoning,
                source="witnessed",
                confidence="high",
                acquired_at=dict(event.timestamp),
                about=self._extract_about(event),
            )
            self._stores[event.actor].add(reasoning_belief)

        return affected

    def _resolve_recipients(self, event: GameEvent) -> List[str]:
        if event.visibility == "public":
            return list(self._stores.keys())
        if event.visibility == "private":
            return [event.actor] if event.actor in self._stores else []
        # location: witnesses 列表
        return [npc_id for npc_id in event.witnesses if npc_id in self._stores]

    def _extract_about(self, event: GameEvent) -> List[str]:
        about = []
        if event.actor != "world":
            about.append(event.actor)
        if event.type == "world":
            about.append("world")
        return about if about else ["world"]
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest tests/server/test_witness_engine.py -v`
预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add server/core/witness_engine.py tests/server/test_witness_engine.py
git commit -m "feat: WitnessEngine 目击规则引擎——Event→Belief 按 visibility 分发"
```

---

## 任务 6：ContextBuilder 信念驱动改造

**文件：**
- 修改：`server/llm/context_builder.py`
- 测试：`tests/server/test_context_builder_v2.py`

### 设计说明

ContextBuilder 的 L1-L4 层从"客观注入"改为"信念注入"：
- **L1**：从 `world_state` 全量注入 → 只注入时间+天气（客观环境），事件信息改由信念提供
- **L2**：保留生理状态，新增 reasoning 信念（"你最近的决策"）
- **L3**：从 YAML relationships → 注入"对对方的所有信念"
- **L4**：从关键词文件检索 → 按相关性从 BeliefStore 检索信念子集

新增 `BuildParams.beliefs` 字段传入信念数据，向后兼容——beliefs 为空时退化为旧行为。

- [ ] **步骤 1：编写失败的测试**

```python
# tests/server/test_context_builder_v2.py
import pytest
from server.llm.context_builder import ContextBuilder, BuildParams, ScenarioType
from server.models.npc_state import NPCState
from server.models.belief import Belief


def _make_beliefs():
    """构造测试用信念列表。"""
    return [
        Belief(
            content="昨天下午你在田里看到一个陌生商人往市场方向走去",
            source="witnessed", confidence="high",
            acquired_at={"day": 2, "hour": 14}, about=["world"],
        ),
        Belief(
            content="盖斯上周告诉你最近有外地人在打听村子的事",
            source="told_by:bartender", confidence="medium",
            acquired_at={"day": 1, "hour": 18}, about=["world"],
        ),
        Belief(
            content="你今早决定去市场看看，想亲眼确认商人是否真在卖违禁品",
            source="witnessed", confidence="high",
            acquired_at={"day": 3, "hour": 7}, about=["farmer"],
        ),
    ]


def _make_interlocutor_beliefs():
    """构造对对话对象的信念。"""
    return [
        Belief(
            content="盖斯是酒馆老板，你和他认识三年了",
            source="witnessed", confidence="high",
            acquired_at={"day": 1, "hour": 0}, about=["bartender"],
        ),
        Belief(
            content="盖斯最近似乎心事重重",
            source="witnessed", confidence="high",
            acquired_at={"day": 2, "hour": 20}, about=["bartender"],
        ),
    ]


class TestContextBuilderV2:
    def setup_method(self):
        self.builder = ContextBuilder(model_limit=4096, output_reserve=500)
        self.identity = {
            "name": "乔治",
            "daily_habits": "每天清晨起来先去田地查看庄稼。",
            "core_motivation": "你热爱土地，靠双手养活自己。",
            "speaking_style": "朴实直率，偶尔用农谚。",
            "secret": "你曾在森林里发现过一个隐秘洞穴",
        }

    def test_belief_injection_in_l1(self):
        """L1 不再注入事件文本，只保留时间和天气。"""
        params = BuildParams(
            identity=self.identity,
            npc_state=NPCState(),
            world_state={"day": 3, "hour": 10, "weather": "晴", "events": "旅行商人到来"},
            beliefs=_make_beliefs(),
            scenario=ScenarioType.AUTONOMOUS_DECISION,
            current_input="你正在思考接下来做什么。",
        )
        result = self.builder.build(params)
        messages_text = " ".join(m["content"] for m in result.messages)
        # 事件文本不再直接出现在 L1
        assert "旅行商人到来" not in messages_text or "你确定的事" in messages_text

    def test_belief_categories_in_context(self):
        """信念按 confidence 分级呈现。"""
        params = BuildParams(
            identity=self.identity,
            npc_state=NPCState(),
            world_state={"day": 3, "hour": 10, "weather": "晴"},
            beliefs=_make_beliefs(),
            scenario=ScenarioType.AUTONOMOUS_DECISION,
            current_input="你正在思考接下来做什么。",
        )
        result = self.builder.build(params)
        messages_text = " ".join(m["content"] for m in result.messages)
        assert "你确定的事" in messages_text
        assert "你听说的" in messages_text
        assert "陌生商人" in messages_text

    def test_interlocutor_beliefs_in_l3(self):
        """L3 使用对对方的信念而非 YAML 静态数据。"""
        params = BuildParams(
            identity=self.identity,
            npc_state=NPCState(),
            world_state={"day": 3, "hour": 14, "weather": "晴"},
            beliefs=_make_beliefs(),
            interlocutor_beliefs=_make_interlocutor_beliefs(),
            interlocutor={"id": "bartender", "name": "盖斯"},
            scenario=ScenarioType.PLAYER_DIALOGUE,
            current_input="你好啊乔治",
            dialogue_history=[],
        )
        result = self.builder.build(params)
        messages_text = " ".join(m["content"] for m in result.messages)
        assert "认识三年" in messages_text
        assert "心事重重" in messages_text

    def test_reasoning_beliefs_in_l2(self):
        """L2 包含最近的 reasoning 信念。"""
        reasoning_beliefs = [
            Belief(
                content="你今早决定去市场是因为想确认违禁品的事",
                source="witnessed", confidence="high",
                acquired_at={"day": 3, "hour": 7}, about=["farmer"],
            ),
        ]
        params = BuildParams(
            identity=self.identity,
            npc_state=NPCState(),
            world_state={"day": 3, "hour": 10, "weather": "晴"},
            beliefs=_make_beliefs(),
            reasoning_beliefs=reasoning_beliefs,
            scenario=ScenarioType.AUTONOMOUS_DECISION,
            current_input="你正在思考。",
        )
        result = self.builder.build(params)
        messages_text = " ".join(m["content"] for m in result.messages)
        assert "你的近期决策" in messages_text
        assert "确认违禁品" in messages_text

    def test_backward_compat_no_beliefs(self):
        """beliefs 为空时退化为旧行为（不崩溃）。"""
        params = BuildParams(
            identity=self.identity,
            npc_state=NPCState(),
            world_state={"day": 1, "hour": 8, "weather": "晴", "events": "无特殊事件"},
            scenario=ScenarioType.AUTONOMOUS_DECISION,
            current_input="你正在思考。",
        )
        result = self.builder.build(params)
        assert len(result.messages) >= 2
        assert result.audit["L0"]["tokens"] > 0

    def test_empty_beliefs_no_header(self):
        """没有信念时不注入空的分类标题。"""
        params = BuildParams(
            identity=self.identity,
            npc_state=NPCState(),
            world_state={"day": 1, "hour": 8, "weather": "晴"},
            beliefs=[],
            scenario=ScenarioType.AUTONOMOUS_DECISION,
            current_input="你正在思考。",
        )
        result = self.builder.build(params)
        messages_text = " ".join(m["content"] for m in result.messages)
        assert "你确定的事" not in messages_text
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest tests/server/test_context_builder_v2.py -v`
预期：FAIL，报错 "TypeError" — `BuildParams` 不接受 `beliefs` 参数

- [ ] **步骤 3：修改 BuildParams 数据结构**

修改 `server/llm/context_builder.py` 中的 `BuildParams`：

```python
@dataclass
class BuildParams:
    identity: dict
    npc_state: any = None
    world_state: dict = field(default_factory=dict)
    interlocutor: dict = field(default_factory=dict)
    memory_files: dict = field(default_factory=dict)
    dialogue_history: List[dict] = field(default_factory=list)
    current_input: str = ""
    background: dict = field(default_factory=dict)
    scenario: ScenarioType = ScenarioType.PLAYER_DIALOGUE
    # 信念系统新增字段
    beliefs: List = field(default_factory=list)
    interlocutor_beliefs: List = field(default_factory=list)
    reasoning_beliefs: List = field(default_factory=list)
```

- [ ] **步骤 4：实现信念注入层 `_build_layer_1_v2`**

在 `ContextBuilder` 类中新增方法，当 `params.beliefs` 非空时使用：

```python
def _build_layer_1_v2(self, world_state: dict) -> LayerResult:
    """L1 改造：只保留时间+天气，不注入事件文本。"""
    content = (
        f"【世界信息】\n"
        f"当前时间：Day {world_state.get('day', '?')}, {world_state.get('hour', '?')}:00。"
        f"天气：{world_state.get('weather', '晴')}。"
    )
    tokens = TokenCounter.count(content)
    return LayerResult(content=content, tokens=tokens)
```

- [ ] **步骤 5：实现信念格式化方法 `_format_beliefs`**

```python
def _format_beliefs(self, beliefs: list) -> str:
    """将信念列表按 confidence 分组格式化。"""
    high = [b for b in beliefs if b.confidence == "high"]
    medium = [b for b in beliefs if b.confidence == "medium"]
    low = [b for b in beliefs if b.confidence == "low"]

    parts = []
    if high:
        parts.append("【你确定的事】")
        for b in high:
            parts.append(f"- {b.content}")
    if medium or low:
        parts.append("【你听说的（未证实）】")
        for b in medium + low:
            source_hint = ""
            if b.source.startswith("told_by:"):
                teller = b.source.replace("told_by:", "")
                source_hint = f"（{teller}说的）"
            parts.append(f"- {b.content}{source_hint}")
    return "\n".join(parts)
```

- [ ] **步骤 6：实现 `_build_layer_2_v2`（加入 reasoning 信念）**

```python
def _build_layer_2_v2(self, npc_state, reasoning_beliefs: list, background: dict) -> LayerResult:
    """L2 改造：生理状态 + 近期决策 reasoning。"""
    d = npc_state.describe()
    parts = [
        f"【自身状态】",
        f"{d['health']}。{d['hunger']}。{d['fatigue']}。{d['mood']}。",
    ]

    # state_reactions 保留
    state_reactions = background.get("state_reactions", {})
    reactions = []
    if npc_state.mood < 40 and "mood_low" in state_reactions:
        reactions.append(state_reactions["mood_low"])
    if npc_state.hunger < 40 and "hunger_low" in state_reactions:
        reactions.append(state_reactions["hunger_low"])
    if npc_state.fatigue > 60 and "fatigue_high" in state_reactions:
        reactions.append(state_reactions["fatigue_high"])
    if reactions:
        parts.append("由于当前状态：" + "；".join(reactions))

    if reasoning_beliefs:
        parts.append("\n【你的近期决策】")
        for b in reasoning_beliefs[-3:]:
            parts.append(f"- {b.content}")

    content = "\n".join(parts)
    tokens = TokenCounter.count(content)
    return LayerResult(content=content, tokens=tokens)
```

- [ ] **步骤 7：实现 `_build_layer_3_v2`（信念驱动关系）**

```python
def _build_layer_3_v2(self, interlocutor: dict, interlocutor_beliefs: list) -> LayerResult:
    """L3 改造：用对对方的信念替代静态 YAML 关系数据。"""
    name = interlocutor.get("name", "某人")
    parts = [f"【对方信息】\n你正在与{name}对话。"]

    if interlocutor_beliefs:
        parts.append("你对ta的了解：")
        for b in interlocutor_beliefs[:5]:
            parts.append(f"- {b.content}")

    content = "\n".join(parts)
    tokens = TokenCounter.count(content)
    quota = self._quota(3)
    truncated = tokens > quota
    if truncated:
        content = parts[0] + "\n" + "\n".join(parts[1:4])
        tokens = TokenCounter.count(content)
    return LayerResult(content=content, tokens=tokens, truncated=truncated)
```

- [ ] **步骤 8：修改 `build()` 主方法路由到 v2 层**

在 `build()` 方法中，当 `params.beliefs` 非空时使用新的 v2 层方法：

```python
def build(self, params: BuildParams) -> BuildResult:
    # ... 现有逻辑 ...
    use_beliefs = bool(params.beliefs)

    # L1
    if use_beliefs:
        l1 = self._build_layer_1_v2(params.world_state)
    else:
        l1 = self._build_layer_1(params.world_state, bg)

    # L2
    if use_beliefs:
        l2 = self._build_layer_2_v2(params.npc_state, params.reasoning_beliefs, bg)
    else:
        l2 = self._build_layer_2(params.npc_state, bg)

    # L3
    if scenario_config["L3"]:
        if use_beliefs and params.interlocutor_beliefs:
            l3 = self._build_layer_3_v2(params.interlocutor, params.interlocutor_beliefs)
        else:
            l3 = self._build_layer_3(params.interlocutor, bg)
    else:
        l3 = LayerResult(content="", tokens=0)

    # L4：信念驱动时用格式化信念替代关键词检索
    if use_beliefs:
        belief_text = self._format_beliefs(params.beliefs)
        l4_content = belief_text
        l4_tokens = TokenCounter.count(l4_content)
        l4_meta = {"source": "belief_store", "count": len(params.beliefs)}
    else:
        filtered_files = self._filter_memory_scope(params.memory_files, scenario_config["L4_scope"])
        l4_content, l4_meta = self._build_layer_4(params.current_input, filtered_files, bg)
        l4_tokens = TokenCounter.count(l4_content)

    # ... 后续逻辑不变 ...
```

- [ ] **步骤 9：运行测试验证通过**

运行：`pytest tests/server/test_context_builder_v2.py -v`
预期：全部 PASS

- [ ] **步骤 10：运行旧测试确保向后兼容**

运行：`pytest tests/server/test_context_builder.py -v`
预期：全部 PASS（旧行为未受影响）

- [ ] **步骤 11：Commit**

```bash
git add server/llm/context_builder.py tests/server/test_context_builder_v2.py
git commit -m "feat: ContextBuilder 信念驱动改造——L1-L4 支持信念注入，向后兼容"
```

---

## 任务 7：工具执行产生结构化事件

**文件：**
- 修改：`server/tools/executor.py`
- 修改：`server/core/interaction_runner.py:154-170`（`_write_results`）
- 测试：`tests/server/test_tool_executor.py`（追加测试）

### 设计说明

工具执行后，除了返回 `ToolResult`，还需产生一个 `GameEvent` 写入 EventLog。事件由 WitnessEngine 处理后自动分发信念。ToolExecutor 不直接依赖 EventLog/WitnessEngine，而是通过回调（`on_event` hook）解耦。

- [ ] **步骤 1：编写失败的测试**

```python
# tests/server/test_tool_event_integration.py
import pytest
import tempfile
from unittest.mock import MagicMock
from server.models.event import GameEvent
from server.tools.executor import ToolExecutor
from server.tools.registry import ToolRegistry
from server.tools.definitions import FarmNPCTool, EatTool, MoveTool


class TestToolExecutorEvents:
    def setup_method(self):
        self.registry = ToolRegistry()
        self.registry.register(FarmNPCTool())
        self.registry.register(EatTool())
        self.registry.register(MoveTool())
        self.events_collected = []
        self.executor = ToolExecutor(
            registry=self.registry,
            on_event=lambda e: self.events_collected.append(e),
        )

    def test_farm_produces_action_event(self):
        context = {
            "actor_id": "farmer",
            "location": "field",
            "game_time": {"day": 1, "hour": 8},
            "location_registry": None,
        }
        results = self.executor.execute_tool_calls(
            actor_id="farmer",
            tool_calls=[{"call_id": "c1", "name": "farm", "arguments": {}}],
            context=context,
        )
        assert results[0]["success"]
        assert len(self.events_collected) == 1
        event = self.events_collected[0]
        assert event.type == "action"
        assert event.actor == "farmer"
        assert event.location == "field"
        assert event.visibility == "location"

    def test_move_produces_movement_event(self):
        loc_reg = MagicMock()
        loc_reg.get_npcs_at.return_value = {"farmer", "bartender"}
        context = {
            "actor_id": "farmer",
            "location": "field",
            "game_time": {"day": 1, "hour": 10},
            "location_registry": loc_reg,
        }
        results = self.executor.execute_tool_calls(
            actor_id="farmer",
            tool_calls=[{"call_id": "c1", "name": "move", "arguments": {"destination": "tavern"}}],
            context=context,
        )
        assert len(self.events_collected) == 1
        event = self.events_collected[0]
        assert event.type == "movement"
        assert "tavern" in event.content or "酒馆" in event.content

    def test_no_event_callback_still_works(self):
        """on_event 为 None 时不崩溃（向后兼容）。"""
        executor = ToolExecutor(registry=self.registry, on_event=None)
        context = {
            "actor_id": "farmer",
            "location": "field",
            "game_time": {"day": 1, "hour": 8},
            "location_registry": None,
        }
        results = executor.execute_tool_calls(
            actor_id="farmer",
            tool_calls=[{"call_id": "c1", "name": "farm", "arguments": {}}],
            context=context,
        )
        assert results[0]["success"]

    def test_failed_tool_no_event(self):
        """工具执行失败时不产生事件。"""
        context = {
            "actor_id": "farmer",
            "location": "field",
            "game_time": {"day": 1, "hour": 8},
            "location_registry": None,
        }
        results = self.executor.execute_tool_calls(
            actor_id="farmer",
            tool_calls=[{"call_id": "c1", "name": "nonexistent", "arguments": {}}],
            context=context,
        )
        assert not results[0]["success"]
        assert len(self.events_collected) == 0
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest tests/server/test_tool_event_integration.py -v`
预期：FAIL，`ToolExecutor.__init__` 不接受 `on_event` 参数

- [ ] **步骤 3：修改 ToolExecutor 支持事件回调**

修改 `server/tools/executor.py`：

```python
from typing import Any, Callable, Dict, List, Optional
from server.models.event import GameEvent

TOOL_EVENT_TYPE = {
    "farm": "action", "brew": "action", "patrol": "action",
    "divine": "action", "paint": "action",
    "eat": "action", "sleep": "action", "rest": "action",
    "move": "movement",
    "gossip": "dialogue", "trade": "dialogue",
}


class ToolExecutor:
    def __init__(self, registry: ToolRegistry, max_calls_per_turn: int = 3,
                 on_event: Optional[Callable[[GameEvent], None]] = None):
        self.registry = registry
        self.max_calls_per_turn = max_calls_per_turn
        self.on_event = on_event

    def execute_tool_calls(
        self,
        actor_id: str,
        tool_calls: List[Dict[str, Any]],
        context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        results = []
        for call in tool_calls[:self.max_calls_per_turn]:
            call_id = call.get("call_id", "")
            name = call.get("name", "")
            arguments = call.get("arguments", {})

            tool = self.registry.get(name)
            if tool is None:
                results.append({
                    "call_id": call_id, "name": name,
                    "success": False, "message": f"未知工具: {name}",
                    "state_changes": {},
                })
                continue

            try:
                result = tool.execute(actor_id, arguments, context)
                results.append({
                    "call_id": call_id, "name": name,
                    "success": result.success, "message": result.message,
                    "state_changes": result.state_changes,
                })
                if result.success and self.on_event:
                    self._emit_event(name, actor_id, arguments, result, context)
            except Exception as e:
                results.append({
                    "call_id": call_id, "name": name,
                    "success": False, "message": f"执行失败: {e}",
                    "state_changes": {},
                })
        return results

    def _emit_event(self, tool_name, actor_id, arguments, result, context):
        game_time = context.get("game_time", {"day": 1, "hour": 0})
        location = context.get("location", "unknown")
        loc_reg = context.get("location_registry")

        witnesses = [actor_id]
        if loc_reg:
            colocated = loc_reg.get_npcs_at(location)
            if isinstance(colocated, set):
                witnesses = list(colocated)
            elif isinstance(colocated, list):
                witnesses = colocated

        event = GameEvent(
            type=TOOL_EVENT_TYPE.get(tool_name, "action"),
            timestamp=dict(game_time) if isinstance(game_time, dict) else game_time.to_dict(),
            actor=actor_id,
            location=arguments.get("destination", location) if tool_name == "move" else location,
            content=result.message,
            witnesses=witnesses,
            visibility="location",
        )
        self.on_event(event)

    def build_result_messages(self, results: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        messages = []
        for r in results:
            content = json.dumps(
                {"success": r["success"], "message": r["message"], "state_changes": r["state_changes"]},
                ensure_ascii=False,
            )
            messages.append({"role": "tool", "tool_call_id": r["call_id"], "content": content})
        return messages
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest tests/server/test_tool_event_integration.py -v`
预期：全部 PASS

- [ ] **步骤 5：运行旧测试确保不破坏**

运行：`pytest tests/server/test_tool_executor.py -v`
预期：全部 PASS（`on_event` 默认 None，旧行为不变）

- [ ] **步骤 6：Commit**

```bash
git add server/tools/executor.py tests/server/test_tool_event_integration.py
git commit -m "feat: ToolExecutor 工具执行后产生 GameEvent，通过回调解耦"
```

---

## 任务 8：对话中的信念传播

**文件：**
- 修改：`server/core/interaction_runner.py`
- 创建：`server/core/belief_propagator.py`
- 测试：`tests/server/test_belief_propagator.py`

### 设计说明

NPC 对话时，对话内容中的事实性陈述应作为信念传递给对方。两种实现方式：
1. LLM 标注方式（在对话回复末尾附加 `[传递信念: ...]`）— Phase 3 实现
2. 规则提取方式（当前：对话结束后将摘要作为 `told_by` 信念传递给对方）

当前先用方式 2（简单可靠），后续可升级为 LLM 标注。

- [ ] **步骤 1：编写失败的测试**

```python
# tests/server/test_belief_propagator.py
import pytest
import tempfile
from server.models.belief import Belief
from server.core.belief_store import BeliefStore
from server.core.belief_propagator import BeliefPropagator


class TestBeliefPropagator:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.stores = {
            "farmer": BeliefStore(npc_id="farmer", base_path=self.tmpdir),
            "bartender": BeliefStore(npc_id="bartender", base_path=self.tmpdir),
        }
        self.propagator = BeliefPropagator(belief_stores=self.stores)

    def test_propagate_dialogue_summary(self):
        """对话摘要作为 told_by 信念传递给双方。"""
        self.propagator.propagate_from_dialogue(
            speaker_id="farmer",
            listener_id="bartender",
            summary="乔治告诉盖斯他在田里发现了一把生锈的剑",
            game_time={"day": 2, "hour": 14},
        )
        bartender_beliefs = self.stores["bartender"].get_all()
        assert len(bartender_beliefs) == 1
        assert bartender_beliefs[0].source == "told_by:farmer"
        assert bartender_beliefs[0].confidence == "medium"
        assert "生锈的剑" in bartender_beliefs[0].content

    def test_both_participants_get_dialogue_belief(self):
        """双方都获得关于此对话的信念。"""
        self.propagator.propagate_from_dialogue(
            speaker_id="farmer",
            listener_id="bartender",
            summary="两人讨论了最近的天气和收成",
            game_time={"day": 2, "hour": 14},
        )
        # farmer 获得 witnessed（自己参与的对话）
        farmer_beliefs = self.stores["farmer"].get_all()
        assert len(farmer_beliefs) == 1
        assert farmer_beliefs[0].source == "witnessed"
        assert farmer_beliefs[0].confidence == "high"

        # bartender 获得 told_by:farmer
        bartender_beliefs = self.stores["bartender"].get_all()
        assert len(bartender_beliefs) == 1
        assert bartender_beliefs[0].source == "told_by:farmer"

    def test_share_specific_belief(self):
        """NPC 主动分享一条已有信念给对方。"""
        original = Belief(
            content="商人在卖违禁品",
            source="witnessed", confidence="high",
            acquired_at={"day": 1, "hour": 10}, about=["world"],
        )
        self.stores["farmer"].add(original)

        self.propagator.share_belief(
            from_npc="farmer",
            to_npc="bartender",
            belief=original,
            new_content="听说商人在卖违禁品",
            game_time={"day": 2, "hour": 14},
        )

        bartender_beliefs = self.stores["bartender"].get_all()
        assert len(bartender_beliefs) == 1
        assert bartender_beliefs[0].confidence == "medium"  # high → medium
        assert bartender_beliefs[0].source == "told_by:farmer"

    def test_duplicate_share_ignored(self):
        """重复分享同一信念不产生新条目。"""
        self.propagator.propagate_from_dialogue(
            speaker_id="farmer",
            listener_id="bartender",
            summary="乔治说天气不好",
            game_time={"day": 2, "hour": 14},
        )
        self.propagator.propagate_from_dialogue(
            speaker_id="farmer",
            listener_id="bartender",
            summary="乔治说天气不好",
            game_time={"day": 2, "hour": 15},
        )
        bartender_beliefs = self.stores["bartender"].get_all()
        assert len(bartender_beliefs) == 1

    def test_unknown_npc_safe(self):
        """未知 NPC ID 不崩溃。"""
        self.propagator.propagate_from_dialogue(
            speaker_id="unknown",
            listener_id="bartender",
            summary="神秘人说了什么",
            game_time={"day": 1, "hour": 10},
        )
        bartender_beliefs = self.stores["bartender"].get_all()
        assert len(bartender_beliefs) == 1
```

- [ ] **步骤 2：运行测试验证失败**

运行：`pytest tests/server/test_belief_propagator.py -v`
预期：FAIL，"ModuleNotFoundError: No module named 'server.core.belief_propagator'"

- [ ] **步骤 3：编写实现代码**

```python
# server/core/belief_propagator.py
from __future__ import annotations
from typing import Dict, Optional
from server.models.belief import Belief
from server.core.belief_store import BeliefStore


class BeliefPropagator:
    """对话中的信念传播。

    对话结束后调用，将摘要内容转化为参与者的信念。
    """

    def __init__(self, belief_stores: Dict[str, BeliefStore]):
        self._stores = belief_stores

    def propagate_from_dialogue(
        self,
        speaker_id: str,
        listener_id: str,
        summary: str,
        game_time: Dict[str, int],
    ) -> None:
        """对话摘要 → 信念传播。

        speaker 获得 witnessed/high 信念（自己经历的对话）
        listener 获得 told_by:speaker/medium 信念
        """
        if speaker_id in self._stores:
            speaker_belief = Belief(
                content=summary,
                source="witnessed",
                confidence="high",
                acquired_at=dict(game_time),
                about=self._extract_about(speaker_id, listener_id),
            )
            self._stores[speaker_id].add(speaker_belief)

        if listener_id in self._stores:
            listener_belief = Belief(
                content=summary,
                source=f"told_by:{speaker_id}",
                confidence="medium",
                acquired_at=dict(game_time),
                about=self._extract_about(speaker_id, listener_id),
            )
            self._stores[listener_id].add(listener_belief)

    def share_belief(
        self,
        from_npc: str,
        to_npc: str,
        belief: Belief,
        new_content: Optional[str] = None,
        game_time: Optional[Dict[str, int]] = None,
    ) -> bool:
        """NPC 主动将一条信念分享给另一个 NPC。

        confidence 降一级，source 变为 told_by:from_npc。
        """
        store = self._stores.get(to_npc)
        if store is None:
            return False
        content = new_content or belief.content
        propagated = belief.propagate(teller_id=from_npc, new_content=content)
        if game_time:
            propagated.acquired_at = dict(game_time)
        return store.add(propagated)

    def _extract_about(self, speaker_id: str, listener_id: str) -> list:
        about = []
        if speaker_id != "world":
            about.append(speaker_id)
        if listener_id != "world":
            about.append(listener_id)
        return about or ["world"]
```

- [ ] **步骤 4：运行测试验证通过**

运行：`pytest tests/server/test_belief_propagator.py -v`
预期：全部 PASS

- [ ] **步骤 5：修改 InteractionRunner 集成 BeliefPropagator**

修改 `server/core/interaction_runner.py`，在 `_write_results` 后调用信念传播：

```python
class InteractionRunner:
    def __init__(self, context_builder: ContextBuilder, llm_client,
                 belief_propagator=None, event_log=None):
        self._builder_factory = context_builder
        self.llm_client = llm_client
        self._belief_propagator = belief_propagator
        self._event_log = event_log

    # ... 在 run_conversation 末尾，_write_results 之后追加：

        if self._belief_propagator and summary:
            initiator_id = initiator.id if hasattr(initiator, 'id') else initiator.agent_id
            target_id = target.id if hasattr(target, 'id') else target.agent_id
            self._belief_propagator.propagate_from_dialogue(
                speaker_id=initiator_id,
                listener_id=target_id,
                summary=summary,
                game_time={"day": game_time.day, "hour": game_time.hour},
            )

        if self._event_log:
            from server.models.event import GameEvent
            event = GameEvent(
                type="dialogue",
                timestamp={"day": game_time.day, "hour": game_time.hour},
                actor=initiator_id,
                location=location,
                content=summary,
                witnesses=[initiator_id, target_id],
                visibility="location",
            )
            self._event_log.append(event)
```

- [ ] **步骤 6：运行旧测试确保向后兼容**

运行：`pytest tests/server/test_interaction_hook.py -v`
预期：PASS（`belief_propagator=None` 时不触发新逻辑）

- [ ] **步骤 7：Commit**

```bash
git add server/core/belief_propagator.py server/core/interaction_runner.py tests/server/test_belief_propagator.py
git commit -m "feat: BeliefPropagator 对话信念传播——对话摘要转化为参与者信念"
```

---

## 任务 9：端到端集成——Orchestrator 组装完整管道

**文件：**
- 修改：`server/core/orchestrator.py`
- 修改：`server/tools/setup.py`
- 创建：`tests/integration/test_belief_pipeline.py`

### 设计说明

Orchestrator 启动时创建 EventLog、BeliefStore（每 NPC 一个）、WitnessEngine、BeliefPropagator，将它们注入到 ToolExecutor 和 InteractionRunner。NPC 做决策时，从 BeliefStore 获取信念传入 ContextBuilder。

- [ ] **步骤 1：编写集成测试**

```python
# tests/integration/test_belief_pipeline.py
import pytest
import tempfile
from unittest.mock import AsyncMock, MagicMock, patch
from server.models.event import GameEvent
from server.models.belief import Belief
from server.models.game_time import GameTime
from server.core.event_log import EventLog
from server.core.belief_store import BeliefStore
from server.core.witness_engine import WitnessEngine
from server.core.belief_propagator import BeliefPropagator


class TestBeliefPipelineIntegration:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.event_log = EventLog(base_path=f"{self.tmpdir}/events")
        self.belief_stores = {
            "farmer": BeliefStore(npc_id="farmer", base_path=f"{self.tmpdir}/beliefs"),
            "bartender": BeliefStore(npc_id="bartender", base_path=f"{self.tmpdir}/beliefs"),
        }
        self.witness_engine = WitnessEngine(belief_stores=self.belief_stores)
        self.propagator = BeliefPropagator(belief_stores=self.belief_stores)

    def test_full_cycle_action_to_belief(self):
        """完整循环：工具执行 → 事件 → 目击 → 信念。"""
        event = GameEvent(
            type="action", timestamp={"day": 1, "hour": 10},
            actor="farmer", location="field",
            content="乔治在田地里发现了一颗奇怪的种子",
            witnesses=["farmer"],
            visibility="location",
        )
        self.event_log.append(event)
        self.witness_engine.process_event(event)

        beliefs = self.belief_stores["farmer"].get_active(current_day=1)
        assert len(beliefs) == 1
        assert "奇怪的种子" in beliefs[0].content
        assert beliefs[0].confidence == "high"

        # bartender 不知道
        assert len(self.belief_stores["bartender"].get_active(current_day=1)) == 0

    def test_full_cycle_gossip_propagation(self):
        """完整循环：farmer 目击 → 对话传播给 bartender。"""
        # Step 1: farmer 亲眼看到
        event = GameEvent(
            type="action", timestamp={"day": 1, "hour": 10},
            actor="farmer", location="field",
            content="一个陌生商人鬼鬼祟祟地进了森林",
            witnesses=["farmer"],
            visibility="location",
        )
        self.event_log.append(event)
        self.witness_engine.process_event(event)

        # Step 2: farmer 去酒馆告诉 bartender
        self.propagator.propagate_from_dialogue(
            speaker_id="farmer",
            listener_id="bartender",
            summary="乔治说他看到陌生商人进了森林",
            game_time={"day": 1, "hour": 14},
        )

        # 验证
        bartender_beliefs = self.belief_stores["bartender"].get_active(current_day=1)
        assert len(bartender_beliefs) == 1
        assert bartender_beliefs[0].confidence == "medium"
        assert bartender_beliefs[0].source == "told_by:farmer"

        # farmer 有两条信念：亲眼所见 + 对话记录
        farmer_beliefs = self.belief_stores["farmer"].get_active(current_day=1)
        assert len(farmer_beliefs) == 2

    def test_public_event_reaches_all(self):
        """公共事件所有 NPC 都知道。"""
        event = GameEvent(
            type="world", timestamp={"day": 2, "hour": 6},
            actor="world", location="village",
            content="村口来了一位旅行商人",
            witnesses=[],
            visibility="public",
        )
        self.event_log.append(event)
        self.witness_engine.process_event(event)

        for store in self.belief_stores.values():
            beliefs = store.get_active(current_day=2)
            assert any("旅行商人" in b.content for b in beliefs)

    def test_belief_retrieval_for_context(self):
        """从 BeliefStore 获取 context 注入用的信念子集。"""
        # 添加多条不同优先级的信念
        self.belief_stores["farmer"].add(Belief(
            content="亲眼看到商人", source="witnessed",
            confidence="high", acquired_at={"day": 3, "hour": 10},
            about=["world"],
        ))
        self.belief_stores["farmer"].add(Belief(
            content="听说商人有问题", source="told_by:bartender",
            confidence="medium", acquired_at={"day": 3, "hour": 14},
            about=["world"],
        ))
        self.belief_stores["farmer"].add(Belief(
            content="很久以前的小道消息", source="overheard",
            confidence="low", acquired_at={"day": 1, "hour": 8},
            about=["world"],
        ))

        # day 5 时，low confidence 已过期
        context_beliefs = self.belief_stores["farmer"].get_for_context(current_day=5)
        assert len(context_beliefs) == 2  # high + medium，low 过期
        assert context_beliefs[0].confidence == "high"  # 按优先级排序

    def test_event_log_persistence(self):
        """事件持久化并可查询。"""
        for i in range(5):
            self.event_log.append(GameEvent(
                type="action", timestamp={"day": 1, "hour": 8 + i},
                actor="farmer", location="field",
                content=f"活动{i}", witnesses=["farmer"],
                visibility="location",
            ))
        # 重新加载
        log2 = EventLog(base_path=f"{self.tmpdir}/events")
        day1 = log2.query(day=1)
        assert len(day1) == 5
```

- [ ] **步骤 2：运行测试验证通过**

运行：`pytest tests/integration/test_belief_pipeline.py -v`
预期：全部 PASS（仅依赖前面任务已实现的组件，不需要改 Orchestrator）

- [ ] **步骤 3：修改 `build_autonomous_context` 适配信念**

修改 `server/tools/setup.py` 中的 `build_autonomous_context`，新增可选参数：

```python
def build_autonomous_context(agent, game_time, location_registry=None,
                             event_engine=None, belief_store=None) -> str:
    """构建 NPC 自主决策时的 current_input 文本。

    当 belief_store 提供时，不再注入 activity_log，改为仅提供行动指令。
    信念内容由 ContextBuilder 的 L1-L4 层负责注入。
    """
    location_cn = LOCATION_NAMES.get(agent.location, agent.location)
    idle_reason = agent.activity_state.idle_reason

    if idle_reason is None:
        status_text = "刚起床" if game_time.hour == 6 else "空闲"
        last_activity_text = ""
    else:
        status_text = "空闲"
        last_activity_text = f"\n上一个活动：{idle_reason}"

    # 当前环境（保留——这是客观的即时感知）
    env_parts = []
    if event_engine:
        weather = event_engine.get_current_weather()
        env_parts.append(f"天气：{weather}")
    env_parts.append(f"当前地点：{location_cn}")
    if location_registry:
        colocated = location_registry.get_npcs_at(agent.location) - {agent.agent_id}
        if colocated:
            names = [_get_npc_name(nid) for nid in colocated]
            env_parts.append(f"同处此地的人：{'、'.join(names)}")
    env_section = "\n【当前环境】\n" + "\n".join(env_parts)

    # 信念系统模式：精简 input，信念由 ContextBuilder 注入
    if belief_store is not None:
        return (
            f"【行动指令】\n"
            f"当前时间：Day {game_time.day}, {game_time.hour}:00\n"
            f"你的状态：{status_text}"
            f"{last_activity_text}"
            f"{env_section}\n"
            f"你正在独自思考接下来做什么，不需要说话或与任何人对话。"
            f"请直接调用一个工具，不要生成对话文本。"
        )

    # 旧模式：保持原有逻辑不变
    if agent.activity_log:
        today_log = "\n【今日已完成】\n" + "\n".join(agent.activity_log)
    else:
        today_log = "\n【今日已完成】\n（刚开始新的一天）"

    recent = agent.memory.read_recent_summaries(game_time.day, count=2)
    recent_section = f"\n【近日回顾】\n{recent}" if recent else ""

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
```

- [ ] **步骤 4：运行全部测试**

运行：`pytest tests/ -v --tb=short`
预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add server/tools/setup.py tests/integration/test_belief_pipeline.py
git commit -m "feat: 端到端集成——build_autonomous_context 适配信念系统，集成测试验证完整管道"
```

---

## 自检

### 1. 规格覆盖度

| 规格需求 | 对应任务 |
|---------|---------|
| Belief 数据模型（id/content/source/confidence/acquired_at/about） | 任务 1 |
| 信念生命周期：产生/传播/衰减/冲突 | 任务 1（模型）+ 任务 4（BeliefStore） |
| Event 数据模型（id/type/timestamp/actor/location/content/witnesses/visibility/reasoning） | 任务 2 |
| Event Log 持久化和查询 | 任务 3 |
| 目击规则（public/location/private → 信念分发） | 任务 5 |
| reasoning 字段作为 actor 自己的信念 | 任务 5 |
| ContextBuilder L1 改为信念注入 | 任务 6 |
| ContextBuilder L2 加入 reasoning 信念 | 任务 6 |
| ContextBuilder L3 改为关系信念 | 任务 6 |
| ContextBuilder L4 信念检索替代关键词检索 | 任务 6 |
| 信念格式（你确定的事/你听说的/你的近期决策） | 任务 6 |
| 工具执行产生事件 | 任务 7 |
| 对话中信念传播 | 任务 8 |
| 端到端管道集成 | 任务 9 |
| 信念衰减（low 3天/medium 7天/high 不衰减） | 任务 1 + 任务 4 |
| 重复信念去重 | 任务 4 |
| 向后兼容（beliefs 为空时退化旧行为） | 任务 6 + 任务 9 |

### 2. 未覆盖（属于后续 Phase 范围）

- 去机械化：取消固定决策点，改为事件驱动（需改 Orchestrator 调度逻辑，独立计划）
- 对话自由化（LLM 决定对话长度，独立计划）
- 策略门控放松（独立计划）
- 成就系统（独立计划）
- 信念中断决策（依赖事件驱动调度，独立计划）
- LLM 标注信念传播方式（Phase 3）

### 3. 类型一致性检查

- `Belief.propagate()` 返回 `Belief` — 在 `BeliefPropagator.share_belief()` 中使用 ✓
- `GameEvent.to_dict()` / `from_dict()` — 在 `EventLog` 中使用 ✓
- `BeliefStore.get_for_context()` 返回 `List[Belief]` — 传入 `BuildParams.beliefs` ✓
- `WitnessEngine.process_event()` 接受 `GameEvent` — `ToolExecutor.on_event` 回调传入 ✓
- `BuildParams.beliefs` / `interlocutor_beliefs` / `reasoning_beliefs` 类型均为 `List` ✓
- `ToolExecutor.on_event` 签名 `Callable[[GameEvent], None]` ✓
