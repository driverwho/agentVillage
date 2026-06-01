# 🌾 麦穗小镇 · Agent Village

> LLM 驱动的多智能体村庄模拟游戏——NPC 拥有独立信念系统与自主决策能力，世界通过信息传播与因果链自然演化。

**🎮 [静态演示页面](https://driverwho.github.io/agentVillage/)**

---

## 核心理念

**涌现优于编排。** 不为 NPC 硬编码行为逻辑，而是创造条件让自发、可信的交互自然涌现：

- **主观信念** — 每个 NPC 维护独立的信念存储，通过目击、交谈、推断获得，随时间衰减
- **信息传播** — 信息通过对话扩散，信任度逐级衰减（高→中→低），内容由 LLM 自然扭曲
- **事件驱动** — NPC 不按固定时间表行动，而是由活动完成、信念冲突、生理需求触发决策
- **玩家平等** — 玩家是村庄的普通一员，行为遵循与 NPC 相同的规则，无特殊地位

---

## 主要功能

| 功能 | 说明 |
|---|---|
| **LLM 驱动 NPC** | 基于 DeepSeek API，NPC 通过 function calling 自主选择工具执行动作 |
| **信念系统** | 目击（高置信度）、被告知（中）、推断/偷听（低），冲突信念由 LLM 自行裁决 |
| **NPC 间对话** | NPC 可自主发起对话，对话有生命周期，信念在对话中传播 |
| **梦境/日结** | NPC 睡眠时 LLM 生成当日叙事总结，既是记忆压缩也是故事生成 |
| **世界事件** | 基于 YAML 模板随机生成天气、事件、访客，有条件和冷却机制 |
| **六层上下文构建** | L0 人格→L1 世界→L2 自身→L3 对话者→L4 记忆→L5 对话历史，每层有预算配额 |
| **双页面前端** | 游戏主页面 + 观察调试页面（实时 NPC 状态、LLM 调用历史） |
| **多用户支持** | 数据按用户隔离存储，当前使用 "default" 用户 |

---

## 技术栈

| 层 | 技术 |
|---|---|
| **前端** | Vue 3 + TypeScript + Pinia + Vite 5 |
| **后端** | Python 3 + FastAPI + Uvicorn |
| **LLM** | DeepSeek API（httpx 异步客户端 + SSE 流式） |
| **通信** | REST + WebSocket（状态广播）+ SSE（流式对话） |
| **存储** | 本地 JSON 文件 + YAML 配置 |
| **NPC 配置** | YAML 角色背景文档（传记、怪癖、对话主题、信息层级、状态反应） |

---

## 项目结构

```
agentVillage/
├── client/                    # Vue 3 前端
│   └── src/
│       ├── pages/             # GamePage, ObservePage
│       ├── components/        # ChatPanel, NPCPanel, VillageNewsPanel ...
│       ├── stores/            # Pinia 状态管理
│       └── services/          # API, WebSocket, Mock 模式
├── server/                    # FastAPI 后端
│   ├── api/                   # REST 路由 + WebSocket
│   ├── core/                  # Orchestrator, TimeSystem, EventEngine
│   ├── agents/                # NPC 智能体（Farmer, Bartender）
│   ├── llm/                   # LLMClient, ContextBuilder, MemoryRetriever
│   ├── tools/                 # 工具系统（定义、策略、执行、注册）
│   ├── memory/                # 文件记忆管理器
│   └── data/                  # NPC 背景 YAML + 事件模板
└── data/                      # 运行时数据
    └── users/{user_id}/       # 世界状态、信念、事件日志、记忆
```

---

## 快速开始

### 环境准备

```bash
# 复制配置文件，填入 DeepSeek API Key
cp server/.env.example server/.env
# 编辑 server/.env：DEEPSEEK_API_KEY=sk-your-key
```

### 启动后端

```bash
cd server
pip install -r requirements.txt
python main.py
# 运行于 http://localhost:8000
```

### 启动前端

```bash
cd client
npm install
npm run dev
# 运行于 http://localhost:5173
```

### Mock 模式（无需后端和 API Key）

```bash
cd client
VITE_MOCK=true npm run dev
```

### 页面入口

| 页面 | 地址 |
|---|---|
| 游戏主页 | `http://localhost:5173/` |
| 观察调试 | `http://localhost:5173/observe` |
| LLM 监控 | `http://localhost:8000/llm-monitor` |

---

## 开发状态

**当前阶段：Phase 1 MVP 完成**

- [x] 2 个 NPC（农夫 George、酒保 Gus）
- [x] 时间系统（10s 真实时间 = 1 游戏小时）
- [x] 玩家对话（REST + SSE 流式）
- [x] NPC 状态系统
- [x] 基础世界事件引擎
- [x] 村庄见闻面板
- [x] 信念系统 + 事件日志 + 目击规则
- [ ] Phase 2：信念传播扭曲、交互优化
- [ ] Phase 3：剩余 4 个 NPC（警长、医生、牧师、画家）、成就系统

---

## License

MIT
