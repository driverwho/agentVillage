# 村庄见闻面板 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 将酒馆面板改造为"村庄见闻"实时 NPC 对话 feed，通过 WebSocket 逐条推送对话消息到前端。同时隐藏未使用的工具面板和偷听面板。

**架构：** InteractionRunner 在对话过程中逐条通过 ws_manager 广播消息（start/message/end）；前端 conversationStore 管理对话块数组；VillageNewsPanel 渲染实时对话流。

**技术栈：** Python/FastAPI WebSocket / Vue 3 + Pinia + TypeScript

**规格文档：** `docs/superpowers/specs/2026-05-23-village-news-panel-design.md`

---

## 文件结构

### 新增文件

| 文件 | 职责 |
|------|------|
| `client/src/stores/conversationStore.ts` | 管理 ConversationBlock 数组，处理 3 种 WebSocket 消息类型 |
| `client/src/components/VillageNewsPanel.vue` | 村庄见闻面板 UI 组件 |

### 修改文件

| 文件 | 修改内容 |
|------|----------|
| `server/core/interaction_runner.py` | 在对话过程中逐条广播 WebSocket 消息 |
| `client/src/pages/GamePage.vue` | 替换 TavernPanel 为 VillageNewsPanel，改 tab 名，隐藏 ToolPanelV2 和 EavesdropPanel，扩展 ws handler |

---

## 任务 1：后端 InteractionRunner 广播对话消息

**文件：**
- 修改：`server/core/interaction_runner.py`

- [ ] **步骤 1：在 run_conversation 中添加 WebSocket 广播**

在 `server/core/interaction_runner.py` 的 `run_conversation` 方法中，在对话循环之前广播 `start`，在每条消息生成后广播 `message`，在对话结束后广播 `end`。

修改 `run_conversation` 方法，在 `activity_mgr.transition_to_active` 之后、对话循环之前添加：

```python
        from server.api.ws import ws_manager
        import asyncio

        conversation_id = f"conv_d{game_time.day}h{game_time.hour}_{'_'.join(sorted([initiator.id if hasattr(initiator, 'id') else initiator.agent_id, target.id if hasattr(target, 'id') else target.agent_id]))}"

        try:
            asyncio.ensure_future(ws_manager.broadcast({
                "type": "npc_conversation_start",
                "conversation_id": conversation_id,
                "day": game_time.day,
                "hour": game_time.hour,
                "location": location,
                "participants": sorted([
                    initiator.id if hasattr(initiator, 'id') else initiator.agent_id,
                    target.id if hasattr(target, 'id') else target.agent_id,
                ]),
            }))
        except RuntimeError:
            pass
```

在对话循环中，每次 `dialogue.append(...)` 之后添加：

```python
            try:
                asyncio.ensure_future(ws_manager.broadcast({
                    "type": "npc_conversation_message",
                    "conversation_id": conversation_id,
                    "speaker_id": speaker_id,
                    "speaker_name": speaker.identity.get("name", speaker_id),
                    "content": dialogue[-1]["content"],
                }))
            except RuntimeError:
                pass
```

在 `_write_results` 调用之后、return 之前添加：

```python
        try:
            asyncio.ensure_future(ws_manager.broadcast({
                "type": "npc_conversation_end",
                "conversation_id": conversation_id,
                "summary": summary,
            }))
        except RuntimeError:
            pass
```

- [ ] **步骤 2：验证导入无误**

运行：`python -c "from server.core.interaction_runner import InteractionRunner; print('OK')"`
预期：OK

- [ ] **步骤 3：运行现有测试确认无回归**

运行：`pytest tests/server/ -v`
预期：207 passed

- [ ] **步骤 4：Commit**

```bash
git add server/core/interaction_runner.py
git commit -m "feat: InteractionRunner 对话过程中逐条广播 WebSocket 消息（任务 1/4）"
```

---

## 任务 2：前端 conversationStore

**文件：**
- 创建：`client/src/stores/conversationStore.ts`

- [ ] **步骤 1：创建 store**

```typescript
// client/src/stores/conversationStore.ts
import { defineStore } from 'pinia'
import { ref } from 'vue'

export interface ConversationMessage {
  speakerId: string
  speakerName: string
  content: string
}

export interface ConversationBlock {
  id: string
  day: number
  hour: number
  location: string
  participants: string[]
  messages: ConversationMessage[]
  finished: boolean
  summary?: string
}

const MAX_CONVERSATIONS = 20

const LOCATION_NAMES: Record<string, string> = {
  home: '家',
  field: '田地',
  tavern: '酒馆',
  market: '市场',
  church: '教堂',
  forest: '森林',
}

export function getLocationName(loc: string): string {
  return LOCATION_NAMES[loc] || loc
}

const AVATAR_MAP: Record<string, string> = {
  farmer: '/img/48/farmer.png',
  bartender: '/img/48/bartender.png',
  sheriff: '/img/48/sheriff.png',
  beggar: '/img/48/beggar.png',
  painter: '/img/48/shopkeeper.png',
  fortune_teller: '/img/48/witch.png',
}

export function getAvatar(npcId: string): string {
  return AVATAR_MAP[npcId] || '/img/48/farmer.png'
}

export const useConversationStore = defineStore('conversation', () => {
  const conversations = ref<ConversationBlock[]>([])

  function handleMessage(msg: any): boolean {
    switch (msg.type) {
      case 'npc_conversation_start':
        _onStart(msg)
        return true
      case 'npc_conversation_message':
        _onMessage(msg)
        return true
      case 'npc_conversation_end':
        _onEnd(msg)
        return true
      default:
        return false
    }
  }

  function _onStart(msg: any) {
    const block: ConversationBlock = {
      id: msg.conversation_id,
      day: msg.day,
      hour: msg.hour,
      location: msg.location,
      participants: msg.participants,
      messages: [],
      finished: false,
    }
    conversations.value.unshift(block)
    if (conversations.value.length > MAX_CONVERSATIONS) {
      conversations.value.pop()
    }
  }

  function _onMessage(msg: any) {
    const block = conversations.value.find(c => c.id === msg.conversation_id)
    if (!block) return
    block.messages.push({
      speakerId: msg.speaker_id,
      speakerName: msg.speaker_name,
      content: msg.content,
    })
  }

  function _onEnd(msg: any) {
    const block = conversations.value.find(c => c.id === msg.conversation_id)
    if (!block) return
    block.finished = true
    block.summary = msg.summary
  }

  return { conversations, handleMessage }
})
```

- [ ] **步骤 2：验证 TypeScript 编译**

运行：`cd client && npx vue-tsc --noEmit 2>&1 | grep conversationStore`
预期：无输出（无类型错误）

- [ ] **步骤 3：Commit**

```bash
git add client/src/stores/conversationStore.ts
git commit -m "feat: conversationStore 管理实时 NPC 对话数据（任务 2/4）"
```

---

## 任务 3：VillageNewsPanel 组件

**文件：**
- 创建：`client/src/components/VillageNewsPanel.vue`

- [ ] **步骤 1：创建组件**

```vue
<template>
  <div class="village-news-panel">
    <div class="news-stream" ref="streamRef">
      <template v-if="conversations.length === 0">
        <div class="news-empty">暂无 NPC 对话，等待村民们开始交流...</div>
      </template>
      <template v-for="conv in conversations" :key="conv.id">
        <div class="conv-separator">
          <span class="conv-separator-line"></span>
          <span class="conv-separator-text">
            Day {{ conv.day }} {{ conv.hour }}:00 · {{ getLocationName(conv.location) }}
          </span>
          <span v-if="!conv.finished" class="conv-live-dot"></span>
          <span class="conv-separator-line"></span>
        </div>
        <div
          v-for="(msg, i) in conv.messages"
          :key="`${conv.id}-${i}`"
          class="conv-msg"
        >
          <div class="msg-avatar">
            <img :src="getAvatar(msg.speakerId)" :alt="msg.speakerName" />
          </div>
          <div class="msg-body">
            <span class="msg-name">{{ msg.speakerName }}</span>
            <span class="msg-text">"{{ msg.content }}"</span>
          </div>
        </div>
        <div v-if="conv.finished && conv.summary" class="conv-summary">
          {{ conv.summary }}
        </div>
      </template>
    </div>
    <div class="news-status">
      <span class="live-dot"></span> 实时收听中
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { storeToRefs } from 'pinia'
import { useConversationStore, getLocationName, getAvatar } from '../stores/conversationStore'

const store = useConversationStore()
const { conversations } = storeToRefs(store)
const streamRef = ref<HTMLElement | null>(null)

watch(conversations, async () => {
  await nextTick()
  if (streamRef.value) {
    streamRef.value.scrollTop = 0
  }
}, { deep: true })
</script>

<style scoped>
.village-news-panel {
  padding: var(--gap-md);
  display: flex;
  flex-direction: column;
  flex: 1;
}

.news-stream {
  flex: 1;
  overflow-y: auto;
  max-height: 400px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.news-empty {
  font-family: var(--font-pixel);
  font-size: 10px;
  color: var(--color-text-dim);
  text-align: center;
  padding: var(--gap-lg) var(--gap-md);
}

.conv-separator {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 12px 0 6px;
}

.conv-separator-line {
  flex: 1;
  height: 1px;
  background: var(--color-border);
}

.conv-separator-text {
  font-family: var(--font-pixel);
  font-size: 9px;
  color: var(--color-text-dim);
  white-space: nowrap;
}

.conv-live-dot {
  width: 6px;
  height: 6px;
  background: var(--color-health);
  border-radius: 50%;
  animation: pulse 1.5s ease-in-out infinite;
}

.conv-msg {
  display: flex;
  gap: 10px;
  padding: 6px 8px;
  background: var(--color-bg);
  border-left: 3px solid var(--color-border);
}

.conv-msg:hover {
  border-left-color: var(--color-accent);
}

.msg-avatar {
  width: 32px;
  height: 32px;
  background: var(--color-panel);
  border: 2px solid var(--color-border);
  flex-shrink: 0;
  overflow: hidden;
}

.msg-avatar img {
  width: 100%;
  height: 100%;
  object-fit: contain;
  image-rendering: pixelated;
}

.msg-body {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.msg-name {
  font-family: var(--font-pixel);
  font-size: 10px;
  color: var(--color-accent);
}

.msg-text {
  font-family: var(--font-body);
  font-size: 13px;
  color: var(--color-text);
  line-height: 1.5;
}

.conv-summary {
  font-family: var(--font-pixel);
  font-size: 9px;
  color: var(--color-text-dim);
  padding: 4px 8px;
  font-style: italic;
}

.news-status {
  margin-top: var(--gap-sm);
  padding-top: var(--gap-xs);
  border-top: 1px solid var(--color-border);
  font-family: var(--font-pixel);
  font-size: 10px;
  color: var(--color-text-dim);
  text-align: center;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
}

.live-dot {
  width: 6px;
  height: 6px;
  background: var(--color-health);
  display: inline-block;
  animation: pulse 1.5s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}
</style>
```

- [ ] **步骤 2：验证 TypeScript 编译**

运行：`cd client && npx vue-tsc --noEmit 2>&1 | grep VillageNews`
预期：无输出（无类型错误）

- [ ] **步骤 3：Commit**

```bash
git add client/src/components/VillageNewsPanel.vue
git commit -m "feat: VillageNewsPanel 村庄见闻面板组件（任务 3/4）"
```

---

## 任务 4：GamePage 集成 + 隐藏模块

**文件：**
- 修改：`client/src/pages/GamePage.vue`

- [ ] **步骤 1：替换 import 和组件引用**

在 `<script setup>` 中：
- 移除 `import TavernPanel from '../components/TavernPanel.vue'`
- 移除 `import ToolPanelV2 from '../components/ToolPanelV2.vue'`
- 移除 `import EavesdropPanel from '../components/EavesdropPanel.vue'`
- 添加 `import VillageNewsPanel from '../components/VillageNewsPanel.vue'`
- 添加 `import { useConversationStore } from '../stores/conversationStore'`

在 `const store = useGameStore()` 之后添加：
```typescript
const convStore = useConversationStore()
```

- [ ] **步骤 2：修改 centerTab 类型和 tab 名称**

将：
```typescript
const centerTab = ref<'chat' | 'tavern'>('chat')
```
改为：
```typescript
const centerTab = ref<'chat' | 'news'>('chat')
```

在模板中，将酒馆 tab 按钮：
```html
<button
  class="switch-tab"
  :class="{ 'switch-tab--active': centerTab === 'tavern' }"
  @click="centerTab = 'tavern'"
>🍺 酒馆</button>
```
改为：
```html
<button
  class="switch-tab"
  :class="{ 'switch-tab--active': centerTab === 'news' }"
  @click="centerTab = 'news'"
>👂 村庄见闻</button>
```

将：
```html
<TavernPanel v-show="centerTab === 'tavern'" />
```
改为：
```html
<VillageNewsPanel v-show="centerTab === 'news'" />
```

- [ ] **步骤 3：隐藏 ToolPanelV2 和 EavesdropPanel**

在模板中：
- 移除 `<ToolPanelV2 />`（整行删除）
- 移除 `<EavesdropPanel />`（整行删除）

- [ ] **步骤 4：扩展 WebSocket handler**

修改 `onMounted` 中的 connect 回调：

```typescript
onMounted(async () => {
  await Promise.all([store.fetchWorld(), store.fetchPlayer()])
  connect((msg) => {
    if (convStore.handleMessage(msg)) return
    if (msg.type === 'game_time_update' && store.world) {
      store.world.game_time = { day: msg.day, hour: msg.hour }
    }
  })
})
```

- [ ] **步骤 5：验证 TypeScript 编译**

运行：`cd client && npx vue-tsc --noEmit 2>&1 | grep -v GamePage.vue:95`
预期：无新增错误（GamePage.vue:95 是预先存在的 minute 类型问题）

- [ ] **步骤 6：Commit**

```bash
git add client/src/pages/GamePage.vue
git commit -m "feat: GamePage 集成村庄见闻面板，隐藏工具和偷听模块（任务 4/4）"
```
