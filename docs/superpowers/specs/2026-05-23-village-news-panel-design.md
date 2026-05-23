# 村庄见闻面板 设计规格

> 日期：2026-05-23
> 状态：设计完成，待实现

## 1. 目标

将前端主页面的酒馆面板改造为"村庄见闻"——一个全局 NPC 对话实时 feed，展示任意 NPC 组合之间的对话，不限地点。同时隐藏当前未使用的"可用工具"和"偷听模块"。

## 2. 设计决策

| 决策项 | 选择 | 理由 |
|--------|------|------|
| 面板定位 | 全局 NPC 对话 feed，不限地点 | 后期 NPC 增多，对话在各处发生 |
| 展示时机 | 实时逐条推送 | 直播围观感 |
| 对话分隔 | 分隔卡片标注日期/时间/地点 | 区分不同轮次 |
| 历史容量 | 保留最近 20 轮对话，FIFO | 保持面板轻量 |
| Tab 名称 | "👂 村庄见闻" | 沉浸叙事风格 |
| 可用工具模块 | 隐藏（注释或 v-if=false） | 当前未使用 |
| 偷听模块 | 隐藏（注释或 v-if=false） | 当前未使用 |

## 3. 后端推送协议

InteractionRunner 在对话过程中通过主 WebSocket（`ws_manager`）逐条广播三种消息：

### 3.1 对话开始

```json
{
  "type": "npc_conversation_start",
  "conversation_id": "conv_d3h20_farmer_bartender",
  "day": 3,
  "hour": 20,
  "location": "tavern",
  "participants": ["farmer", "bartender"]
}
```

### 3.2 对话消息（每条话逐一推送）

```json
{
  "type": "npc_conversation_message",
  "conversation_id": "conv_d3h20_farmer_bartender",
  "speaker_id": "farmer",
  "speaker_name": "农夫·乔治",
  "content": "今天的麦酒闻起来不错啊。"
}
```

### 3.3 对话结束

```json
{
  "type": "npc_conversation_end",
  "conversation_id": "conv_d3h20_farmer_bartender",
  "summary": "乔治夸了新酿的麦酒，Gus介绍了蜂蜜新配方。"
}
```

### 3.4 conversation_id 生成规则

格式：`conv_d{day}h{hour}_{sorted_participant_ids_joined_by_underscore}`

确保同一次对话的所有消息可以关联到同一个 ConversationBlock。

## 4. 前端数据结构

```typescript
// conversationStore.ts
interface ConversationMessage {
  speakerId: string
  speakerName: string
  content: string
}

interface ConversationBlock {
  id: string
  day: number
  hour: number
  location: string
  participants: string[]
  messages: ConversationMessage[]
  finished: boolean
  summary?: string
}

// store state
conversations: ConversationBlock[]  // 最多 20 轮，超出 FIFO 移除最旧的
```

## 5. 前端面板布局

```
┌─────────────────────────────────────┐
│ 👂 村庄见闻                    实时 ● │
├─────────────────────────────────────┤
│ ── Day 3 20:00 · 酒馆 ──           │
│                                     │
│ [头像] 农夫·乔治                    │
│  "今天的麦酒闻起来不错啊。"          │
│                                     │
│ [头像] 酒馆老板·Gus                 │
│  "新酿的，加了点蜂蜜。"             │
│                                     │
│ [头像] 农夫·乔治                    │
│  "......" (对话进行中 ●)            │
│                                     │
├─── ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ────┤
│ ── Day 3 14:00 · 市场 ──           │
│                                     │
│ [头像] 农夫·乔治                    │
│  "今天这商人卖的种子看着不错。"      │
│ ...                                 │
└─────────────────────────────────────┘
```

### 5.1 视觉规则

- 每轮对话以分隔行开头：`── Day X HH:00 · 地点中文名 ──`
- 消息逐条追加到当前对话块底部
- 新消息到达时自动滚动到底部（除非用户正在向上翻阅）
- 正在进行中的对话块，分隔行右侧有呼吸灯（● 绿色闪烁）
- 对话结束后呼吸灯消失，可选展示一行灰色总结文字
- 最新对话在最上方（新对话 prepend 到列表顶部）
- 头像复用现有 NPC 头像资源（AVATAR_MAP）

## 6. GamePage 布局调整

### 6.1 隐藏模块

- `ToolPanelV2`（可用工具）：从模板中用 `v-if="false"` 隐藏或注释
- `EavesdropPanel`（偷听模块）：同上

### 6.2 Tab 改名

中间栏的 tab 从 `"🍺 酒馆"` 改为 `"👂 村庄见闻"`。

## 7. 文件清单

### 新增文件

| 文件 | 职责 |
|------|------|
| `client/src/stores/conversationStore.ts` | 管理 ConversationBlock 数组，处理 3 种 WebSocket 消息 |
| `client/src/components/VillageNewsPanel.vue` | 村庄见闻面板组件 |

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `client/src/pages/GamePage.vue` | Tab 改名；引入 VillageNewsPanel 替换 TavernPanel；隐藏 ToolPanelV2 和 EavesdropPanel |
| `client/src/services/websocket.ts` 或 `GamePage.vue` 的 ws handler | 新增 3 种消息类型分发到 conversationStore |
| `server/core/interaction_runner.py` | 对话过程中逐条广播 WebSocket 消息（start/message/end） |

### 删除/废弃文件

| 文件 | 处理 |
|------|------|
| `client/src/components/TavernPanel.vue` | 删除或保留不引用 |
| `mockStore.ts` 中 `tavernConversations` | 移除相关 mock 数据 |

## 8. 不在本次范围内

- 对话内容的持久化（当前仅 session 内保留）
- 玩家参与 NPC 对话
- 对话回放/历史查看页面
- 头像气泡动画
