# NPC 观察页面设计

## 概述

独立路由页面 `/observe`，通过 WebSocket 实时展示所有 NPC 的活动状态、LLM 调用信息和历史记录。用于开发调试和行为观察。

## 1. 页面布局

全屏自适应网格，每个 NPC 一个卡片。卡片使用 CSS Grid 自动填充（`auto-fill, minmax(320px, 1fr)`），2 个 NPC 时两列，6 个 NPC 时自动换行。

### NPC 卡片结构（从上到下）

1. **头像区**：128px 像素风头像，居中
2. **基础信息**：名字、位置（中文）、当前活动状态、结束时间
3. **状态条**：health/hunger/fatigue/mood 四条进度条 + 数值
4. **LLM 状态指示器**：空闲 / 请求中(spinner) / 完成
5. **历史记录**：最近 5 条 LLM 调用（时间 + 工具名 + 回复摘要 + token 消耗）

### 页面 header

标题 "Agent Village — NPC 观察面板" + 返回游戏按钮 + WebSocket 连接状态指示灯（绿/红）

## 2. 数据流

### 初始加载

```
页面 mounted → GET /api/npcs/status → 全量快照填充 store
            → WebSocket connect /ws/observe → 监听增量推送
```

### 实时更新

后端在以下时机广播 WebSocket 事件：

| 时机 | 事件类型 | payload |
|------|---------|---------|
| NPC 活动状态变更（idle→active、active→idle） | `npc_activity_change` | `{npc_id, status, current_tool, end_day, end_hour, idle_reason, location}` |
| LLM 调用开始 | `npc_llm_start` | `{npc_id, timestamp}` |
| LLM 调用完成 | `npc_llm_done` | `{npc_id, tool_used, message, tokens, timestamp}` |
| 状态值更新（每 tick） | `npc_state_update` | `{npc_id, health, hunger, fatigue, mood}` |

### Store 结构

```typescript
interface NPCObserveData {
  id: string
  name: string
  avatar: string
  location: string
  activity: {
    status: 'idle' | 'active'
    currentTool: string | null
    endDay: number | null
    endHour: number | null
    idleReason: string | null
  }
  state: { health: number; hunger: number; fatigue: number; mood: number }
  llmStatus: 'idle' | 'requesting' | 'done'
  history: Array<{
    timestamp: string
    tool: string
    message: string
    tokens: number
  }>  // 最多保留 5 条
}
```

## 3. 后端改造

### 新增 REST API

`GET /api/npcs/status` — 返回所有 NPC 当前快照：

```json
{
  "npcs": {
    "farmer": {
      "name": "农夫·乔治",
      "location": "field",
      "activity": {"status": "active", "current_tool": "farm", "end_day": 1, "end_hour": 12},
      "state": {"health": 100, "hunger": 55, "fatigue": 40, "mood": 60},
      "llm_status": "idle",
      "history": []
    }
  },
  "game_time": {"day": 1, "hour": 8, "minute": 0}
}
```

### 新增 WebSocket 端点

`/ws/observe` — 观察专用 WebSocket 连接。复用现有 `ConnectionManager`，但使用独立实例（与游戏 WS 分离）。

### 广播时机

在 Orchestrator 的以下位置插入广播调用：
- `_on_hour_tick` 步骤 1 后 → `npc_state_update`
- `_on_hour_tick` 步骤 2-4（状态转换时）→ `npc_activity_change`
- `_single_autonomous_turn` 开始 → `npc_llm_start`
- `_single_autonomous_turn` 结束 → `npc_llm_done` + `npc_activity_change`

## 4. 前端新增文件

| 文件 | 职责 |
|------|------|
| `client/src/router.ts` | Vue Router 配置（/ → App, /observe → ObservePage） |
| `client/src/pages/ObservePage.vue` | 观察页面主组件 |
| `client/src/components/NPCObserveCard.vue` | 单个 NPC 观察卡片 |
| `client/src/stores/observeStore.ts` | WebSocket 连接 + NPC 观察数据管理 |

### 改造现有文件

| 文件 | 变更 |
|------|------|
| `client/src/main.ts` | 添加 vue-router |
| `client/src/App.vue` | 改为 `<router-view />`，原内容移为 GamePage |
| `client/src/pages/GamePage.vue` | 现有 App.vue 的游戏内容 |
| `server/api/routes.py` | 新增 `/api/npcs/status` 端点 |
| `server/core/orchestrator.py` | 在关键位置插入 ws broadcast |

## 5. 视觉风格

保持现有像素风主题：
- 背景色 `--color-bg` (#2c1f16)
- 卡片背景 `--color-panel` (#3d2d20)
- 边框 `--color-border` (#7a5540) 2px solid
- 字体 `--font-pixel` 用于标题和数值
- 字体 `--font-body` 用于历史摘要文本
- 状态条颜色复用 `--color-health/hunger/fatigue/info`
- 金色高亮 `--color-accent` (#daa520) 用于活动中的 NPC 卡片边框

## 6. 依赖新增

- `vue-router` (^4.x) — 前端路由

## 7. 不包含

- 手动触发 NPC 行为的控制按钮（后续迭代）
- NPC 间对话的实时展示（对话系统尚未实现）
- 历史记录持久化到后端（当前仅前端内存保留最近 5 条）
