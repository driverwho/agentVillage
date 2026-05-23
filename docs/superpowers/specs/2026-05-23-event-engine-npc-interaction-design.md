# 事件引擎 + NPC 交互系统 设计规格

> 日期：2026-05-23
> 状态：设计完成，待实现

## 1. 目标

解决当前 NPC 行为趋于固定循环的核心问题：

- **缺乏外部刺激**：world_state 硬编码为"晴/今日无事"，NPC 没有可反应的事件
- **NPC 之间完全隔离**：gossip/trade 执行结果不送达目标，无面对面交互

本设计引入两个独立模块：

1. **EventEngine** — 规则驱动的事件生成，为 NPC 决策提供变化的外部环境
2. **InteractionHook** — NPC 到达地点后自主触发的交互系统，实现 NPC 间多轮对话

## 2. 设计决策记录

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 事件生成方式 | 纯规则驱动（概率表 + 时间条件） | 可控、确定性高、不消耗 LLM token |
| 事件影响方式 | 仅注入 prompt，LLM 自决 | 保持最大自由度，不强制行为 |
| 交互触发方式 | NPC 到达地点后自主触发（hook） | 社交行为由 NPC 驱动，非外部调度 |
| 对话深度 | 2 轮来回（4 次 LLM 调用），固定上限 | 叙事丰富且成本可控 |
| 事件池规模 | 最小可用集：4 类约 15 个事件 | 快速验证效果 |
| 架构模式 | 事件引擎 + 交互 Hook 独立模块 | 改动范围小，模块边界清晰 |
| Hook 组织方式 | 独立 `server/hooks/` 目录，含基类和 registry | 预留后续 hook 系统扩展 |
| 地点管理 | 全局 LocationRegistry（location → NPC 集合） | 统一管理，避免状态散落 |

## 3. EventEngine 事件引擎

### 3.1 职责

每 tick 根据规则生成当日/当时段生效的事件，写入 world_state 供 NPC 决策 prompt 消费。

### 3.2 事件定义格式

事件定义存放在 `server/data/events/` 目录，按类别分文件（YAML）：

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

### 3.3 事件类别（第一版）

| 类别 | 文件 | 事件数 | 示例 |
|------|------|--------|------|
| weather | `weather.yaml` | 4 | 暴雨、浓雾、酷暑、大风 |
| visitor | `visitor.yaml` | 3 | 旅行商人、流浪诗人、神秘信使 |
| discovery | `discovery.yaml` | 4 | 田里挖出旧物、井水变色、异常植物、远处浓烟 |
| npc_trigger | `npc_trigger.yaml` | 4 | 乔治收到儿子来信、Gus 发现可疑脚印、流浪狗受伤、酒馆漏雨 |

### 3.4 核心接口

```python
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
    cooldowns: Dict[str, int] = field(default_factory=dict)  # event_id → expires_on_day

class EventEngine:
    def __init__(self, event_defs: List[EventDef], state: EventState):
        self.event_defs = event_defs
        self.state = state

    def tick(self, game_time: GameTime) -> List[ActiveEvent]:
        """每 tick 调用，返回当前生效的事件列表。
        1. 检查已生效事件是否过期，移除
        2. 对每个候选事件：检查 conditions → roll 概率 → 命中则加入 active
        3. 返回 active 事件列表
        """
        ...

    def get_current_weather(self) -> str:
        """返回当前天气描述，无天气事件时返回'晴'"""
        ...

    def get_world_events_text(self) -> str:
        """生成注入 world_state['events'] 的文本。
        无事件返回'今日无事'；有事件返回分号分隔的描述。
        """
        ...
```

### 3.5 Conditions 规则

| 条件字段 | 类型 | 含义 |
|----------|------|------|
| `min_day` | int | 最早可触发的游戏日 |
| `cooldown_days` | int | 触发后的冷却天数 |
| `hour_range` | [int, int] | 仅在该小时区间内可触发 |
| `required_event` | str | 前置事件 ID（该事件正在生效时才可触发） |
| `max_active_events` | int | 全局最大同时生效事件数（默认 3） |

## 4. LocationRegistry 全局地点管理

### 4.1 职责

维护 location → set[npc_id] 的全局映射，作为唯一的地点真相源。

### 4.2 接口

```python
class LocationRegistry:
    def __init__(self, initial: Dict[str, List[str]] = None):
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

### 4.3 持久化

LocationRegistry 的状态保存到 `world_state.json` 的 `locations` 字段，随 orchestrator 的 auto_save 一起写入。

## 5. Hook 系统

### 5.1 目录结构

```
server/hooks/
├── __init__.py           # HookRegistry
├── base.py               # Hook 基类
└── interaction_hook.py   # NPC 到达地点后的交互检测
```

### 5.2 Hook 基类

```python
# server/hooks/base.py
from typing import Any, Dict

class Hook:
    event: str  # 监听的事件名：post_move, post_sleep, post_trade 等

    async def execute(self, context: Dict[str, Any]) -> None:
        raise NotImplementedError
```

### 5.3 HookRegistry

```python
# server/hooks/__init__.py
from collections import defaultdict
from typing import Dict, List
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

### 5.4 Hook 事件列表（第一版）

| 事件名 | 触发时机 | context 内容 |
|--------|----------|-------------|
| `post_move` | NPC move 工具执行成功后 | `actor_id`, `location`, `game_time` |
| `post_sleep` | NPC sleep 工具执行后（预留） | `actor_id`, `game_time` |

## 6. InteractionHook NPC 交互

### 6.1 触发流程

```
NPC-A 调用 move(tavern)
  → MoveTool.execute() 成功
  → hook_registry.fire("post_move", {actor_id, location, game_time})
    → InteractionHook.execute()
      → location_registry.get_npcs_at(location) - {actor_id}
      → 对每个共处 NPC-B: should_interact(A, B)?
      → 通过: interaction_runner.run_conversation(A, B)
      → 结果写入双方 activity_log
```

### 6.2 关系门控

```python
def should_interact(initiator: NPC, target: NPC, game_time: GameTime,
                    interaction_counter: "InteractionCounter") -> bool:
    rel = initiator.background.relationships.get(target.id)
    if not rel:
        return False
    if rel.trust_level < 4:
        return False
    pair_key = tuple(sorted([initiator.id, target.id]))
    today_count = interaction_counter.get_today_count(pair_key, game_time.day)
    if today_count >= 2:
        return False
    if target.activity_state.status != "idle":
        return False
    return True
```

门控条件：
- 必须存在关系定义
- 信任度 >= 4
- 同一对 NPC 每天最多交互 2 次
- 目标 NPC 必须处于 idle 状态

**InteractionCounter** 作为 InteractionHook 的成员，内存中维护 `{(pair_key, day): count}` 字典。每次对话完成后 +1。无需持久化——每次服务启动时从 0 开始，同一天内重启的边界情况可以忽略。

### 6.3 多轮对话执行

```python
class InteractionRunner:
    def __init__(self, context_builder: ContextBuilder, llm_client):
        self.context_builder = context_builder
        self.llm_client = llm_client

    async def run_conversation(self, initiator: NPC, target: NPC,
                                location: str, game_time: GameTime) -> ConversationResult:
        dialogue = []
        speakers = [initiator, target, initiator, target]  # 2轮来回

        for i, speaker in enumerate(speakers):
            listener = target if speaker == initiator else initiator
            params = BuildParams(
                scenario=ScenarioType.NPC_INTERACTION,
                identity=speaker.identity,
                npc_state=speaker.state,
                world_state=current_world_state,
                interlocutor={"name": listener.name, "relationship": ...},
                memory_files=speaker.memory_files,
                dialogue_history=dialogue,
                current_input=self._build_interaction_prompt(speaker, listener, dialogue, i),
                background=speaker.background,
            )
            messages = self.context_builder.build(params).messages
            response = await self.llm_client.chat(messages)
            dialogue.append({"speaker": speaker.id, "content": response})

        summary = self._generate_summary(dialogue)
        return ConversationResult(
            participants=(initiator.id, target.id),
            location=location,
            dialogue=dialogue,
            summary=summary,
            game_time=game_time,
        )
```

对话流程：固定 4 次 LLM 调用（发起方说 → 接收方回 → 发起方再说 → 接收方结束）。

### 6.4 对话结果数据结构

```python
@dataclass
class ConversationResult:
    participants: Tuple[str, str]
    location: str
    dialogue: List[Dict[str, str]]  # [{"speaker": "farmer", "content": "..."}, ...]
    summary: str                     # 一句话总结
    game_time: GameTime
```

### 6.5 对话摘要生成

`ConversationResult.summary` 由最后一轮 LLM 调用时在 prompt 中附加指令生成：在第 4 次调用（接收方最后回应）时，system prompt 额外要求"用一句话总结本次对话的要点"。不额外增加 LLM 调用次数。

### 6.6 状态锁定时序

1. 对话开始前：立即将双方标记为 `active`（current_tool = "socializing"，duration = 1h）
2. 执行 4 次 LLM 调用（实时顺序执行，总耗时取决于 LLM 响应速度）
3. 对话完成后：结果写入双方 activity_log

先锁定再执行，确保对话期间不会有其他 hook 或 tick 打断双方。1h 的 game duration 意味着对话结束后双方在下一个游戏小时才会重新进入决策。

### 6.7 结果写入

对话完成后：
1. 写入双方的 `activity_log`（当日可见）
2. 作为"近期社交"注入后续决策 prompt
3. interaction_counter 对应 pair +1

## 7. Prompt 注入变化

`build_autonomous_context` 增加以下字段：

```
【当前环境】
天气：暴雨
今日事件：一个旅行商人在市场摆摊
当前地点：酒馆
同处此地的人：酒馆老板 Gus

【近期社交】
Day 3 12:00 — 在酒馆与 Gus 聊了几句，他提到最近夜里听到奇怪的脚步声。
```

## 8. 前端观察面板：全局事件展示

### 8.1 位置

在 ObservePage 的 header 和 NPC 卡片 grid 之间，新增一个"全局事件"区域。

### 8.2 布局

```
ObservePage
├── <header> (已有)
├── .event-banner  ← 新增
│   ├── 标题："当前事件"
│   └── 事件列表（横向排列，标签样式）
│       ├── 🌧 暴雨（6:00 起）
│       └── 🧳 旅行商人在市场摆摊
│       （无事件时显示"今日无事"）
└── .observe-grid (已有)
```

### 8.3 数据流

**后端推送**：EventEngine 在事件变更时（新增或过期），通过 observe WebSocket 广播：

```json
{
  "type": "world_events_update",
  "events": [
    {"id": "heavy_rain", "name": "暴雨", "description": "乌云密布，暴雨倾盆", "started_hour": 6},
    {"id": "merchant_visit", "name": "旅行商人", "description": "一个旅行商人在市场摆摊", "started_hour": 8}
  ]
}
```

**前端处理**：

- `observeStore` 新增 `worldEvents: []` 状态
- `handleMessage` 新增 `world_events_update` 类型处理
- 初始加载时 `GET /api/npcs/status` 的响应中也包含当前 active events

### 8.4 组件

不需要独立组件，直接在 `ObservePage.vue` 中作为一行 banner 渲染。事件用标签（tag/chip）样式展示，每个事件一个标签，带有类别对应的图标。

## 9. 持久化结构

world_state.json 扩展为：

```json
{
  "game_time": {"day": 3, "hour": 14},
  "is_paused": false,
  "locations": {
    "tavern": ["bartender"],
    "field": ["farmer"],
    "home": []
  },
  "event_state": {
    "active_events": [
      {"id": "heavy_rain", "started_day": 3, "started_hour": 6, "expires_day": 3, "expires_hour": 14}
    ],
    "cooldowns": {"heavy_rain": 5}
  }
}
```

## 9. 文件清单

### 新增文件

| 文件 | 职责 |
|------|------|
| `server/hooks/__init__.py` | HookRegistry |
| `server/hooks/base.py` | Hook 基类 |
| `server/hooks/interaction_hook.py` | 到达地点交互检测 + should_interact |
| `server/core/event_engine.py` | EventEngine + EventState + EventDef |
| `server/core/location_registry.py` | LocationRegistry |
| `server/core/interaction_runner.py` | 多轮对话执行器 + ConversationResult |
| `server/data/events/weather.yaml` | 天气事件定义（4 个） |
| `server/data/events/visitor.yaml` | 访客事件定义（3 个） |
| `server/data/events/discovery.yaml` | 发现事件定义（4 个） |
| `server/data/events/npc_trigger.yaml` | NPC 触发事件定义（4 个） |

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `server/core/orchestrator.py` | 初始化 event_engine / location_registry / hook_registry；tick 中调用 event_engine.tick()；move 后 fire("post_move")；auto_save 扩展；事件变更时广播 world_events_update |
| `server/tools/setup.py` | `build_autonomous_context` 增加【当前环境】和【近期社交】字段 |
| `server/llm/context_builder.py` | 实现 `NPC_INTERACTION` 场景的 build 逻辑 |
| `data/users/default/world_state.json` | 结构扩展（locations、event_state 字段） |
| `client/src/stores/observeStore.ts` | 新增 `worldEvents` 状态，处理 `world_events_update` 消息 |
| `client/src/pages/ObservePage.vue` | header 下方新增事件 banner 区域 |
| `server/api/` (status endpoint) | 响应中包含当前 active events |

## 10. 不在本次范围内

- 事件对工具可用性的硬约束（选择了"仅注入 prompt"模式）
- 记忆回流（daily_summary 搜索）— 已有独立设计文档
- 经济系统 / 库存系统
- 玩家与事件的交互
- 事件链（事件触发事件）
