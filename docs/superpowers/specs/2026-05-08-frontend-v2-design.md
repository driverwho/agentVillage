# Agent Village 前端 v2 完全体设计规格

## 概述

基于 v2 核心玩法设计文档，重构建前端为三栏布局的"完全体"形态。即使后端功能未完全实现，前端也展示完整的 UI 结构——未实现的功能按钮可点击但触发前端动画后弹出"功能开发中"提示。

## 已确认决策

| 决策项 | 结论 |
|--------|------|
| 布局 | 三栏：左 260px（NPC+状态）+ 中 flex（对话+工具）+ 右 280px（事件+笔记簿+偷听） |
| 配色 | 暖褐金提亮版，保留夜间模式，整体抬升 2 档亮度 |
| 按钮风格 | 去除渐变+发光阴影，改为纯色底+粗像素边框，与面板背景统一 |
| 像素风 | 保留 Press Start 2P 像素字体 + CRT 扫描线叠加层 |
| 未实现功能 | 按钮可点击，执行纯前端效果后弹出 toast 提示"功能开发中，敬请期待" |
| 实现方式 | 逐组件构建 + mockStore 驱动，不影响现有对话/时间功能 |
| NPC 命名 | 简洁代号风格：农夫·托德、酒保·盖斯、警长·巴顿、占卜师·丽娜、流浪者·威利、杂货商·洛克 |

---

## 1. 布局架构

```
┌──────────────────────────────────────────────────────────────────┐
│  HEADER (sticky)                                                  │
│  🏘 Agent Village          Day 3 · 14:00  ▶ 运行中  [+1时] [+6时] │
├────────────────┬────────────────────────────┬─────────────────────┤
│ LEFT (260px)   │ CENTER (flex, min 400px)   │ RIGHT (280px)       │
│ scroll-y       │ scroll-y                   │ scroll-y            │
│                │                            │                     │
│ 📊 玩家状态     │ 💬 对话面板                 │ ⚡ 每日事件          │
│ ─────────────  │ ───────────────────────     │ ──────────────────   │
│ 生命 ████ 80   │ [对话历史]                  │ 🎴 随机事件卡        │
│ 饥饿 ████ 60   │                            │ 📝 自定义事件        │
│ 疲劳 ████ 30   │ [对话选项居中分散]           │ 🎲 D20 骰子          │
│ 金币 120       │ [问问庄稼] [聊聊天气] [..]    │                     │
│                │                            │ 👂 偷听 (1次/天)     │
│ 👤 村庄居民     │ [自由输入____________] [发送] │ ──────────────────   │
│ ─────────────  │                            │                     │
│ 🧑‍🌾 农夫·托德   │ 🛠 可用工具                 │ 📜 笔记簿            │
│   🌾 工作中     │ ──────────────────          │ ──────────────────   │
│ ♥80 🍖60 💤30  │ 🌾耕作 🗡交易🔒 🛡巡逻🔒    │ 📋时间线 👤NPC 💬行动│
│                │                            │ Day1 酒保和商人交易.. │
│ 🍺 酒保·盖斯    │                            │ Day2 农夫在酒馆发火.. │
│   🧹 整理中     │                            │                     │
│ ♥45 🍖50 💤20  │                            │                     │
│                │                            │                     │
│ 🔒 待解锁       │                            │                     │
│ ⭐ 警长·巴顿    │                            │                     │
│ 🔮 占卜师·丽娜  │                            │                     │
│ 🪙 流浪者·威利  │                            │                     │
│ 📦 杂货商·洛克  │                            │                     │
└────────────────┴────────────────────────────┴─────────────────────┘
```

### 1.1 列规则

| 属性 | 左栏 | 中栏 | 右栏 |
|------|------|------|------|
| 宽度 | 260px, flex-shrink: 0 | flex: 1, min-width: 400px | 280px, flex-shrink: 0 |
| 滚动 | overflow-y: auto | overflow-y: auto | overflow-y: auto |
| 边线 | border-right | 无 | border-left |

### 1.2 响应式断点

| 宽度 | 行为 |
|------|------|
| >= 1000px | 三栏完整显示 |
| 700-999px | 右栏折叠为底部面板 |
| < 700px | 左栏折叠为顶部 tab，单列布局 |

---

## 2. 组件树

```
App.vue
├── TimeControl.vue          (Header 内，已有)
├── StatusPanel.vue          (左栏，已有，需改样式)
├── NPCPanel.vue             (左栏，重构：头像+状态标签+解锁列表)
├── ChatPanel.vue            (中栏，重构：居中选项按钮+像素风格)
├── ToolPanelV2.vue          (中栏，重构：多工具+信任解锁)
├── EventPanel.vue           (右栏，新增：随机事件卡+自定义+骰子)
├── EavesdropPanel.vue       (右栏，新增：偷听选择)
├── NotebookPanel.vue        (右栏，新增：时间线/NPC/行动)
└── DiceRoller.vue           (EventPanel 子组件，骰子动画)
```

### 2.1 组件职责

| 组件 | 状态 | 职责 |
|------|------|------|
| TimeControl | 已有，微调样式 | 时间显示、暂停/开始、+1时/+6时/+1天 |
| StatusPanel | 已有，改样式 | 玩家生命/饥饿/疲劳/金币/好感度 |
| NPCPanel | 重构 | NPC 列表：像素头像+名称+状态标签+数值+好感度条，解锁角色灰显 |
| ChatPanel | 重构 | 对话历史、居中分散选项按钮、自由输入框；选项来自 mock 数据 |
| ToolPanelV2 | 重构 | 工具列表，信任等级解锁，未解锁工具灰显+点击弹提示 |
| EventPanel | 新增 | 随机事件卡抽取、自定义事件输入、D20 骰子 |
| DiceRoller | 新增 | D20 骰子动画（纯前端，不调用后端） |
| EavesdropPanel | 新增 | 1次/天偷听，选择目标 NPC 组合 |
| NotebookPanel | 新增 | 三 tab：事件时间线、NPC 观察日志、玩家行动记录 |

---

## 3. CSS 变量规格

```css
:root {
  /* 背景（暖褐提亮） */
  --color-bg: #2c1f16;           /* 页面底色，原 #1a1410 */
  --color-panel: #3d2d20;        /* 面板底色，原 #2a2218 */
  --color-input: #33251a;        /* 输入框底色，原 #1f1a12 */
  --color-hover: #4a3828;        /* hover 高亮，新增 */

  /* 边框 */
  --color-border: #7a5540;       /* 常规边框，原 #5c3d2e */
  --color-border-light: #a08060; /* 亮边框/分隔线，原 #8b7355 */

  /* 强调色 */
  --color-accent: #daa520;       /* 金色（不变） */
  --color-accent-light: #e8c44a; /* 浅金，原 #ffd700 */

  /* 文字 */
  --color-text: #f0dfc4;         /* 主文字，原 #e8d5b7 */
  --color-text-dim: #c4a882;     /* 次级文字，原 #8b7355 */

  /* 状态色 */
  --color-health: #7fb330;       /* 生命，原 #6b8e23 */
  --color-hunger: #e8a64e;       /* 饥饿，原 #cd853f */
  --color-fatigue: #cc4444;      /* 疲劳/危险，原 #b22222 */
  --color-info: #6b9ec4;         /* 信息/蓝色，原 #4682b4 */

  /* 排版（不变） */
  --font-pixel: 'Press Start 2P', 'Courier New', monospace;
  --font-body: 'Microsoft YaHei', 'SimHei', sans-serif;
  --font-size-xs: 10px;
  --font-size-sm: 12px;
  --font-size-base: 14px;
  --font-size-lg: 18px;

  /* 间距（不变） */
  --gap-xs: 4px;
  --gap-sm: 8px;
  --gap-md: 16px;
  --gap-lg: 24px;
}
```

### 3.1 按钮样式变更

```css
/* 旧（删除） */
button {
  background: linear-gradient(180deg, #3a2a18 0%, #2a1a10 100%);
  box-shadow: var(--pixel-border);  /* 0 0 0 2px + 0 0 0 3px 双层阴影 */
  border: none;
}

/* 新（替换） */
button {
  background: var(--color-bg);      /* #2c1f16，与页面背景统一 */
  border: 2px solid var(--color-border); /* #7a5540，单层粗边框 */
  color: var(--color-text);
  font-family: var(--font-pixel);
  padding: 6px 12px;
  cursor: pointer;
}
button:hover { border-color: var(--color-accent); color: var(--color-accent); }
button:disabled { opacity: 0.4; border-color: var(--color-text-dim); cursor: not-allowed; }
```

### 3.2 NPC 状态标签颜色

| 状态 | 标签 | 颜色 | 判定条件 |
|------|------|------|---------|
| 工作中 | 🌾 工作中 | #7fb330 绿 | 08:00-18:00，在自身工作地点 |
| 休息中 | ☕ 休息中 | #e8a64e 橙 | 12:00-13:00 或 fatigue > 70 |
| 酒馆社交 | 🍺 酒馆社交 | #6b9ec4 蓝 | 18:00-22:00，在酒馆 |
| 睡眠中 | 😴 睡眠中 | #c4a882 灰 | 22:00-06:00 |
| 状态异常 | ⚠ 状态异常 | #cc4444 红 | mood < 20 或 health < 30 |
| 外出中 | 📍 外出中 | #6b9ec4 蓝 | 不在常驻地点 |

---

## 4. NPC 设定

### 4.1 NPC 列表

| ID | 名称 | 角色 | 头像 | 初始状态 |
|----|------|------|------|---------|
| farmer | 农夫·托德 | 村庄农夫 | 🧑‍🌾（像素头像） | 已解锁 |
| bartender | 酒保·盖斯 | 酒馆老板 | 🍺（像素头像） | 已解锁 |
| sheriff | 警长·巴顿 | 治安官 | ⭐（像素头像） | 待解锁 |
| fortune_teller | 占卜师·丽娜 | 神秘占卜师 | 🔮（像素头像） | 待解锁 |
| beggar | 流浪者·威利 | 流浪乞丐 | 🪙（像素头像） | 待解锁 |
| shopkeeper | 杂货商·洛克 | 杂货店老板 | 📦（像素头像） | 待解锁 |

### 4.2 NPC 头像

每个 NPC 使用 40×40 像素风头像，放置在角色卡片左侧。Demo 阶段使用 CSS pixel-art 或 emoji 占位，后续替换为真正的像素艺术资源。

---

## 5. Mock 数据层

### 5.1 mockStore 设计

```typescript
// stores/mockStore.ts
export const useMockStore = defineStore('mock', () => {
  // ── 事件系统 mock ──
  const dailyEventQuota = ref(1)
  const randomEvents = ref([...])  // 事件池
  const currentEvent = ref(null)

  // ── 笔记簿 mock ──
  const timeline = ref([...])      // 事件时间线条目
  const npcObservations = ref({})  // 按 NPC 分组的观察日志
  const playerActions = ref([...]) // 玩家行动记录

  // ── 偷听 mock ──
  const eavesdropQuota = ref(1)
  const eavesdropTargets = ref([])

  // ── 工具解锁 mock ──
  const tools = ref([
    { id: 'farming', name: '耕作', unlocked: true, trustRequired: 0 },
    { id: 'trading', name: '交易', unlocked: false, trustRequired: 30 },
    { id: 'patrol', name: '巡逻', unlocked: false, trustRequired: 60 },
    { id: 'divination', name: '占卜', unlocked: false, trustRequired: 90 },
  ])

  // ── 方法：前端动画 + 提示 ──
  function rollDice(): { result: number; success: boolean } {
    // 纯前端随机，返回动画结果
  }

  function showComingSoonToast(feature: string) {
    // 弹出 "功能开发中，敬请期待" toast
  }
})
```

### 5.2 真实 API vs Mock 对照

| 功能 | 数据来源 | 按钮行为 |
|------|---------|---------|
| 对话 | 真实 API `/api/chat/{npc}` | 正常发送 |
| 时间推进 | 真实 API `/time/advance` | 正常推进 |
| 玩家状态 | 真实 API `/api/player` | 正常刷新 |
| 耕作工具 | 真实 API `/api/tool/farming` | 正常使用 |
| 随机事件卡 | Mock | 前端动画 + toast 提示 |
| 自定义事件 | Mock | 前端动画 + toast 提示 |
| 骰子掷出 | Mock | 前端 D20 动画 + toast 提示 |
| 偷听 | Mock | 前端动画 + toast 提示 |
| 笔记簿 | Mock 静态数据 | 只读展示 |
| 交易/巡逻/占卜 | Mock | toast 提示"功能开发中" |

---

## 6. 对话选项按钮规范

NPC 回复时展示 2-3 个情境化选项按钮：

- 按钮居中排列，`justify-content: center`，间距 10px
- 样式与面板背景统一：`background: var(--color-bg); border: 2px solid var(--color-border)`
- hover 时边框变金色
- 点击后替换为下一组选项（mock 数据提供预设选项链）
- 自由输入框始终在选项下方可用
- Demo 阶段选项由前端 mock 数据提供，不依赖后端 LLM 生成

---

## 7. 待解锁角色展示规则

- 虚线边框 `border: 1px dashed`
- 整体透明度 0.55
- 头像灰度 `filter: grayscale(70%)`
- 状态标签统一显示 "🔒 解锁条件未知"
- 不可点击选择
- 按游戏设定顺序排列在已解锁 NPC 下方
- 分隔线标题 "🔒 待解锁"

---

## 8. 无终点设计

根据 v2 设计，取消固定结局。前端移除：
- 结局条件进度条
- 结局触发提示
- 重生/轮回 UI

---

## 9. 实现范围

### Phase 1（本次实现）—— 完全体前端

**新增组件（5 个）：**
- EventPanel.vue — 每日事件面板
- DiceRoller.vue — D20 骰子动画
- EavesdropPanel.vue — 偷听面板
- NotebookPanel.vue — 笔记簿面板
- ToolPanelV2.vue — 工具面板重构

**重构组件（4 个）：**
- App.vue — 三栏 Grid 布局
- ChatPanel.vue — 居中选项按钮+像素按钮风格
- NPCPanel.vue — 头像+状态标签+解锁列表
- StatusPanel.vue — 新配色变量

**新增模块（2 个）：**
- mockStore.ts — Mock 数据驱动
- toast.ts — Toast 提示工具

**样式改动：**
- variables.css — 暖褐金配色覆盖
- global.css — 按钮风格统一，移除渐变阴影

### 保留不变
- TimeControl.vue（仅配色适配）
- api.ts / websocket.ts
- gameStore.ts（保持现有 API 调用逻辑）
- types/index.ts

### 后续对接
后端功能逐步就绪后，mockStore 中的数据和方法替换为真实 API 调用，接口保持一致。
