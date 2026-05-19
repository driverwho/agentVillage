# Agent Village - 多Agent网页游戏需求文档

## 1. 项目概述

一款基于LLM的多Agent网页游戏。玩家置身于一个虚拟村庄，通过与AI驱动的NPC对话交互，推动剧情发展，最终达成不同结局。

## 2. 核心架构

### 2.1 系统角色

| 角色 | 职责 |
|------|------|
| 主控Agent (Orchestrator) | 管理游戏世界状态、时间流动、事件调度、结局判定 |
| NPC Agent × 6 | 农夫、酒保、警长、画家、占卜师、乞丐 |
| 玩家 (Player) | 人类玩家，通过对话与NPC交互 |

### 2.2 技术架构概要

```
┌─────────────��───────────────────────────────┐
│                 前端 (Web UI)                 │
│         对话界面 / 状态面板 / 时间显示         │
└──────────────────────┬──────────────────────┘
                       │
┌──────────────────────▼──────────────────────┐
│              后端 API 层                      │
│     WebSocket (实时) + REST (状态查询)        │
└──────────────────────┬──────────────────────┘
                       │
┌──────────────────────▼──────────────────────┐
│            主控 Agent (Orchestrator)          │
│  时间管理 │ 事件调度 │ 状态仲裁 │ 结局判定    │
└───┬───────────┬───────────┬─────────────────┘
    │           │           │
┌───▼───┐ ┌────▼────┐ ┌───▼───┐
│NPC Agent│ │NPC Agent│ │NPC Agent│  ...
│ (农夫)  │ │ (酒保)  │ │ (警长)  │
└─────────┘ └─────────┘ └─────────┘
```

## 3. 时间系统 (Workflow)

### 3.1 时间流动

- 游戏内时间独立于现实时间，流速可调节
- 默认流速：现实1秒 = 游戏1分钟（可配置）
- 流速档位：暂停 / 0.5x / 1x / 2x / 4x
- 游戏以"天"为大周期，每天24小时

### 3.2 整点事件调度

每个游戏整点，主控Agent触发：
1. 通知所有NPC Agent当前时间
2. NPC Agent根据时间+自身状态决定是否进行状态变换
3. 状态变换包括：位置移动、活动切换、主动发起NPC间交互
4. 更新世界状态广播

### 3.3 时间对NPC行为的影响

| 时间段 | NPC行为倾向 |
|--------|------------|
| 06:00-08:00 | 起床、准备工作 |
| 08:00-12:00 | 工作/日常活动 |
| 12:00-13:00 | 午餐休息 |
| 13:00-18:00 | 工作/日常活动 |
| 18:00-22:00 | 社交/休闲 （酒馆所有agent集合，目前唯一的agent之间进行交互的点位）|
| 22:00-06:00 | 睡眠（不可交互） |

## 4. NPC Agent 设计

### 4.1 NPC 角色定义

| 角色 | 性格特征 | 核心功能 | 可见玩家状态 |
|------|---------|---------|-------------|
| 农夫 | 朴实、勤劳、善良 | 提供食物、种子、农事信息 | 基础状态 |
| 酒保 | 健谈、消息灵通、圆滑 | 提供情报、社交枢纽 | 基础状态 + 社交关系 |
| 警长 | 严肃、正义、威严 | 维护秩序、任务发布 | 基础状态 + 不良记录 + 犯罪历史 |
| 画家 | 敏感、浪漫、洞察力强 | 情感交流、灵感触发 | 基础状态 + 心灵状态 + 情绪 |
| 占卜师 | 神秘、模糊、暗示性强 | 提供线索、预言、获知梦境 | 基础状态 + 命运值 + 隐藏属性 |
| 乞丐 | 卑微、狡黠、信息贩子 | 地下情报、隐藏任务 | 基础状态 + 财富等级 |

### 4.2 NPC 状态系统

每个NPC拥有以下状态值（0-100）：

```
NPCState {
  health: number      // 健康状态 (0=濒死, 100=完全健康)
  hunger: number      // 饱食度 (0=饥饿, 100=饱足)
  fatigue: number     // 疲惫值 (0=精力充沛, 100=极度疲惫)
  mood: number        // 心情 (0=极差, 100=极好)
}
```

### 4.3 状态→上下文映射

NPC调用LLM时，状态值映射为自然语言描述注入prompt：

| 值范围 | 健康描述 | 饱食描述 | 疲惫描述 |
|--------|---------|---------|---------|
| 0-20   | 你感觉身体极度虚弱 | 你饿得头晕眼花 | 你疲惫到几乎无法站立 |
| 21-40  | 你身体有些不适 | 你的肚子在咕咕叫 | 你感到很疲倦 |
| 41-60  | 你身体状况一般 | 你不太饿也不太饱 | 你有些累了 |
| 61-80  | 你感觉身体不错 | 你吃得还算饱 | 你精神还不错 |
| 81-100 | 你感觉精力充沛，非常健康 | 你吃得很饱很满足 | 你精神抖擞 |

### 4.4 NPC 行为与工具调用

所有 NPC 行为统一为工具调用，由 LLM function calling 全权决策。

**工具分类：**

| 类别 | 工具 | 特性 |
|------|------|------|
| 社交 | speak, speak_reply, end_speak, accept, reject, gossip | speak 建立对话会话，其他一次性 |
| 职业 | farm, brew, patrol, divine, paint, trade | 一次性调用 |
| 生存 | eat, sleep, rest, move | 一次性调用 |

**工具策略管道（五层过滤）：**

1. **身份门** — 农夫不能 brew()，酒保不能 farm()
2. **状态门** — fatigue > 80 时不能做复杂社交
3. **关系门** — trust < 30 时对话语气受限
4. **时间门** — 22:00-06:00 不能工作类工具
5. **配额门** — 每天 speak 有次数上限

### 4.5 NPC间交互：对话作为连接

speak 工具与其他工具有根本区别——它建立持续对话会话而非一次性调用。

**DialogueSession 生命周期：**

```
发起: A 的 LLM 调用 speak(target=B)
  → 创建 DialogueSession(status=pending)
  → B 的 LLM 决定 accept(from=A) 或 reject(from=A, reason=...)

对话循环: status=active
  每轮：当前方 LLM 选择 speak_reply / trade / end_speak / leave
  上下文累积整个会话的对话历史
  轮次上限 5 轮

断开: 任一条件触发
  - 任一方调用 end_speak()
  - 达到 5 轮上限
  - 任一方 token budget 耗尽
  - 环境事件迫使中断

归档: 完整对话写入事件日志
  → 双方评价更新 → 关系边更新
```

对话中 NPC 可以穿插调用其他一次性工具（如 trade），结果对双方可见，对话继续。

### 4.6 NPC 决策时机

NPC 做决策只有两个时机：

| 时机 | 说明 |
|------|------|
| Orchestrator 派发的主动 turn | 整点 tick、酒馆社交配对、事件响应 |
| 回应他人发起的交互 | 收到 speak 连接请求、收到对话上一条、收到 trade 请求 |

## 5. 玩家系统

### 5.1 Player State

```
PlayerState {
  // 基础状态（所有NPC可见）
  basic: {
    name: string
    health: number
    hunger: number
    fatigue: number
    location: string
  }

  // 社交状态（酒保可见）
  social: {
    relationships: Map<NPC, number>  // 与各NPC好感度
    reputation: number               // 村庄声望
  }

  // 执法状态（警长可见）
  criminal: {
    records: string[]        // 不良记录
    wantedLevel: number      // 通缉等级
    lawfulScore: number      // 守法分数
  }

  // 心灵状态（画家可见）
  spiritual: {
    mood: string             // 情绪状态
    innerThoughts: string[]  // 内心想法记录（和梦境内容）
    creativity: number       // 创造力
  }

  // 命运状态（占卜师可见）
  destiny: {
    fateScore: number        // 命运值
    hiddenFlags: string[]    // 隐藏标记
    endingProgress: Map<string, number>  // 各结局进度
  }

  // 财富状态（乞丐可见）
  wealth: {
    gold: number
    items: Item[]
    wealthTier: string       // 贫穷/普通/富有/富豪
  }
}
```

### 5.2 状态可见性权限（白名单机制）

```
VisibilityConfig = {
  farmer:       ["basic"],
  bartender:    ["basic", "social"],
  sheriff:      ["basic", "criminal"],
  painter:      ["basic", "spiritual"],
  fortuneTeller:["basic", "destiny"],
  beggar:       ["basic", "wealth"]
}
```

默认白名单：NPC只能看到被授权的状态层级。主控Agent可动态调整权限（如：玩家获得警长信任后，警长可额外看到social状态）。

### 5.3 交互限制

- 每游戏小时：玩家最多与NPC交互 **3次**（可配置）
- 交互冷却：同一NPC第二次交互需间隔 **10游戏分钟**
- 夜间（22:00-06:00）：大部分NPC不可交互，除警长外

## 6. 游戏结局

### 6.1 结局列表

| 结局 | 触发条件概要 | 描述 |
|------|-------------|------|
| 大暴动 | 村庄不满度达到临界值，多数NPC处于极端状态 | 村庄陷入混乱 |
| 警徽 | 获得警长高度信任 + 完成执法任务链 + 守法分数达标 | 玩家成为新警长 |
| 死亡 | 玩家健康值归零 / 触发致命事件 | 游戏结束 |
| 农夫乐事 | 与农夫建立深厚关系 + 参与农事 + 安定生活 | 归隐田园 |
| 星辰大海 | 收集所有NPC的关键信息 + 命运值达标 + 触发离开事件 | 离开村庄探索世界 |

### 6.2 结局判定

主控Agent每整点检查结局条件，当满足时：
1. 触发结局事件序列
2. 播放结局叙事
3. 记录玩家成就

## 7. 叙事引擎架构

### 7.1 三层架构

```
L1: 社交关系图（骨架）
  - NPC 节点：身份 + 状态 + 位置
  - 边：态度(-10~+10) + 信任(0~10) + 共享事件
  - 玩家节点：特殊角色（可对话所有 NPC / 观察所在位置事件）

L2: 事件日志（血肉）
  - 结构化事件：{actor, tool, params, location, visible_to, caused_by}
  - 因果链：caused_by 字段连接事件
  - 信息不对称：visible_to 决定谁知道此事

L3: 评价记忆（神经系统）
  - 每个事件对每个知晓者产生评价
  - 评价 = {情感, 强度, 归因, 衰减}
  - 关系边 = 两人间所有评价的衰减加权聚合
  - 行为选择 = 状态 + 关系 + 近期评价
```

### 7.2 因果链闭合

```
事件发生 → 结构化记录(actor/tool/params/visible_to)
下次对话 → 事件日志检索(时间衰减+可见性过滤) → 注入上下文
→ NPC 行为被过去事件塑造 → 产生新事件
→ 因果链闭合
```

### 7.3 信息不对称

- 每个事件的 `visible_to` 字段运行时计算（actor + target + 同 location 旁观者）
- NPC 上下文只注入其可见的事件
- NPC 必须通过对话从别人那里获取自己不知道的信息
- 玩家不在场的事件不会出现在笔记簿中

### 7.4 玩家影响路径

| 玩家力量 | 插入层 | 效果 |
|----------|--------|------|
| 事件注入（每日1次） | L2 | 写入事件，NPC 自行反应；自定义事件有骰子搞耍态 |
| 直接对话（随时） | L1/L3 | 态度+信任变化；透露信息改变 NPC 评价 |
| 选择站队/行动 | L1/L2 | 行为直接影响关系+产生事件 |

玩家**不能**：直接改变 NPC 间关系、直接控制 NPC 行为、撤回已发生事件。不确定性由 LLM 决策 + 社交网络传播速度自然产生。

## 8. 技术挑战与解决方案

### 8.1 Token计费控制

| 策略 | 说明 |
|------|------|
| 上下文窗口管理 | 每个NPC维护固定长度的对话历史（滑动窗口） |
| 摘要压缩 | 超出窗口的历史通过摘要压缩保留关键信息 |
| 分级模型 | 简单状态判断用小模型，深度对话用大模型 |
| 缓存机制 | 相似场景的NPC响应缓存复用 |
| Token预算 | 每个游戏日设置单个NPC的Token消耗上限,"我有些累了/我需要工作了/我准备工作了，你不要打扰我了。" |

### 8.2 Prompt注入防护

| 策略 | 说明 |
|------|------|
| 输入过滤 | 玩家输入预处理，过滤明显的注入模式 |
| 角色锚定 | System prompt强化角色身份，抵抗越狱 |
| 输出验证 | NPC响应经过合规性检查 |
| 沙箱隔离 | 每个NPC Agent独立上下文，互不污染 |
| 行为边界 | 定义NPC不可能做的事（硬编码规则） |

### 8.3 上下文管理

```
NPC上下文结构：
├── System Prompt（角色设定，固定）
├── 世界状态摘要（主控Agent提供，每整点更新）
├── 自身状态描述（从状态值映射）
├── 可见的玩家状态（权限过滤后）
├── 近期记忆（最近N轮对话摘要）
└── 当前对话（实时对话内容）
```

### 8.4 Agent编排

- 主控Agent作为中心调度器
- 事件驱动架构：整点tick + 玩家交互触发
- NPC间交互通过主控Agent中转，避免直接调用

### 8.5 记忆管理

| 记忆类型 | 存储方式 | 用途 |
|---------|---------|------|
| 短期记忆 | 对话上下文窗口 | 当前对话连贯性 |
| 中期记忆 | 摘要存储 | 近期事件回忆 |
| 长期记忆 | 向量数据库/结构化存储 | 关键事件、关系变化 |
| 世界记忆 | 主控Agent维护 | 全局事件时间线 |

## 9. Demo 阶段规划

### Phase 1：最小可行���品（1-2个Agent）

**目标**：验证核心交互循环

**范围**：
- 实现 **农夫** + **酒保** 两个NPC Agent
- 基础时间系统（简化版，手动推进）
- 玩家对话交互
- NPC状态系统 + 状态→上下文映射
- 基础Player State + 权限可见性
- 一个可达成的结局（农夫乐事）

**不包含**：
- NPC间自主交互
- 复杂结局判定
- 向量数据库记忆
- 流速调节UI

### Phase 2：核心体验完善

- 增加警长、画家
- NPC间交互系统
- 完整时间系统 + 流速调节
- 多结局支持
- 记忆系统升级

### Phase 3：完整版本

- 全部6个NPC
- 所有结局
- 性能优化 + Token成本控制
- Prompt注入防护加固
- 前端UI完善

## 10. 技术栈选型（已确认）

| 层级 | 选型 | 说明 |
|------|------|------|
| 前端 | Vue 3 | SPA，对话界面 + 状态面板 |
| 后端 | Python | FastAPI / WebSocket |
| LLM | DeepSeek | 主要对话模型 |
| 存储 | 本地文件 / SQLite | 游戏存档，后续可迁移数据库 |

## 11. 核心系统模块

### 11.1 叙事引擎数据模型

**L1：社交关系图**

```python
class RelationshipEdge:
    source: str              # NPC A
    target: str              # NPC B（或 player）
    attitude: float          # -10 ~ +10
    trust: float             # 0 ~ 10
    shared_event_ids: List[str]
    last_interaction_day: int

# 存储：data/users/{user_id}/social_graph.json
```

**L2：事件日志**

```python
class GameEvent:
    id: str                  # "evt_003_farmer_speak_bartender"
    day: int / hour: int / location: str
    actor: str               # "farmer" | "bartender" | "player" | "world"
    tool: str                # "speak" | "trade" | "farm" | "move" ...
    params: dict
    result: dict | None
    visible_to: List[str]    # actor + target + 同 location 旁观者
    caused_by: str | None    # 父事件 ID
    dialogue_session_id: str | None

# 存储：data/users/{user_id}/events/day_003.jsonl（按天分文件追加写入）
```

**L3：评价记忆**

```python
class Evaluation:
    id: str
    evaluator: str           # "farmer"
    about: str               # "bartender" | "event_xxx"
    emotion: str             # "anger" | "gratitude" | "resentment" | ...
    intensity: float         # 0 ~ 1
    attribution: str         # "因为他涨价" | "玩家告诉我的"
    triggered_by_event: str  # 触发事件 ID
    day: int
    decay_rate: float        # 0.05/day

# 关系态度投影：attitude = sum(e.intensity * e.decay_weight * valence(e.emotion) for e in 两人双向评价)
# 存储：data/users/{user_id}/evaluations/{npc_id}.jsonl
```

**与现有文件的映射：**

| 现有文件 | 新系统对应 |
|----------|-----------|
| user.md | L3 评价中 about=player 的聚合视图 |
| agent_mem.md | L1 关系边 + L3 评价中 about=other_NPC 的聚合视图 |
| self.md | L2 事件中 actor=NPC 的自我视角 + NPCState |
| world_state.json | L2 事件中 visible_to=["world"] 的过滤视图 |

现有 markdown 文件保留为人类可读聚合视图（便于调试），推理全部走结构化数据。

### 11.2 Agent编排系统

**运行时流程：**

```
整点 Tick:
  1. 更新所有 NPC 状态（hunger-5, fatigue+5）
  2. 每个 NPC 获得一次自主决策 turn
  3. 18:00-22:00 → 触发酒馆社交配对（按关系权重随机配对在场 NPC）
  4. 每对建立 DialogueSession（3-5 轮）
  5. 产生事件 → 写回三层
  6. 自动存档

事件广播:
  1. 事件写入 L2
  2. Orchestrator 筛选 affected NPC（visible_to 包含此事件的所有 NPC）
  3. 每个受影响 NPC 获得额外决策 turn
  4. NPC 自由选择反应
```

### 11.3 工具系统

所有 NPC 行为统一为工具调用。NPC 的工具选择由 LLM function calling 全权决定，策略管道约束边界。

**工具分类：**

| 类别 | 工具 | 使用者 |
|------|------|--------|
| 社交 | speak, speak_reply, end_speak, accept, reject, gossip, trade | 所有 NPC + 玩家 |
| 职业 | farm | 农夫 |
| 职业 | brew | 酒保 |
| 职业 | patrol | 警长 |
| 职业 | divine | 占卜师 |
| 职业 | paint | 画家 |
| 生存 | eat, sleep, rest, move | 所有 NPC |

**工具策略管道（五层过滤）：**

```
1. 身份门   — 农夫不能 brew()，酒保不能 farm()
2. 状态门   — fatigue > 80 时不能做复杂社交
3. 关系门   — trust < 30 时对话语气受限
4. 时间门   — 22:00-06:00 不能工作类工具
5. 配额门   — 每天 speak 有次数上限
```

NPC 每个 turn 看到的可用工具列表是管道过滤后的结果，以 function calling schema 注入 LLM 上下文。

### 11.4 Token预算控制

```
TokenBudget {
  per_npc_daily: number     // 每个NPC每游戏日的token上限
  warning_threshold: 0.8    // 80%时NPC开始"疲惫"减少对话
  hard_limit: 1.0           // 100%时完全停止LLM调用
}
```

**达到上限后的NPC行为：**
- 80%阈值：NPC回复变短，倾向结束对话（"我有些累了"）
- 100%硬上限：NPC使用预设模板回复，不触发LLM

**NPC间交互token预估：**
一次 NPC↔NPC 5 轮对话约 7,000 tokens，每天酒馆社交 3 轮配对约 21,000 tokens。需调高 NPC 每日预算或 NPC 间交互使用低成本模型。Token 耗尽时该 NPC 跳过社交轮次。

### 11.5 NPC初始化系统

**背景设定 + 预运行：**

1. **背景设定文本**：每个NPC有详细的背景故事文档，定义：
   - 身世、性格、习惯
   - 与其他NPC的初始关系
   - 核心动机和背景故事

2. **预运行天数**：游戏开始前模拟N天NPC生活
   - 生成初始记忆（agent_mem.md已有内容）
   - 建立NPC间的既有关系和话题
   - 让世界有"已经运转过"的质感
   - 预运行可用低成本模型 + 简化prompt

## 12. 多用户架构（预留）

当前单用户，但数据层按多用户设计：

```
data/
├── users/
│   ├── user_001/
│   │   ├── player_state.json   # 全自动存档，实时写入
│   │   ├── world_state.json    # 该用户的世界状态快照
│   │   └── memory/             # 该用户视角下的NPC记忆
│   └── user_002/
│       └── ...
└── shared/
    └── npc_backgrounds/     # NPC背景设定（所有用户共享）
```

- 存档隔离：每个用户独立存档，互不影响
- 后续可扩展为多人在线（共享世界状态，独立玩家状态）

## 13. 结局触发条件（已确认部分）

### 农夫乐事

| 条件 | 阈值 |
|------|------|
| 与农夫好感度 | ≥ 80（高） |
| 完成作物收获种类 | ≥ 2种 |
| 参与耕作次数 | ≥ 5次（待定） |

其他结局的具体数值阈值待后续设计。

## 14. 补充设计决策（已确认）

| 决策项 | 结论 |
|--------|------|
| NPC行为统一 | 工具调用 + LLM function calling 全权决策 + 五层策略管道约束 |
| NPC间交互协议 | DialogueSession：connect → accept → dialogue_loop → disconnect |
| 交互发起方式 | LLM 在可用工具中自主选择 speak(target=...) |
| 叙事架构 | 三层：社交关系图(L1) + 事件日志(L2) + 评价记忆(L3) |
| 因果链 | L2 events 的 caused_by 字段连接，L3 评价的 triggered_by_event 追踪 |
| 信息不对称 | L2 events 的 visible_to 字段运行时计算，NPC 只能注入其可见事件 |
| 玩家影响 | 事件注入→L2 / 直接对话→L1+L3 / 不能直接改变NPC间关系或控制NPC行为 |
| 后端架构 | 混合模式：单体进程 + 内部消息总线抽象 + 状态存储接口 |
| NPC背景设定 | 混合方案：极简启动 + 结构化字段（日常习惯、核心动机、说话风格） |
| 时间流逝 | 暂停制：玩家退出后世界冻结 |
| 玩家输入方式 | 选项+自由文本混合：系统提供2-3个情境化选项，保留自由输入 |
| NPC间交互频率 | 3-5次/天（酒馆时段） |
| 预运行天数 | 5天 |
| 存档机制 | 全自动存档：任何状态变化实时写入 |
| 状态约束 | 混合约束：对话始终可行，工具使用受状态限制 |
| 结局模式 | 隐性互斥：触发条件对玩家不可见，某路线超阈值后其他路线降温 |
| 结局/死亡后处理 | 叙事包装重生：保留部分状态继承（好感度×0.3），NPC记忆清空 |
| LLM Client | 异步请求队列 + 并发控制 + 每用户独立Token预算 + 请求优先级 |
| NPC上下文动态加载 | 从结构化事件日志中检索，替代关键词匹配 |
| 记忆衰减 | 评价记忆自带衰减率（0.05/day），关系边为衰减加权聚合 |

## 15. 待确认事项

- [ ] Token预算具体数值（每NPC每日，需考虑NPC间交互消耗）
- [ ] 工具系统的完整前置条件数值
- [ ] 各结局的完整触发条件数值
- [ ] DeepSeek具体模型版本（deepseek-chat / deepseek-reasoner）
- [ ] NPC间交互使用低成本模型的成本评估
