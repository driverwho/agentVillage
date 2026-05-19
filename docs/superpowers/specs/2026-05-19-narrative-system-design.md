# 叙事系统设计 — 多 Agent 持续交互与玩家影响

## 概述

设计 Agent Village 的叙事引擎，使 NPC 之间的交互可持续、非形式化、在玩家略微操控下有不同发展。核心思路：以社交关系图为骨架，事件日志为血肉，评价记忆为神经系统，三层各司其职；所有 NPC 行为统一为工具调用，由 LLM 全权决策，策略管道定义边界。

## 1. 核心架构：叙事引擎三层

```
┌─────────────────────────────────────────┐
│            叙事引擎三层                   │
├─────────────────────────────────────────┤
│  L1: 社交关系图（骨架）                    │
│  - NPC 节点：身份 + 状态 + 位置            │
│  - 边：态度 + 信任 + 共享事件              │
│  - 玩家节点：特殊角色（对话所有NPC/观察）    │
│  - 信息沿边流动：信任高 → 对话多 → 信息传递  │
├─────────────────────────────────────────┤
│  L2: 事件日志（血肉）                      │
│  - 结构化事件：{actor, tool, params,        │
│     location, visible_to, caused_by}     │
│  - 因果链：caused_by 字段连接事件           │
│  - 信息不对称：visible_to 决定谁知道        │
├─────────────────────────────────────────┤
│  L3: 评价记忆（神经系统）                   │
│  - 每个事件对每个知晓者产生评价              │
│  - 评价 = {情感, 强度, 归因, 衰减}          │
│  - 关系边 = 两人间所有评价的衰减加权聚合      │
│  - 行为选择 = 状态 + 关系 + 近期评价         │
└─────────────────────────────────────────┘
```

## 2. 决策模型

### 2.1 工具作为 NPC 行为的统一接口

所有 NPC 行为通过工具调用表达。工具分三类：

| 类别 | 工具 | 特性 |
|------|------|------|
| 社交 | speak, speak_reply, end_speak, accept, reject, gossip | speak 建立对话会话，其他是一次性 |
| 职业 | farm, brew, patrol, divine, paint, trade | 一次性调用 |
| 生存 | eat, sleep, rest, move | 一次性调用 |

### 2.2 LLM 全权决策

NPC 在每一 turn 的决策由 LLM function calling 完成。系统注入可用工具列表（由策略管道过滤），LLM 自主选择调用哪个工具及参数。没有规则引擎预选。

决策时机：
- **整点 tick**：每个 NPC 获得一次评估机会，自由选择行为
- **酒馆社交**：被配对的 NPC 获得 speak 机会
- **事件响应**：被事件影响的 NPC 获得额外反应 turn
- **回应交互**：收到 speak 连接/对话/交易请求时决定如何回应

### 2.3 工具策略管道

五层过滤，约束 NPC 行为边界：

```
1. 身份门   — 农夫不能 brew()，酒保不能 farm()
2. 状态门   — fatigue > 80 时不能做复杂社交
3. 关系门   — trust < 30 时对话语气受限
4. 时间门   — 22:00-06:00 不能工作类工具
5. 配额门   — 每天 speak 有次数上限
```

## 3. 对话作为连接

### 3.1 speak 与其他工具的区别

一次性工具：`call → execute → result → done`
对话工具：`connect → accept → dialogue_loop → disconnect`

### 3.2 DialogueSession 生命周期

```
发起: A 的 LLM 调用 speak(target=B)
  → 创建 DialogueSession(status=pending)
  → B 的 LLM 决定 accept(from=A) 或 reject(from=A, reason=...)

对话循环: status=active
  每轮：当前方 LLM 选择 speak_reply / trade / end_speak / leave
  上下文累积整个会话的对话历史

断开: 任一条件触发
  - 任一方调用 end_speak()
  - 达到 5 轮上限
  - 任一方 token budget 耗尽
  - 环境事件迫使中断

归档: 完整对话写入 L2 事件日志
  → 双方 L3 评价更新 → L1 关系边更新
```

### 3.3 对话中穿插其他工具

对话会话中 NPC 可以调用其他一次性工具（如 trade），结果对双方可见，对话继续。

## 4. 信息不对称与可见范围

### 4.1 事件可见性

每个事件有 `visible_to` 字段，运行时根据 location 计算旁观者：

```
speak(酒保, 农夫, location=酒馆) → visible_to = [酒保, 农夫, 当时也在酒馆的NPC]
trade(酒保, 商人, location=后门) → visible_to = [酒保, 商人]
```

### 4.2 NPC 信息不对称

NPC 的上下文只注入他可见的事件。NPC 必须通过对话从别人那里获取他不知道的信息。这是叙事动力的关键来源。

### 4.3 玩家信息不对称

- 玩家在当前 location → 可见该 location 的公开事件
- 玩家不在场 → 只能通过后续对话打听到
- 玩家笔记簿只记录玩家目击或听说的内容

## 5. 玩家影响路径

### 5.1 事件注入（每日1次）

```
随机事件卡 → L2 写入（匿名事件，NPC 自行归因）
自定义事件+骰子 → L2 写入（可追溯，有搞耍失败态）

事件不可撤销。NPC 的反应由各自的 LLM 自主决定。
```

### 5.2 直接对话（随时）

| 行为 | 影响层 | 效果 |
|------|--------|------|
| 与 NPC 对话 | L1 | 玩家↔NPC 态度+信任变化 |
| 提及另一个 NPC | L3 | 听者对被提及者的评价可能改变 |
| 透露信息 | L3 | 改变 NPC 对某人/某事的评价 |
| 行动（trade/协助） | L1/L2 | 行为直接影响关系+产生事件 |

### 5.3 操控分寸

- 玩家**能做的**：注入事件、提供信息、表达态度、选择站队
- 玩家**不能做的**：直接改变 NPC 关系、直接控制 NPC 行为、撤回已发生事件
- 不确定性由 LLM 决策 + 社交网络传播速度自然产生

## 6. 数据模型

### 6.1 L1：社交关系图

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

### 6.2 L2：事件日志

```python
class GameEvent:
    id: str                  # "evt_003_farmer_speak_bartender"
    day: int
    hour: int
    location: str
    actor: str               # "farmer" | "bartender" | "player" | "world"
    tool: str                # "speak" | "trade" | "farm" | "move" ...
    params: dict
    result: dict | None
    visible_to: List[str]
    caused_by: str | None    # 父事件 ID
    dialogue_session_id: str | None

# 存储：data/users/{user_id}/events/day_003.jsonl（按天分文件，追加写入）
```

### 6.3 L3：评价记忆

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

# 关系边的态度投影：
# attitude = sum(e.intensity * e.decay_weight * valence(e.emotion)
#                for e in 两人的双向评价)

# 存储：data/users/{user_id}/evaluations/{npc_id}.jsonl
```

### 6.4 与现有存储的映射

| 现有文件 | 新系统对应 |
|----------|-----------|
| user.md | L3 评价中 evaluator=NPC, about=player 的聚合视图 |
| agent_mem.md | L1 关系边 + L3 评价中 about=other_NPC 的聚合视图 |
| self.md | L2 事件中 actor=NPC 的自我视角 + NPCState |
| world_state.json | L2 事件中 visible_to=["world"] 的过滤视图 |
| (新增) | social_graph.json |
| (新增) | events/ 目录 |
| (新增) | evaluations/ 目录 |

现有 markdown 文件保留为人类可读的聚合视图（便于调试），系统推理全部走结构化数据。

## 7. 运行时流程

### 7.1 整点 Tick

```
1. 更新所有 NPC 状态（hunger-5, fatigue+5）
2. 每个 NPC 获得一次自主决策 turn
3. 18:00-22:00 → 触发酒馆社交配对
4. 自动存档
```

### 7.2 酒馆社交配对

```
1. Orchestrator 按关系权重随机配对在场 NPC
2. 每对进行 DialogueSession（3-5 轮）
3. 产生事件 → 写回三层
```

### 7.3 事件响应广播

```
1. 事件写入 L2
2. Orchestrator 筛选 affected NPC（visible_to 包含此事件的所有 NPC）
3. 每个受影响 NPC 获得额外决策 turn
4. NPC 自由选择反应
```

## 8. Token 预算考量

一次 NPC↔NPC 的 5 轮对话预估 ~7,000 tokens。每天酒馆社交 3 轮配对 ~21,000 tokens。当前 TokenBudget(5000/NPC/天) 不足以支撑 NPC 间交互。需要：
- 调高 NPC 每日预算
- NPC 间交互使用低成本模型
- Token 耗尽时该 NPC 跳过社交轮次

## 9. 不在此设计中的内容

- 秘密系统（已移除）
- 结局系统（v1 设计，待后续调整）
- 重生/轮回机制
- 多用户共享世界
- 向量检索（暂用结构化检索，字段匹配 + 时间衰减）
