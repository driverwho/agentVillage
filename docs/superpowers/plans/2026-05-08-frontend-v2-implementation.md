# 前端 v2 完全体 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 将 Agent Village 前端重构为三栏布局完全体，包含暖褐金配色、5 个新面板、6 个 NPC（含待解锁）、mock 数据驱动、未实现功能可点击+动画+toast 提示。

**架构：** Vue 3 + Pinia + TypeScript，逐组件构建。现有 gameStore 保持真实 API 调用不变，新增 mockStore 驱动新面板。CSS 变量全局替换为暖褐金提亮版，按钮从渐变阴影改为纯色像素边框。

**技术栈：** Vue 3.4, Pinia 2.1, TypeScript 5.3, Vite 5, axios 1.6

---

### 任务 1：CSS 变量与全局样式替换

**文件：**
- 修改：`client/src/styles/variables.css`
- 修改：`client/src/styles/global.css`

- [ ] **步骤 1：替换 variables.css 为暖褐金提亮版配色**

```css
:root {
  /* ── Background ── */
  --color-bg: #2c1f16;
  --color-panel: #3d2d20;
  --color-input: #33251a;
  --color-hover: #4a3828;

  /* ── Border ── */
  --color-border: #7a5540;
  --color-border-light: #a08060;

  /* ── Accent ── */
  --color-accent: #daa520;
  --color-accent-light: #e8c44a;

  /* ── Text ── */
  --color-text: #f0dfc4;
  --color-text-dim: #c4a882;

  /* ── Status ── */
  --color-health: #7fb330;
  --color-hunger: #e8a64e;
  --color-fatigue: #cc4444;
  --color-info: #6b9ec4;

  /* ── Typography ── */
  --font-pixel: 'Press Start 2P', 'Courier New', monospace;
  --font-body: 'Microsoft YaHei', 'SimHei', sans-serif;
  --font-size-xs: 10px;
  --font-size-sm: 12px;
  --font-size-base: 14px;
  --font-size-lg: 18px;

  /* ── Spacing ── */
  --gap-xs: 4px;
  --gap-sm: 8px;
  --gap-md: 16px;
  --gap-lg: 24px;
}
```

- [ ] **步骤 2：更新 global.css 按钮样式 — 删除渐变阴影，改为纯色像素边框**

将现有的 `button { ... }` 规则替换为：

```css
button {
  font-family: var(--font-pixel);
  font-size: var(--font-size-xs);
  color: var(--color-text);
  background: var(--color-bg);
  border: 2px solid var(--color-border);
  padding: 6px 12px;
  cursor: pointer;
  text-transform: uppercase;
  letter-spacing: 1px;
  transition: border-color 0.15s, color 0.15s;
}

button:hover {
  border-color: var(--color-accent);
  color: var(--color-accent-light);
}

button:active {
  transform: translateY(2px);
}

button:disabled {
  opacity: 0.4;
  border-color: var(--color-text-dim);
  cursor: not-allowed;
  filter: grayscale(50%);
}

button:disabled:hover {
  color: var(--color-text);
  border-color: var(--color-text-dim);
}

button:disabled:active {
  transform: none;
}
```

- [ ] **步骤 3：移除 global.css 中的 `.pixel-border` 类和相关旧样式**

删除以下规则（不再使用双层阴影边框）：
```css
/* 删除 */
.pixel-border {
  box-shadow: var(--pixel-border);
  border: 1px solid var(--color-border-light);
}
```

从 variables.css 删除：
```css
/* 删除 */
--pixel-border: 0 0 0 2px var(--color-border-dark), 0 0 0 3px var(--color-border-light);
--pixel-border-inset: ...;
```

- [ ] **步骤 4：更新 global.css input 样式以匹配新配色**

```css
input, textarea {
  font-family: var(--font-body);
  font-size: var(--font-size-base);
  color: var(--color-text);
  background: var(--color-input);
  border: 2px solid var(--color-border);
  padding: 6px 10px;
  outline: none;
}

input:focus, textarea:focus {
  border-color: var(--color-accent);
}
```

- [ ] **步骤 5：验证 CSS 构建**

运行：`cd client && npx vite build`
预期：构建成功，无 CSS 相关错误。

- [ ] **步骤 6：Commit**

```bash
git add client/src/styles/variables.css client/src/styles/global.css
git commit -m "style: 暖褐金提亮配色 + 按钮统一为纯色像素边框风格

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 2：Toast 提示工具

**文件：**
- 创建：`client/src/services/toast.ts`

- [ ] **步骤 1：创建 toast 工具模块**

```typescript
// client/src/services/toast.ts
import { ref } from 'vue'

export interface Toast {
  id: number
  message: string
  visible: boolean
}

let nextId = 0
export const toasts = ref<Toast[]>([])

export function showToast(message: string, duration = 2500): void {
  const id = nextId++
  const toast: Toast = { id, message, visible: true }
  toasts.value.push(toast)
  setTimeout(() => {
    const t = toasts.value.find(t => t.id === id)
    if (t) t.visible = false
    setTimeout(() => {
      toasts.value = toasts.value.filter(t => t.id !== id)
    }, 300)
  }, duration)
}
```

- [ ] **步骤 2：验证 TypeScript 编译**

运行：`cd client && npx vue-tsc --noEmit src/services/toast.ts`
预期：无类型错误。

- [ ] **步骤 3：Commit**

```bash
git add client/src/services/toast.ts
git commit -m "feat: add toast utility for coming-soon notifications

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 3：更新类型定义

**文件：**
- 修改：`client/src/types/index.ts`

- [ ] **步骤 1：扩展 types/index.ts 以支持新面板数据结构**

```typescript
// client/src/types/index.ts

export interface GameTime {
  day: number
  hour: number
  minute: number
}

export interface NPCState {
  health: number
  hunger: number
  fatigue: number
  mood: number
}

// 新增：NPC 状态标签
export type NPCStatusType = 'working' | 'resting' | 'socializing' | 'sleeping' | 'abnormal' | 'away'

// 新增：NPC 完整信息
export interface NPCInfo {
  id: string
  name: string
  role: string
  avatar: string          // emoji 占位，后续替换为像素艺术
  unlocked: boolean
  state: NPCState
  status: NPCStatusType
  statusLabel: string
  relationship: number    // 好感度 0-100
}

export interface WorldState {
  game_time: GameTime
  is_paused: boolean
  npcs: Record<string, { state: NPCState }>
}

export interface PlayerState {
  name: string
  health: number
  hunger: number
  fatigue: number
  location: string
  gold: number
  relationships: Record<string, number>
  reputation: number
  farm_count: number
}

export interface ChatResponse {
  reply: string
  options: string[]
}

// 新增：工具定义
export interface ToolDef {
  id: string
  name: string
  icon: string
  unlocked: boolean
  trustRequired: number
  npcId: string
}

// 新增：笔记簿条目
export interface TimelineEntry {
  day: number
  text: string
  source: 'witnessed' | 'heard' | 'inferred'
}

export interface NPCObservation {
  npcId: string
  entries: { day: number; text: string }[]
}

export interface PlayerAction {
  day: number
  text: string
}

// 新增：随机事件
export interface RandomEvent {
  id: string
  name: string
  description: string
  icon: string
}
```

- [ ] **步骤 2：验证编译**

运行：`cd client && npx vue-tsc --noEmit`
预期：无类型错误。

- [ ] **步骤 3：Commit**

```bash
git add client/src/types/index.ts
git commit -m "feat: 扩展类型定义 — NPCInfo, ToolDef, 笔记簿, 随机事件

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 4：Mock Store

**文件：**
- 创建：`client/src/stores/mockStore.ts`

- [ ] **步骤 1：创建 mockStore 包含 NPC 列表、工具、事件、笔记簿、偷听数据**

```typescript
// client/src/stores/mockStore.ts
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { NPCInfo, ToolDef, RandomEvent, TimelineEntry, NPCObservation, PlayerAction, NPCStatusType } from '../types'
import { showToast } from '../services/toast'

// 根据游戏时间判定 NPC 状态
function deriveStatus(npcId: string, hour: number): { status: NPCStatusType; label: string } {
  if (hour >= 22 || hour < 6) return { status: 'sleeping', label: '😴 睡眠中' }
  if (hour >= 18 && hour < 22 && npcId === 'bartender') return { status: 'socializing', label: '🍺 酒馆营业' }
  if (hour >= 18 && hour < 22) return { status: 'socializing', label: '🍺 酒馆社交' }
  if (hour >= 12 && hour < 13) return { status: 'resting', label: '☕ 休息中' }
  return { status: 'working', label: getWorkLabel(npcId) }
}

function getWorkLabel(npcId: string): string {
  const labels: Record<string, string> = {
    farmer: '🌾 耕作中',
    bartender: '🧹 整理中',
    sheriff: '🛡 巡逻中',
    fortune_teller: '🔮 占卜中',
    beggar: '🚶 流浪中',
    shopkeeper: '📦 看店中',
  }
  return labels[npcId] || '工作中'
}

export const useMockStore = defineStore('mock', () => {
  const currentHour = ref(14)

  // ── NPC 列表 ──
  const npcs = ref<NPCInfo[]>([
    {
      id: 'farmer', name: '农夫·托德', role: '村庄农夫', avatar: '🧑‍🌾',
      unlocked: true, state: { health: 80, hunger: 60, fatigue: 30, mood: 70 },
      status: 'working', statusLabel: '🌾 耕作中', relationship: 35,
    },
    {
      id: 'bartender', name: '酒保·盖斯', role: '酒馆老板', avatar: '🍺',
      unlocked: true, state: { health: 90, hunger: 50, fatigue: 20, mood: 60 },
      status: 'working', statusLabel: '🧹 整理中', relationship: 20,
    },
    {
      id: 'sheriff', name: '警长·巴顿', role: '治安官', avatar: '⭐',
      unlocked: false, state: { health: 100, hunger: 70, fatigue: 10, mood: 80 },
      status: 'working', statusLabel: '🔒 解锁条件未知', relationship: 0,
    },
    {
      id: 'fortune_teller', name: '占卜师·丽娜', role: '神秘占卜师', avatar: '🔮',
      unlocked: false, state: { health: 70, hunger: 40, fatigue: 50, mood: 90 },
      status: 'working', statusLabel: '🔒 解锁条件未知', relationship: 0,
    },
    {
      id: 'beggar', name: '流浪者·威利', role: '流浪乞丐', avatar: '🪙',
      unlocked: false, state: { health: 40, hunger: 10, fatigue: 60, mood: 30 },
      status: 'away', statusLabel: '🔒 解锁条件未知', relationship: 0,
    },
    {
      id: 'shopkeeper', name: '杂货商·洛克', role: '杂货店老板', avatar: '📦',
      unlocked: false, state: { health: 85, hunger: 60, fatigue: 15, mood: 75 },
      status: 'working', statusLabel: '🔒 解锁条件未知', relationship: 0,
    },
  ])

  const unlockedNPCs = computed(() => npcs.value.filter(n => n.unlocked))
  const lockedNPCs = computed(() => npcs.value.filter(n => !n.unlocked))

  function updateNPCStatus(hour: number) {
    currentHour.value = hour
    npcs.value.forEach(npc => {
      if (!npc.unlocked) return
      const s = deriveStatus(npc.id, hour)
      npc.status = s.status
      npc.statusLabel = s.label
    })
  }

  // ── 工具列表 ──
  const tools = ref<ToolDef[]>([
    { id: 'farming', name: '耕作', icon: '🌾', unlocked: true, trustRequired: 0, npcId: 'farmer' },
    { id: 'trading', name: '交易', icon: '🗡', unlocked: false, trustRequired: 30, npcId: 'bartender' },
    { id: 'patrol', name: '巡逻', icon: '🛡', unlocked: false, trustRequired: 60, npcId: 'sheriff' },
    { id: 'divination', name: '占卜', icon: '🔮', unlocked: false, trustRequired: 90, npcId: 'fortune_teller' },
    { id: 'brewing', name: '酿酒', icon: '🍺', unlocked: false, trustRequired: 40, npcId: 'bartender' },
    { id: 'painting', name: '作画', icon: '🎨', unlocked: false, trustRequired: 50, npcId: 'shopkeeper' },
  ])

  // ── 事件系统 ──
  const dailyEventQuota = ref(1)
  const randomEvents: RandomEvent[] = [
    { id: 'hail', name: '冰雹', description: '突降冰雹，作物受损', icon: '🌨️' },
    { id: 'theft_tavern', name: '盗窃案（酒馆）', description: '酒馆昨夜遭窃', icon: '🦹' },
    { id: 'harvest', name: '丰收日', description: '今日耕作产出翻倍', icon: '🌾' },
    { id: 'merchant', name: '流浪商人', description: '一位神秘商人路过村庄', icon: '🧳' },
    { id: 'eclipse', name: '月食', description: '占卜之力增强', icon: '🌑' },
    { id: 'brawl', name: '酒馆斗殴', description: '酒馆爆发冲突', icon: '👊' },
  ]
  const currentEvent = ref<RandomEvent | null>(null)

  // ── 笔记簿 ──
  const timeline = ref<TimelineEntry[]>([
    { day: 1, text: '你来到了这个村庄。酒馆里，酒保·盖斯和一个陌生人做了交易。', source: 'witnessed' },
    { day: 2, text: '农夫·托德在酒馆和酒保·盖斯吵架，摔了一个杯子。（原因不明）', source: 'witnessed' },
    { day: 2, text: '听说流浪者·威利在村口捡到了一枚金币。', source: 'heard' },
  ])

  const npcObservations = ref<NPCObservation[]>([
    { npcId: 'bartender', entries: [{ day: 1, text: '和流浪商人交易了东西，神神秘秘的。' }, { day: 2, text: '和农夫吵架，心情不太好。' }] },
    { npcId: 'farmer', entries: [{ day: 2, text: '在酒馆发火，似乎对酒保涨价很不满。' }] },
  ])

  const playerActions = ref<PlayerAction[]>([
    { day: 1, text: '和酒保·盖斯闲聊，问起了村里的情况。' },
    { day: 2, text: '帮农夫·托德耕了一上午的地。' },
  ])

  const notebookTab = ref<'timeline' | 'npc' | 'actions'>('timeline')

  // ── 偷听 ──
  const eavesdropQuota = ref(1)

  // ── 对话选项（mock 预设选项链） ──
  const dialogueOptionSets: Record<string, string[][]> = {
    farmer: [
      ['最近村里有什么事吗？', '庄稼长得怎么样了？', '听说你和酒保闹矛盾了？'],
      ['需要我帮忙耕作吗？', '你为什么讨厌酒保？', '聊聊天气吧。'],
      ['关于警长，你知道些什么？', '我先走了。', '下次再来帮你。'],
    ],
    bartender: [
      ['来一杯你的招牌酒。', '最近生意怎么样？', '那天和你交易的是谁？'],
      ['听说你和农夫吵架了？', '有什么特别的情报吗？', '我随便看看。'],
      ['酒馆来过什么有趣的客人吗？', '给我讲讲这个村子。', '再见。'],
    ],
  }
  const optionIndex = ref<Record<string, number>>({ farmer: 0, bartender: 0 })

  function getOptions(npcId: string): string[] {
    const sets = dialogueOptionSets[npcId]
    if (!sets) return ['聊聊吧。', '我先走了。']
    const idx = optionIndex.value[npcId] || 0
    return sets[idx] || sets[0]
  }

  function advanceOptions(npcId: string) {
    const sets = dialogueOptionSets[npcId]
    if (!sets) return
    const idx = (optionIndex.value[npcId] || 0) + 1
    optionIndex.value[npcId] = idx % sets.length
  }

  // ── Mock 方法（触发 toast） ──
  function drawRandomEvent(): RandomEvent {
    if (dailyEventQuota.value <= 0) {
      showToast('今日事件次数已用完')
      return null!
    }
    dailyEventQuota.value--
    const event = randomEvents[Math.floor(Math.random() * randomEvents.length)]
    currentEvent.value = event
    showToast(`🎴 抽到了「${event.name}」！${event.description}（功能开发中，敬请期待）`)
    return event
  }

  function submitCustomEvent(text: string) {
    if (dailyEventQuota.value <= 0) {
      showToast('今日事件次数已用完')
      return
    }
    if (!text.trim()) {
      showToast('请输入事件描述')
      return
    }
    dailyEventQuota.value--
    showToast(`📝 自定义事件「${text}」已提交！（功能开发中，敬请期待）`)
  }

  function rollDice(): { result: number; success: boolean } {
    const result = Math.floor(Math.random() * 20) + 1
    const success = result >= 12
    showToast(`🎲 掷出了 ${result} 点！${success ? '成功！' : '失败...'}（功能开发中，敬请期待）`)
    return { result, success }
  }

  function doEavesdrop(targetIds: string[]) {
    if (eavesdropQuota.value <= 0) {
      showToast('今日偷听次数已用完')
      return
    }
    eavesdropQuota.value--
    const names = targetIds.map(id => npcs.value.find(n => n.id === id)?.name || id).join(' 和 ')
    showToast(`👂 正在偷听 ${names} 的对话...（功能开发中，敬请期待）`)
  }

  function useLockedTool(tool: ToolDef) {
    showToast(`🛠 「${tool.name}」需要信任等级 ${tool.trustRequired}（功能开发中，敬请期待）`)
  }

  function resetDailyQuotas() {
    dailyEventQuota.value = 1
    eavesdropQuota.value = 1
  }

  return {
    npcs, unlockedNPCs, lockedNPCs,
    tools,
    dailyEventQuota, randomEvents, currentEvent,
    timeline, npcObservations, playerActions, notebookTab,
    eavesdropQuota,
    dialogueOptionSets, optionIndex,
    updateNPCStatus,
    getOptions, advanceOptions,
    drawRandomEvent, submitCustomEvent, rollDice,
    doEavesdrop, useLockedTool,
    resetDailyQuotas,
  }
})
```

- [ ] **步骤 2：验证 TypeScript 编译**

运行：`cd client && npx vue-tsc --noEmit`
预期：无类型错误。

- [ ] **步骤 3：Commit**

```bash
git add client/src/stores/mockStore.ts
git commit -m "feat: add mockStore — NPC列表/工具/事件/笔记簿/偷听 mock 数据

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 5：App.vue 三栏布局重构

**文件：**
- 修改：`client/src/App.vue`

- [ ] **步骤 1：重写 App.vue 为三栏 Grid 布局，集成所有面板**

```vue
<template>
  <div class="game-container">
    <header class="game-header">
      <h1 class="game-title">Agent Village</h1>
      <TimeControl />
    </header>

    <aside class="col-left">
      <StatusPanel />
      <NPCPanel @select="store.selectNPC" />
    </aside>

    <main class="col-center">
      <ChatPanel />
      <ToolPanelV2 />
    </main>

    <aside class="col-right">
      <EventPanel />
      <EavesdropPanel />
      <NotebookPanel />
    </aside>

    <!-- Toast overlay -->
    <div class="toast-container" v-if="toasts.length">
      <div
        v-for="t in toasts"
        :key="t.id"
        class="toast-item"
        :class="{ 'toast-leaving': !t.visible }"
      >
        {{ t.message }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import TimeControl from './components/TimeControl.vue'
import StatusPanel from './components/StatusPanel.vue'
import NPCPanel from './components/NPCPanel.vue'
import ChatPanel from './components/ChatPanel.vue'
import ToolPanelV2 from './components/ToolPanelV2.vue'
import EventPanel from './components/EventPanel.vue'
import EavesdropPanel from './components/EavesdropPanel.vue'
import NotebookPanel from './components/NotebookPanel.vue'
import { useGameStore } from './stores/gameStore'
import { toasts } from './services/toast'

const store = useGameStore()

onMounted(async () => {
  await Promise.all([store.fetchWorld(), store.fetchPlayer()])
})
</script>

<style>
.game-container {
  max-width: 1400px;
  min-height: 100vh;
  margin: 0 auto;
  padding: var(--gap-md);
  display: grid;
  grid-template-areas:
    "header header header"
    "left   center right";
  grid-template-columns: 260px 1fr 280px;
  grid-template-rows: auto 1fr;
  gap: var(--gap-md);
}

.game-header {
  grid-area: header;
  background: var(--color-panel);
  border: 2px solid var(--color-border);
  padding: var(--gap-md);
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: var(--gap-sm);
}

.game-title {
  font-size: var(--font-size-lg);
  margin: 0;
  white-space: nowrap;
}

.col-left {
  grid-area: left;
  display: flex;
  flex-direction: column;
  gap: var(--gap-md);
  overflow-y: auto;
  max-height: calc(100vh - 80px);
}

.col-center {
  grid-area: center;
  display: flex;
  flex-direction: column;
  gap: var(--gap-md);
  min-width: 400px;
  overflow-y: auto;
  max-height: calc(100vh - 80px);
}

.col-right {
  grid-area: right;
  display: flex;
  flex-direction: column;
  gap: var(--gap-md);
  overflow-y: auto;
  max-height: calc(100vh - 80px);
}

/* Toast overlay */
.toast-container {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 10000;
  display: flex;
  flex-direction: column;
  gap: 8px;
  pointer-events: none;
}

.toast-item {
  font-family: var(--font-pixel);
  font-size: var(--font-size-xs);
  color: var(--color-bg);
  background: var(--color-accent);
  border: 2px solid var(--color-accent-light);
  padding: 8px 16px;
  text-align: center;
  animation: toast-in 0.3s ease-out;
  pointer-events: auto;
}

.toast-leaving {
  opacity: 0;
  transition: opacity 0.3s ease-out;
}

@keyframes toast-in {
  from { transform: translateY(-20px); opacity: 0; }
  to { transform: translateY(0); opacity: 1; }
}

/* Responsive */
@media (max-width: 1000px) {
  .game-container {
    grid-template-areas:
      "header header"
      "left   center"
      "right  right";
    grid-template-columns: 260px 1fr;
  }
  .col-right {
    flex-direction: row;
    max-height: none;
  }
}

@media (max-width: 700px) {
  .game-container {
    grid-template-areas:
      "header"
      "left"
      "center"
      "right";
    grid-template-columns: 1fr;
  }
  .col-left, .col-center, .col-right {
    max-height: none;
  }
}
</style>
```

- [ ] **步骤 2：验证编译（此时新组件尚未创建，接受导入错误属正常）**

运行：`cd client && npx vite build 2>&1 | head -30`
预期：构建报错 "Cannot find module"（新组件未创建，后续任务解决）。

- [ ] **步骤 3：Commit**

```bash
git add client/src/App.vue
git commit -m "refactor: App.vue 三栏 Grid 布局 + toast 容器

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 6：NPCPanel 重构

**文件：**
- 修改：`client/src/components/NPCPanel.vue`

- [ ] **步骤 1：重写 NPCPanel — 头像+状态标签+解锁列表**

```vue
<template>
  <div class="npc-panel">
    <h3>村庄居民</h3>

    <!-- 已解锁 NPC -->
    <div
      v-for="npc in mock.unlockedNPCs"
      :key="npc.id"
      class="npc-card"
      :class="{ 'npc-card--active': npc.id === currentNPC }"
      @click="$emit('select', npc.id)"
    >
      <div class="npc-avatar">{{ npc.avatar }}</div>
      <div class="npc-body">
        <div class="npc-header">
          <span class="npc-name">{{ npc.name }}</span>
          <span class="npc-status" :style="{ color: statusColor(npc.status) }">
            {{ npc.statusLabel }}
          </span>
        </div>
        <div class="npc-stats">
          <span class="npc-stat">♥{{ npc.state.health }}</span>
          <span class="npc-stat">🍖{{ npc.state.hunger }}</span>
          <span class="npc-stat">💤{{ npc.state.fatigue }}</span>
          <span class="npc-stat">☻{{ npc.state.mood }}</span>
        </div>
        <div class="npc-rel" v-if="npc.relationship > 0">
          <span class="rel-label">好感</span>
          <div class="rel-bar">
            <div class="rel-fill" :style="{ width: npc.relationship + '%' }"></div>
          </div>
          <span class="rel-val">{{ npc.relationship }}</span>
        </div>
      </div>
    </div>

    <!-- 分隔线 -->
    <div class="locked-divider">🔒 待解锁</div>

    <!-- 待解锁 NPC -->
    <div
      v-for="npc in mock.lockedNPCs"
      :key="npc.id"
      class="npc-card npc-card--locked"
    >
      <div class="npc-avatar npc-avatar--locked">{{ npc.avatar }}</div>
      <div class="npc-body">
        <div class="npc-header">
          <span class="npc-name locked-name">{{ npc.name }}</span>
        </div>
        <div class="npc-status locked-status">🔒 解锁条件未知</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useGameStore } from '../stores/gameStore'
import { useMockStore } from '../stores/mockStore'
import { storeToRefs } from 'pinia'
import type { NPCStatusType } from '../types'

const store = useGameStore()
const mock = useMockStore()
const { currentNPC } = storeToRefs(store)

defineEmits<{ select: [npcId: string] }>()

function statusColor(status: NPCStatusType): string {
  const map: Record<NPCStatusType, string> = {
    working: 'var(--color-health)',
    resting: 'var(--color-hunger)',
    socializing: 'var(--color-info)',
    sleeping: 'var(--color-text-dim)',
    abnormal: 'var(--color-fatigue)',
    away: 'var(--color-info)',
  }
  return map[status]
}
</script>

<style scoped>
.npc-panel {
  background: var(--color-panel);
  border: 2px solid var(--color-border);
  padding: var(--gap-md);
}

.npc-panel h3 {
  margin-bottom: var(--gap-sm);
  font-size: var(--font-size-sm);
}

.npc-card {
  display: flex;
  gap: 10px;
  padding: var(--gap-sm) var(--gap-md);
  margin-bottom: var(--gap-sm);
  background: var(--color-bg);
  border: 2px solid var(--color-border);
  cursor: pointer;
  transition: border-color 0.15s;
  align-items: center;
}

.npc-card:hover {
  border-color: var(--color-border-light);
}

.npc-card--active {
  border-color: var(--color-accent);
}

.npc-card--locked {
  opacity: 0.55;
  border-style: dashed;
  cursor: default;
}

.npc-card--locked:hover {
  border-color: var(--color-border);
}

.npc-avatar {
  width: 40px;
  height: 40px;
  background: var(--color-panel);
  border: 2px solid var(--color-border);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
  flex-shrink: 0;
  image-rendering: pixelated;
}

.npc-avatar--locked {
  filter: grayscale(70%);
}

.npc-body {
  flex: 1;
  min-width: 0;
}

.npc-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 2px;
}

.npc-name {
  font-family: var(--font-pixel);
  font-size: var(--font-size-xs);
  color: var(--color-accent);
  white-space: nowrap;
}

.locked-name {
  color: var(--color-text-dim);
}

.npc-status {
  font-family: var(--font-pixel);
  font-size: 7px;
  white-space: nowrap;
}

.locked-status {
  font-size: 7px;
  color: var(--color-text-dim);
}

.npc-stats {
  display: flex;
  gap: var(--gap-sm);
  flex-wrap: wrap;
  margin-top: 2px;
}

.npc-stat {
  font-family: var(--font-pixel);
  font-size: var(--font-size-xs);
  color: var(--color-text-dim);
}

.npc-rel {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 4px;
}

.rel-label {
  font-family: var(--font-pixel);
  font-size: 7px;
  color: var(--color-text-dim);
  flex-shrink: 0;
}

.rel-bar {
  flex: 1;
  max-width: 80px;
  height: 6px;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
}

.rel-fill {
  height: 100%;
  background: var(--color-health);
  transition: width 0.3s step-end;
}

.rel-val {
  font-family: var(--font-pixel);
  font-size: 7px;
  color: var(--color-text-dim);
  width: 20px;
  text-align: right;
}

.locked-divider {
  font-family: var(--font-pixel);
  font-size: 8px;
  color: var(--color-text-dim);
  margin: var(--gap-sm) 0;
  padding-bottom: 2px;
  border-bottom: 1px solid var(--color-border);
}
</style>
```

- [ ] **步骤 2：Commit**

```bash
git add client/src/components/NPCPanel.vue
git commit -m "refactor: NPCPanel — 像素头像+状态标签+解锁列表+好感度条

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 7：StatusPanel 样式适配

**文件：**
- 修改：`client/src/components/StatusPanel.vue`

- [ ] **步骤 1：更新 StatusPanel 样式以匹配新配色变量**

将 `style scoped` 中的 `.status-panel` 边框从 `pixel-border` 改为新风格：

```vue
<style scoped>
.status-panel {
  background: var(--color-panel);
  border: 2px solid var(--color-border);
  padding: var(--gap-md);
}
/* 其余样式保持不变，颜色变量自动适配 */
</style>
```

同时更新 `.stat-bar` 背景色：

```css
.stat-bar {
  flex: 1;
  height: 10px;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
}
```

- [ ] **步骤 2：Commit**

```bash
git add client/src/components/StatusPanel.vue
git commit -m "refactor: StatusPanel 适配暖褐金配色+像素边框

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 8：ChatPanel 重构

**文件：**
- 修改：`client/src/components/ChatPanel.vue`

- [ ] **步骤 1：重写 ChatPanel — 居中分散选项按钮+像素风格**

```vue
<template>
  <div class="chat-panel">
    <h3>对话 — {{ npcName }}</h3>

    <div class="messages" ref="msgContainer">
      <div
        v-for="(msg, i) in messages"
        :key="i"
        class="msg-bubble"
        :class="msg.speaker === 'player' ? 'msg-player' : 'msg-npc'"
      >
        <div class="msg-speaker">{{ msg.speaker === 'player' ? '你' : npcName }}</div>
        <div class="msg-content">{{ msg.content }}</div>
      </div>
      <div v-if="messages.length === 0" class="msg-empty">
        选择左侧居民开始对话...
      </div>
    </div>

    <!-- 居中分散的选项按钮 -->
    <div class="options" v-if="currentOptions.length">
      <button
        v-for="(opt, i) in currentOptions"
        :key="i"
        class="opt-btn"
        @click="selectOption(opt)"
      >
        {{ opt }}
      </button>
    </div>

    <div class="input-area">
      <input
        v-model="inputText"
        @keyup.enter="send"
        placeholder="或自由输入..."
      />
      <button @click="send">发送</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick, watch } from 'vue'
import { useGameStore } from '../stores/gameStore'
import { useMockStore } from '../stores/mockStore'
import { storeToRefs } from 'pinia'

const store = useGameStore()
const mock = useMockStore()
const { messages, currentNPC } = storeToRefs(store)
const inputText = ref('')
const msgContainer = ref<HTMLElement>()

const npcName = computed(() => {
  const npc = mock.npcs.find(n => n.id === currentNPC.value)
  return npc?.name || 'NPC'
})

const currentOptions = computed(() => mock.getOptions(currentNPC.value))

watch(messages, async () => {
  await nextTick()
  if (msgContainer.value) {
    msgContainer.value.scrollTop = msgContainer.value.scrollHeight
  }
}, { deep: true })

async function send() {
  const text = inputText.value.trim()
  if (!text) return
  inputText.value = ''
  const data = await store.sendMessage(currentNPC.value, text)
  // 后端返回的 options 有就用，没有就用 mock
  if (data.options && data.options.length) {
    // 后端返回了选项，直接展示
    mock.advanceOptions(currentNPC.value)
  } else {
    mock.advanceOptions(currentNPC.value)
  }
}

function selectOption(opt: string) {
  sendWithText(opt)
}

async function sendWithText(text: string) {
  const data = await store.sendMessage(currentNPC.value, text)
  mock.advanceOptions(currentNPC.value)
}
</script>

<style scoped>
.chat-panel {
  background: var(--color-panel);
  border: 2px solid var(--color-border);
  padding: var(--gap-md);
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 300px;
}

.chat-panel h3 {
  margin-bottom: var(--gap-sm);
  font-size: var(--font-size-sm);
}

.messages {
  flex: 1;
  min-height: 200px;
  max-height: 400px;
  overflow-y: auto;
  background: var(--color-bg);
  border: 1px solid var(--color-border);
  padding: var(--gap-sm);
  margin-bottom: var(--gap-sm);
}

.msg-empty {
  color: var(--color-text-dim);
  text-align: center;
  padding-top: 80px;
  font-family: var(--font-pixel);
  font-size: var(--font-size-xs);
}

.msg-bubble {
  margin-bottom: var(--gap-sm);
  padding: var(--gap-xs) var(--gap-sm);
  background: var(--color-panel);
  border: 2px solid var(--color-border);
}

.msg-player {
  margin-left: 20%;
  border-left: 3px solid var(--color-accent);
}

.msg-npc {
  margin-right: 20%;
  border-left: 3px solid var(--color-info);
}

.msg-speaker {
  font-family: var(--font-pixel);
  font-size: var(--font-size-xs);
  color: var(--color-accent);
  margin-bottom: 2px;
}

.msg-content {
  font-size: var(--font-size-base);
  line-height: 1.6;
}

.options {
  display: flex;
  justify-content: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: var(--gap-sm);
}

.opt-btn {
  font-size: 9px;
  padding: 6px 12px;
  background: var(--color-bg);
  border: 2px solid var(--color-border);
  color: var(--color-text);
  font-family: var(--font-pixel);
}

.opt-btn:hover {
  border-color: var(--color-accent);
  color: var(--color-accent-light);
}

.input-area {
  display: flex;
  gap: var(--gap-sm);
}

.input-area input {
  flex: 1;
}
</style>
```

- [ ] **步骤 2：Commit**

```bash
git add client/src/components/ChatPanel.vue
git commit -m "refactor: ChatPanel — 居中分散选项按钮+像素边框风格+mock选项链

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 9：ToolPanelV2 新组件

**文件：**
- 创建：`client/src/components/ToolPanelV2.vue`
- 删除：`client/src/components/ToolPanel.vue`

- [ ] **步骤 1：创建 ToolPanelV2 — 多工具+信任解锁**

```vue
<template>
  <div class="tool-panel">
    <h3>可用工具</h3>
    <div class="tool-grid">
      <button
        v-for="tool in mock.tools"
        :key="tool.id"
        class="tool-btn"
        :class="{ 'tool-locked': !tool.unlocked }"
        :disabled="!tool.unlocked && tool.trustRequired > 0"
        @click="handleToolClick(tool)"
      >
        <span class="tool-icon">{{ tool.icon }}</span>
        <span class="tool-name">{{ tool.name }}</span>
        <span class="tool-lock" v-if="!tool.unlocked">🔒</span>
      </button>
    </div>
    <p v-if="toolMessage" class="tool-msg" :class="{ 'tool-err': isError }">
      {{ toolMessage }}
    </p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useGameStore } from '../stores/gameStore'
import { useMockStore } from '../stores/mockStore'
import type { ToolDef } from '../types'

const store = useGameStore()
const mock = useMockStore()
const toolMessage = ref('')
const isError = ref(false)
const farmingInProgress = ref(false)

async function handleToolClick(tool: ToolDef) {
  if (!tool.unlocked) {
    mock.useLockedTool(tool)
    return
  }

  if (tool.id === 'farming') {
    farmingInProgress.value = true
    toolMessage.value = ''
    isError.value = false
    try {
      const result = await store.useFarmingTool()
      toolMessage.value = result.message || '耕作完成！'
    } catch (e: any) {
      toolMessage.value = e.response?.data?.detail || '耕作失败'
      isError.value = true
    }
    farmingInProgress.value = false
  }
}
</script>

<style scoped>
.tool-panel {
  background: var(--color-panel);
  border: 2px solid var(--color-border);
  padding: var(--gap-md);
}

.tool-panel h3 {
  margin-bottom: var(--gap-sm);
  font-size: var(--font-size-sm);
}

.tool-grid {
  display: flex;
  gap: var(--gap-sm);
  flex-wrap: wrap;
}

.tool-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  font-size: var(--font-size-xs);
}

.tool-locked {
  opacity: 0.4;
}

.tool-icon {
  font-size: 14px;
}

.tool-name {
  font-family: var(--font-pixel);
}

.tool-lock {
  font-size: 10px;
  opacity: 0.6;
}

.tool-msg {
  margin-top: var(--gap-sm);
  font-family: var(--font-pixel);
  font-size: var(--font-size-xs);
  color: var(--color-health);
}

.tool-err {
  color: var(--color-fatigue);
}
</style>
```

- [ ] **步骤 2：删除旧 ToolPanel.vue**

```bash
rm client/src/components/ToolPanel.vue
```

- [ ] **步骤 3：Commit**

```bash
git add client/src/components/ToolPanelV2.vue
git rm client/src/components/ToolPanel.vue
git commit -m "refactor: ToolPanelV2 — 多工具列表+信任等级解锁+锁定提示

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 10：DiceRoller 子组件

**文件：**
- 创建：`client/src/components/DiceRoller.vue`

- [ ] **步骤 1：创建 DiceRoller — D20 骰子动画**

```vue
<template>
  <div class="dice-roller">
    <div class="dice-display" :class="{ 'dice-rolling': rolling }">
      <span class="dice-number">{{ displayNumber }}</span>
    </div>
    <button
      class="dice-btn"
      :disabled="rolling"
      @click="roll"
    >
      🎲 掷骰子
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useMockStore } from '../stores/mockStore'

const mock = useMockStore()
const rolling = ref(false)
const displayNumber = ref('?')

const emit = defineEmits<{
  result: [value: number, success: boolean]
}>()

async function roll() {
  if (rolling.value) return
  rolling.value = true

  // 动画：快速切换数字
  const duration = 800
  const interval = 60
  const start = Date.now()
  const timer = setInterval(() => {
    displayNumber.value = String(Math.floor(Math.random() * 20) + 1)
    if (Date.now() - start >= duration) {
      clearInterval(timer)
      const result = mock.rollDice()
      displayNumber.value = String(result.result)
      rolling.value = false
      emit('result', result.result, result.success)
    }
  }, interval)
}
</script>

<style scoped>
.dice-roller {
  text-align: center;
}

.dice-display {
  width: 80px;
  height: 80px;
  margin: 0 auto 8px;
  background: var(--color-bg);
  border: 3px solid var(--color-accent);
  display: flex;
  align-items: center;
  justify-content: center;
  image-rendering: pixelated;
}

.dice-rolling {
  animation: dice-shake 0.1s infinite alternate;
  border-color: var(--color-accent-light);
}

@keyframes dice-shake {
  from { transform: rotate(-5deg); }
  to { transform: rotate(5deg); }
}

.dice-number {
  font-family: var(--font-pixel);
  font-size: var(--font-size-xl);
  color: var(--color-accent);
}

.dice-btn {
  font-size: var(--font-size-xs);
}
</style>
```

- [ ] **步骤 2：Commit**

```bash
git add client/src/components/DiceRoller.vue
git commit -m "feat: DiceRoller — D20 骰子动画组件

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 11：EventPanel 新组件

**文件：**
- 创建：`client/src/components/EventPanel.vue`

- [ ] **步骤 1：创建 EventPanel — 随机事件卡+自定义事件+骰子**

```vue
<template>
  <div class="event-panel">
    <h3>⚡ 每日事件</h3>
    <div class="quota-label">
      今日剩余 <span class="quota-num">{{ mock.dailyEventQuota }}</span> 次
    </div>

    <!-- 随机事件卡 -->
    <div class="event-cards">
      <div
        v-for="event in mock.randomEvents.slice(0, 3)"
        :key="event.id"
        class="event-card"
        @click="drawEvent(event)"
      >
        <span class="event-icon">{{ event.icon }}</span>
        <span class="event-name">{{ event.name }}</span>
      </div>
    </div>
    <button class="draw-btn" @click="drawRandom()">
      🎴 随机抽一张
    </button>

    <!-- 分隔 -->
    <div class="divider">或</div>

    <!-- 自定义事件 -->
    <div class="custom-event">
      <input
        v-model="customText"
        placeholder="自定义事件..."
        @keyup.enter="submitCustom"
      />
      <button @click="submitCustom">提交</button>
    </div>

    <!-- 骰子 -->
    <div class="divider">D20 判定</div>
    <DiceRoller @result="onDiceResult" />
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useMockStore } from '../stores/mockStore'
import DiceRoller from './DiceRoller.vue'
import type { RandomEvent } from '../types'

const mock = useMockStore()
const customText = ref('')

function drawRandom() {
  mock.drawRandomEvent()
}

function drawEvent(event: RandomEvent) {
  mock.currentEvent = event
  mock.drawRandomEvent()
}

function submitCustom() {
  mock.submitCustomEvent(customText.value)
  customText.value = ''
}

function onDiceResult(value: number, success: boolean) {
  // dice roller 已在内部调用 mock.rollDice() 和 toast
}
</script>

<style scoped>
.event-panel {
  background: var(--color-panel);
  border: 2px solid var(--color-border);
  padding: var(--gap-md);
}

.event-panel h3 {
  margin-bottom: 2px;
  font-size: var(--font-size-sm);
}

.quota-label {
  font-family: var(--font-pixel);
  font-size: 8px;
  color: var(--color-text-dim);
  margin-bottom: var(--gap-sm);
}

.quota-num {
  color: var(--color-accent);
}

.event-cards {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  margin-bottom: var(--gap-sm);
}

.event-card {
  flex: 1;
  min-width: 70px;
  background: var(--color-bg);
  border: 2px solid var(--color-border);
  padding: 6px;
  text-align: center;
  cursor: pointer;
  transition: border-color 0.15s;
}

.event-card:hover {
  border-color: var(--color-accent);
}

.event-icon {
  font-size: 18px;
  display: block;
}

.event-name {
  font-family: var(--font-pixel);
  font-size: 7px;
  color: var(--color-text-dim);
  margin-top: 2px;
  display: block;
}

.draw-btn {
  width: 100%;
  margin-bottom: var(--gap-sm);
}

.divider {
  text-align: center;
  font-family: var(--font-pixel);
  font-size: 8px;
  color: var(--color-text-dim);
  margin: var(--gap-sm) 0;
  position: relative;
}

.divider::before,
.divider::after {
  content: '';
  position: absolute;
  top: 50%;
  width: 30%;
  height: 1px;
  background: var(--color-border);
}

.divider::before { left: 0; }
.divider::after { right: 0; }

.custom-event {
  display: flex;
  gap: var(--gap-xs);
}

.custom-event input {
  flex: 1;
  font-size: 10px;
  padding: 5px;
}
</style>
```

- [ ] **步骤 2：Commit**

```bash
git add client/src/components/EventPanel.vue
git commit -m "feat: EventPanel — 随机事件卡+自定义事件+D20 骰子

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 12：EavesdropPanel 新组件

**文件：**
- 创建：`client/src/components/EavesdropPanel.vue`

- [ ] **步骤 1：创建 EavesdropPanel — 偷听目标选择**

```vue
<template>
  <div class="eavesdrop-panel">
    <h3>👂 偷听</h3>
    <div class="quota-label">
      今日剩余 <span class="quota-num">{{ mock.eavesdropQuota }}</span> 次
    </div>

    <div class="eavesdrop-targets">
      <div
        v-for="npc in mock.unlockedNPCs"
        :key="npc.id"
        class="target-chip"
        :class="{ 'target-selected': selected.includes(npc.id) }"
        @click="toggleTarget(npc.id)"
      >
        {{ npc.avatar }} {{ npc.name }}
      </div>
    </div>

    <button
      class="eavesdrop-btn"
      :disabled="selected.length < 2 || mock.eavesdropQuota <= 0"
      @click="doEavesdrop"
    >
      偷听 ({{ selected.length }}/2)
    </button>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useMockStore } from '../stores/mockStore'

const mock = useMockStore()
const selected = ref<string[]>([])

function toggleTarget(id: string) {
  const idx = selected.value.indexOf(id)
  if (idx >= 0) {
    selected.value.splice(idx, 1)
  } else if (selected.value.length < 2) {
    selected.value.push(id)
  }
}

function doEavesdrop() {
  if (selected.value.length < 2) return
  mock.doEavesdrop([...selected.value])
  selected.value = []
}
</script>

<style scoped>
.eavesdrop-panel {
  background: var(--color-panel);
  border: 2px solid var(--color-border);
  padding: var(--gap-md);
}

.eavesdrop-panel h3 {
  margin-bottom: 2px;
  font-size: var(--font-size-sm);
}

.quota-label {
  font-family: var(--font-pixel);
  font-size: 8px;
  color: var(--color-text-dim);
  margin-bottom: var(--gap-sm);
}

.quota-num {
  color: var(--color-accent);
}

.eavesdrop-targets {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: var(--gap-sm);
}

.target-chip {
  font-family: var(--font-pixel);
  font-size: 8px;
  padding: 4px 8px;
  background: var(--color-bg);
  border: 2px solid var(--color-border);
  cursor: pointer;
  transition: border-color 0.15s;
}

.target-chip:hover {
  border-color: var(--color-border-light);
}

.target-selected {
  border-color: var(--color-info);
  color: var(--color-info);
}

.eavesdrop-btn {
  width: 100%;
}
</style>
```

- [ ] **步骤 2：Commit**

```bash
git add client/src/components/EavesdropPanel.vue
git commit -m "feat: EavesdropPanel — 偷听目标 NPC 组合选择

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 13：NotebookPanel 新组件

**文件：**
- 创建：`client/src/components/NotebookPanel.vue`

- [ ] **步骤 1：创建 NotebookPanel — 三 tab 笔记簿**

```vue
<template>
  <div class="notebook-panel">
    <h3>📜 笔记簿</h3>

    <!-- Tab 栏 -->
    <div class="nb-tabs">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        class="nb-tab"
        :class="{ 'nb-tab--active': mock.notebookTab === tab.id }"
        @click="mock.notebookTab = tab.id"
      >
        {{ tab.icon }} {{ tab.label }}
      </button>
    </div>

    <!-- 事件时间线 -->
    <div class="nb-content" v-if="mock.notebookTab === 'timeline'">
      <div v-for="(entry, i) in mock.timeline" :key="i" class="nb-entry">
        <span class="nb-day">Day {{ entry.day }}</span>
        <span class="nb-source" :class="'src-' + entry.source">
          {{ sourceLabel(entry.source) }}
        </span>
        <span class="nb-text">{{ entry.text }}</span>
      </div>
    </div>

    <!-- NPC 观察 -->
    <div class="nb-content" v-if="mock.notebookTab === 'npc'">
      <div v-for="obs in mock.npcObservations" :key="obs.npcId" class="nb-npc-group">
        <div class="nb-npc-name">
          {{ getNPCName(obs.npcId) }}
        </div>
        <div v-for="(entry, i) in obs.entries" :key="i" class="nb-entry">
          <span class="nb-day">Day {{ entry.day }}</span>
          <span class="nb-text">{{ entry.text }}</span>
        </div>
      </div>
    </div>

    <!-- 玩家行动 -->
    <div class="nb-content" v-if="mock.notebookTab === 'actions'">
      <div v-for="(action, i) in mock.playerActions" :key="i" class="nb-entry">
        <span class="nb-day">Day {{ action.day }}</span>
        <span class="nb-text">{{ action.text }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useMockStore } from '../stores/mockStore'

const mock = useMockStore()

const tabs = [
  { id: 'timeline' as const, icon: '📋', label: '时间线' },
  { id: 'npc' as const, icon: '👤', label: 'NPC' },
  { id: 'actions' as const, icon: '💬', label: '行动' },
]

function sourceLabel(source: string): string {
  const map: Record<string, string> = { witnessed: '目击', heard: '听说', inferred: '推测' }
  return map[source] || source
}

function getNPCName(npcId: string): string {
  return mock.npcs.find(n => n.id === npcId)?.name || npcId
}
</script>

<style scoped>
.notebook-panel {
  background: var(--color-panel);
  border: 2px solid var(--color-border);
  padding: var(--gap-md);
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 150px;
}

.notebook-panel h3 {
  margin-bottom: var(--gap-sm);
  font-size: var(--font-size-sm);
}

.nb-tabs {
  display: flex;
  gap: 4px;
  margin-bottom: var(--gap-sm);
}

.nb-tab {
  flex: 1;
  font-size: 8px;
  padding: 4px 6px;
  background: var(--color-bg);
  border: 2px solid var(--color-border);
  cursor: pointer;
  transition: border-color 0.15s;
}

.nb-tab--active {
  border-color: var(--color-accent);
  color: var(--color-accent);
}

.nb-content {
  flex: 1;
  overflow-y: auto;
  max-height: 250px;
  font-size: 10px;
}

.nb-entry {
  padding: 4px 0;
  border-bottom: 1px solid var(--color-border);
  line-height: 1.5;
}

.nb-day {
  font-family: var(--font-pixel);
  font-size: 8px;
  color: var(--color-accent);
  margin-right: 6px;
}

.nb-source {
  font-family: var(--font-pixel);
  font-size: 7px;
  padding: 1px 3px;
  margin-right: 4px;
}

.src-witnessed { color: var(--color-health); }
.src-heard { color: var(--color-info); }
.src-inferred { color: var(--color-hunger); }

.nb-text {
  color: var(--color-text-dim);
}

.nb-npc-group {
  margin-bottom: var(--gap-sm);
}

.nb-npc-name {
  font-family: var(--font-pixel);
  font-size: 9px;
  color: var(--color-accent-light);
  margin-bottom: 4px;
  padding-bottom: 2px;
  border-bottom: 1px solid var(--color-accent);
}
</style>
```

- [ ] **步骤 2：Commit**

```bash
git add client/src/components/NotebookPanel.vue
git commit -m "feat: NotebookPanel — 三 tab 笔记簿（时间线/NPC观察/玩家行动）

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

### 任务 14：集成验证与构建

**文件：** 无新文件。

- [ ] **步骤 1：运行 TypeScript 类型检查**

```bash
cd client && npx vue-tsc --noEmit
```
预期：无类型错误。

- [ ] **步骤 2：运行 Vite 构建**

```bash
cd client && npx vite build
```
预期：构建成功，所有组件正确编译。

- [ ] **步骤 3：检查构建输出**

```bash
ls -la client/dist/
```
预期：存在 `index.html` 和 `assets/` 目录。

- [ ] **步骤 4：检查所有新增文件在 git 中**

```bash
git status
```
预期：无遗漏的未追踪文件。

- [ ] **步骤 5：Commit**

```bash
git add -A
git commit -m "chore: 前端 v2 完全体构建验证通过

Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>"
```

---

## 依赖关系

```
任务 1 (CSS vars) ──┬── 任务 6 (NPCPanel)
                    ├── 任务 7 (StatusPanel)
                    ├── 任务 8 (ChatPanel)
                    ├── 任务 9 (ToolPanelV2)
                    ├── 任务 10 (DiceRoller)
                    ├── 任务 11 (EventPanel)
                    ├── 任务 12 (EavesdropPanel)
                    └── 任务 13 (NotebookPanel)

任务 2 (toast) ────── 任务 4 (mockStore) ──── 所有组件任务

任务 3 (types) ────── 任务 4 (mockStore) ──── 所有组件任务

任务 5 (App.vue) ──── 依赖任务 1, 4 完成，等待所有组件任务

任务 14 (验证) ────── 依赖所有任务完成
```

推荐执行顺序：1 → (2, 3 并行) → 4 → 5 → (6 到 13 并行) → 14
