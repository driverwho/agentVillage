# NPC 自主活动循环设计

## 概述

让 NPC 随游戏时间自动运行：在决策点和空闲时触发 LLM 决策，选择带时长的工具执行，形成自然的日常行为循环。本次迭代不含 NPC 对话系统和玩家交互。

## 核心模型

NPC 在 IDLE 和 ACTIVE 两个状态之间循环：

```
IDLE（空闲）→ 触发 LLM 决策 → 选择工具 → ACTIVE（执行中, duration）
ACTIVE → 活动完成 / 决策点到达 / 事件中断 → IDLE（附中断原因）
```

NPC 永远不会"停着"——完成活动后立即进入空闲并触发下一次决策。

## 1. NPC 活动状态 (ActivityState)

每个 NPC 新增运行时状态，不持久化到存档（重启时默认 idle）：

```python
@dataclass
class ActivityState:
    status: Literal["idle", "active"] = "idle"
    current_tool: str | None = None      # 正在执行的工具名
    end_hour: int | None = None          # 活动结束的游戏小时（绝对值，跨天用 day*24+hour）
    end_day: int | None = None           # 活动结束的游戏天
    idle_reason: str | None = None       # 上一次进入空闲的原因
```

状态转换由 Orchestrator 驱动，NPC 自身不主动改变状态。

## 2. 工具时长

每个 NPCTool 新增 `duration_hours: int` 类属性，表示执行该工具消耗的游戏小时数。

| 工具 | duration_hours | 说明 |
|------|---------------|------|
| eat | 1 | 吃饭 |
| sleep | 动态计算 | 到次日 6:00 的小时差（若当前 22:00 则 8 小时） |
| rest | 2 | 短暂休息 |
| move | 1 | 移动到目标地点 |
| farm | 4 | 田间劳作 |
| brew | 3 | 酿酒 |
| patrol | 3 | 巡逻 |
| divine | 2 | 占卜 |
| paint | 3 | 绘画 |

sleep 的时长计算：`(24 - current_hour + 6) % 24`，最少 6 小时，最多 10 小时。

## 3. 触发 LLM 决策的三种条件

| 触发类型 | 条件 | idle_reason |
|----------|------|-------------|
| 决策点 | `hour ∈ DECISION_POINTS` | "到了{hour}:00决策时间" |
| 活动完成 | `game_time >= activity.end_time` | "完成了{tool_name}" |
| 事件中断 | `hunger<20 / fatigue>90 / health<20` | "因为{condition}中断了{tool_name}" |

决策点配置：

```python
DECISION_POINTS = [6, 12, 18, 20]
```

优先级：事件中断 > 决策点 > 活动完成（同一 tick 内多个条件满足时，idle_reason 取最高优先级的）。

## 4. Orchestrator Tick 改造

现有 `_auto_tick_loop` 每 10 秒触发一次（= 1 游戏小时）。改造后每 tick 执行：

```
步骤 1: 更新所有 NPC 状态值（hunger-5, fatigue+5）         ← 已有
步骤 2: 检查事件中断 → 满足条件的 ACTIVE NPC 进入 idle
步骤 3: 检查活动完成 → end_time 到达的 ACTIVE NPC 进入 idle
步骤 4: 检查决策点 → hour ∈ DECISION_POINTS 时，所有 ACTIVE NPC 进入 idle
步骤 5: 对所有 IDLE NPC 调用 run_tool_turn → 解析工具 → 设置 ActivityState → 进入 active
步骤 6: 自动存档                                          ← 已有
```

步骤 5 中 LLM 调用是异步的，所有 idle NPC 可并发发起请求。

## 5. LLM 上下文增强

在 NPC 自主 turn 时，current_input 注入活动上下文：

```
【行动指令】
当前时间：Day {day}, {hour}:00
你的位置：{location}
你的状态：空闲
上一个活动：{last_tool}（{idle_reason}）
请从可用工具中选择你接下来要做的事情。
```

如果是游戏开始的第一次决策（无上一个活动）：

```
【行动指令】
当前时间：Day 1, 6:00
你的位置：家
你的状态：刚起床
新的一天开始了，请决定你要做什么。
```

## 6. 工具执行后的状态变更

工具 execute() 返回的 state_changes 在 tick 时立即应用。同时 Orchestrator 设置：

```python
npc.activity_state = ActivityState(
    status="active",
    current_tool=tool_name,
    end_day=计算后的天,
    end_hour=计算后的小时,
    idle_reason=None,
)
```

若 LLM 未调用任何工具（返回纯文本），视为"闲逛"，默认持续 1 小时后再次进入空闲。

## 7. 中断条件

当前实现的中断条件（可扩展）：

```python
INTERRUPT_CONDITIONS = [
    ("hunger", lambda s: s.hunger < 20, "饥饿难耐"),
    ("fatigue", lambda s: s.fatigue > 90, "极度疲惫"),
    ("health", lambda s: s.health < 20, "身体虚弱"),
]
```

中断只对 ACTIVE 状态的 NPC 生效。已经处于 idle 的 NPC 不会被重复中断。

## 8. NPC 位置追踪

新增简单的位置系统，每个 NPC 有 `location` 属性：

```python
# NPCAgent 新增
self.location: str = "home"  # 默认在家
```

MoveTool 执行时更新位置。位置信息注入 LLM 上下文，影响工具可用性（未来可扩展：farm 需要在 field，brew 需要在 tavern）。

本次迭代位置仅作为上下文信息，不做工具可用性约束。

## 9. Token 预算考量

每次自主 turn 消耗 token。按当前配置（5000 token/NPC/天）：
- 预计每天 6-10 次 LLM 调用（4 个决策点 + 2-6 次活动完成触发）
- 每次约 400-600 token（上下文 + 回复）
- 总计约 3000-5000 token/NPC/天，在预算内

Token 耗尽时 NPC 跳过 LLM 调用，默认执行 rest（2 小时），等待次日重置。

## 10. 不包含（本次迭代）

- NPC 间对话（speak/accept/reject/end_speak）
- 玩家交互
- 位置约束工具可用性
- NPC 间事件中断（"有人找你说话"）
- 活动的状态效果随时间渐变（如 farm 每小时+5 fatigue，而非结束时一次性+15）

## 11. 与现有系统的关系

| 现有模块 | 变化 |
|----------|------|
| `server/core/orchestrator.py` | tick 循环改造，新增步骤 2-5 |
| `server/agents/base_agent.py` | 新增 `activity_state` 和 `location` 属性 |
| `server/tools/base_tool.py` | NPCTool 新增 `duration_hours` 属性 |
| `server/tools/definitions.py` | 所有工具添加 duration_hours 值 |
| `server/tools/setup.py` | 新增 `build_autonomous_context()` 辅助函数 |
| `server/api/routes.py` | 现有 `/npc/{npc_id}/turn` 端点保持不变 |

新增文件：
- `server/core/activity_manager.py` — ActivityState 管理、中断检查、完成检查逻辑
