# interview-prep skill 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 构建 interview-prep skill，为求职者提供自适应面试练习功能（技术问答 + 行为面），支持记忆、针对性出题、多模式交互。

**架构：** 三个 markdown 文件组成 skill（SKILL.md 主入口 + question-engine.md 策略引擎 + evaluation-guide.md 评估标准），持久化数据存 `~/.interview-prep/`（JSON 画像 + JSONL 历史），跨项目通用。

**技术栈：** Claude Code skill 框架（markdown 文档 + YAML frontmatter），无传统代码依赖。

---

## 文件结构

```
.claude/skills/interview-prep/
├── SKILL.md              # 主入口：触发条件、命令路由、模式流程、数据管理
├── question-engine.md    # 出题引擎：优先级策略、难度自适应、角度分配、矩阵更新
└── evaluation-guide.md   # 评估标准：反馈模板、评分规则、间隔重复管理

~/.interview-prep/
├── profile.json          # 用户画像（运行时由 skill 创建和管理）
├── ability-matrix.json   # 能力矩阵（运行时由 skill 创建和管理）
├── history/
│   └── YYYY-MM-DD.jsonl  # 答题记录（按日追加）
├── jds/
│   └── *.md              # 用户保存的 JD 文件
└── sessions/
    └── YYYY-MM-DD-mock.md  # 模拟面试记录
```

**职责划分：**
- **SKILL.md** — 用户交互入口，路由命令到对应模式，管理数据文件的读写，不展开策略细节
- **question-engine.md** — 纯策略逻辑，被 SKILL.md 引用，决定"出什么题"
- **evaluation-guide.md** — 纯评估逻辑，被 SKILL.md 引用，决定"怎么判分"

---

### 任务 1：创建 SKILL.md 主入口文件

**文件：**
- 创建：`.claude/skills/interview-prep/SKILL.md`

- [ ] **步骤 1：创建目录并编写 SKILL.md**

```bash
mkdir -p .claude/skills/interview-prep
```

```markdown
---
name: interview-prep
description: 面试准备：出题练习、模拟面试、薄弱点复习。Use when user: 准备面试、要求出题、模拟面试、评估技术掌握程度、复习知识点、查漏补缺、分析 JD。
---

# 面试出题教练

## 概述

自适应面试练习教练。基于能力画像出题（技术问答 + 行为面），记忆答题历史和薄弱点，越练越精准。支持单组出题、模拟面试、间隔复习三种模式。

## 何时使用

触发关键词：面试、出题、模拟面试、mock interview、复习、查漏补缺、技术面、行为面、JD分析、项目深挖

不适用：需要手写代码题、需要联网搜索真实面经

## 命令路由

| 命令 | 模式 | 说明 |
|------|------|------|
| `/interview` | 单组 | 自动选题，3-5 题不同角度 |
| `/interview <维度> <难度>` | 单组 | 指定维度+难度，如 `/interview vue 高级` |
| `/interview --jd <name>` | 单组 | 基于已保存 JD 出题 |
| `/interview --project` | 单组 | 基于当前项目出题 |
| `/interview --weak` | 单组 | 专攻薄弱点 |
| `/interview --mock [分钟]` | 模拟面试 | 连续对话，默认 30 分钟 |
| `/interview --review` | 复习 | 间隔重复复习 |
| `/interview --setup` | 设置 | 初始化/修改画像 |

## 首次使用

当 `~/.interview-prep/` 不存在时，自动进入初始化流程：

1. 告知用户将创建 `~/.interview-prep/` 目录
2. 依次询问并填写 profile.json：
   - 目标岗位（如"全栈工程师 Agent方向"）
   - 技术栈（逗号分隔，如 Vue, TypeScript, Python, LangChain, FastAPI）
   - 工作年限（数字）
   - 当前重点准备方向（逗号分隔）
   - 偏好难度（初级/中级/高级）
   - 反馈模式（简洁/详细）
3. 创建目录结构：`mkdir -p ~/.interview-prep/{history,jds,sessions}`
4. 写入 profile.json 和初始 ability-matrix.json（空矩阵）
5. 提示初始化完成，询问是否开始第一组题目

### profile.json 结构

```json
{
  "target_role": "",
  "experience_years": 0,
  "tech_stack": [],
  "focus_areas": [],
  "preferred_difficulty": "中级",
  "feedback_mode": "concise",
  "active_jd": null
}
```

### ability-matrix.json 初始结构

```json
{
  "dimensions": {},
  "behavioral": {
    "score": 0.5,
    "weak_points": [],
    "last_practiced": null
  }
}
```

## 单组模式（默认）

一次性出 3-5 题（不同角度）。流程：

1. 读取 `~/.interview-prep/profile.json` 和 `~/.interview-prep/ability-matrix.json`
2. 读取 `question-engine.md`，按出题策略选择维度和角度
3. 一次展示 3-5 题：
   ```
   ## 第 N 组：<维度> · <难度>
   
   **Q1** [概念理解] ...
   **Q2** [对比分析] ...
   **Q3** [实践应用] ...
   **Q4** [踩坑经验] ...
   **Q5** [系统设计] ...
   ```
4. 用户逐题作答（支持自由顺序，每题标号对应）
5. 每题作答后，读取 `evaluation-guide.md` 评估：
   - 简洁模式（默认）：判定等级 + 1-2 句遗漏点
   - 如用户回复"详细"，展开完整参考答案和解析
6. 全组答完后更新数据：
   - 按 `evaluation-guide.md` 中的矩阵更新算法更新 ability-matrix.json
   - 追加答题记录到 `~/.interview-prep/history/YYYY-MM-DD.jsonl`
7. 询问：详细反馈某题 / 下一组 / 结束

### 记录追加格式

写入 `~/.interview-prep/history/YYYY-MM-DD.jsonl`，每行一条：

```json
{"id":"q-20260509-001","timestamp":"2026-05-09T14:30:00","mode":"single","dimension":"vue","difficulty":"中级","question":"...","answer_summary":"...","evaluation":"一般","missed_points":["flush timing"],"source":"auto","review_state":{"interval_days":1,"next_review":"2026-05-10","consecutive_correct":0}}
```

- `id` 格式：`q-YYYYMMDD-NNN`（自增序号）
- `evaluation`：熟练 / 一般 / 薄弱
- `source`：auto / jd:<name> / project / weak / spec:<dimension>
- `review_state` 仅当 evaluation 不是"熟练"时写入

## 模拟面试模式

以面试官角色进行连续对话。

1. 读取 profile + ability-matrix + active_jd（如有）
2. 生成面试大纲（不展示给用户）：
   - 开场寒暄（1min）
   - 项目深挖（40%时间）— 基于 active_jd 或用户 focus_areas
   - 技术问答（40%时间）— 3-5 题由浅入深
   - 行为面（15%时间）— 1-2 题
   - 反问环节提示（5%时间）
3. 以面试官角色开始对话，每轮只问一个问题
4. 根据回答实时追问或转向下一题
5. 结束后给出整体评估报告，包含：
   - 各维度表现评级
   - 亮点
   - 改进建议
   - 与目标岗位的差距分析
6. 保存完整记录到 `~/.interview-prep/sessions/YYYY-MM-DD-mock.md`
7. 提取答题记录更新 ability-matrix

## 复习模式

基于间隔重复的复习。

1. 扫描 `~/.interview-prep/history/` 下所有 jsonl 文件
2. 筛选条件：evaluation 为"一般"或"薄弱"，且 `review_state.next_review <= 今天`
3. 按 `next_review` 升序排列，取前 5 题
4. 对每个知识点**换角度出题**（不原题重出）：
   - 原题问概念 → 复习问应用场景
   - 原题问对比 → 复习问选型决策
5. 每题评估后更新 `review_state`（按 evaluation-guide.md 中的间隔规则）
6. 无待复习题时："当前没有需要复习的内容。上次练习是 <date>，要继续常规练习吗？"

## 项目分析（--project 模式）

在当前项目目录中使用时激活。

1. 快速扫描项目：
   - `package.json` / `requirements.txt` → 技术栈
   - 顶级目录结构 → 架构模式
   - `docs/` 目录 → **设计文档视同已实现**
   - `git log --oneline -20` → 用户贡献热点
2. 生成三类题目（3-5 题）：
   - 设计决策题
   - 深挖实现题
   - 假设变更/复盘题
3. 行为面也与项目关联（项目经历、技术挑战、冲突处理）
4. 对项目只读，不在 `~/.interview-prep/` 中存储项目代码

## 设置模式

`/interview --setup` 进入设置流程：

1. 展示当前 profile
2. 询问要修改的字段
3. 更新并保存

## 边界

- 不出手写代码题
- 数据仅本地存储，不联网
- 单组 3-5 题
- 首次使用必须完成 profile 初始化
- 项目分析只读

## 子文件引用

- **出题策略细节** → 读取 `question-engine.md`
- **评估标准与反馈模板** → 读取 `evaluation-guide.md`
- 在需要做出题决策或评分时，必须读取对应子文件
```

- [ ] **步骤 2：验证 SKILL.md 结构**

检查清单：
- YAML frontmatter 含 `name` 和 `description`
- description 以 "Use when" 开头，第三人称，仅含触发条件
- 所有模式有清晰的流程描述
- 子文件引用明确

---

### 任务 2：创建 question-engine.md 出题引擎

**文件：**
- 创建：`.claude/skills/interview-prep/question-engine.md`

- [ ] **步骤 1：编写 question-engine.md**

```markdown
# 出题引擎

被 SKILL.md 引用，决定"出什么题"。

## 出题策略优先级

按以下顺序决策，一旦命中就出题：

| 优先级 | 条件 | 动作 |
|--------|------|------|
| P1 | 用户显式指定维度/难度 | 直接遵循，跳过其他策略 |
| P2 | profile.active_jd 非空，JD 中有技术点在矩阵中 score < 0.7 | 从 JD 技术点 ∩ 低分维度中选题 |
| P3 | 维度 `last_practiced` > 7天前 且 score < 0.7 | 优先出遗忘维度 |
| P4 | 维度 weak_points 非空 | 选频次最高的薄弱点，换角度深挖 |
| P5 | 以上都不触发 | 选 total_questions 最少的维度 |

## 难度自适应

基于当前维度的 score：

| score | 动作 | 说明 |
|-------|------|------|
| >= 0.8 | 升级难度 | 初级→中级→高级，已是高级则拓展相邻维度 |
| 0.5 - 0.8 | 保持 | 若用户指定了难度则优先用户指定 |
| < 0.5 | 降级 | 侧重基础概念和常规用法 |

首次练习的维度从 profile.preferred_difficulty 开始。

## 3-5 题角度分配

每组从以下 5 个角度中选择 3-5 个，根据维度和难度匹配：

| 角度 | 适用难度 | 题型模板 |
|------|----------|----------|
| 概念理解 | 全部 | "解释 X 是什么？核心原理是什么？" |
| 对比分析 | 中/高 | "X vs Y，各自适用场景？你倾向选哪个？" |
| 实践应用 | 全部 | "如何配置/实现 X？写出关键步骤。" |
| 踩坑经验 | 中/高 | "X 的常见问题有哪些？出问题时你怎么排查？" |
| 系统设计 | 高 | "设计一个 X，关键考虑点和 trade-off。" |

**分配规则：**
- 初级：概念理解 + 实践应用（2-3 题），可选 1 题对比（简单对比）
- 中级：5 个角度各选 1 题，偏重对比分析和踩坑经验
- 高级：5 个角度各选 1 题，偏重系统设计和踩坑经验

## 维度映射

用户说"前端"时映射到：

- JavaScript/TypeScript 基础
- 框架（Vue/React，从 profile.tech_stack 判断）
- CSS / 浏览器 / 性能
- 工程化（构建、测试、部署）

用户说"后端"时映射到：

- 语言基础（Python/Node/Go，从 profile.tech_stack 判断）
- 数据库与 ORM
- API 设计与认证
- 部署与运维

用户说"Agent"时映射到：

- LLM 基础（prompt engineering、token、上下文窗口）
- Agent 架构（ReAct、Plan-Execute、多 Agent 协作）
- 工具使用与 function calling
- 记忆系统设计
- 评估与安全

## 题目来源

### 基于 JD 出题（--jd）

1. 读取 `~/.interview-prep/jds/<name>.md`
2. 提取 JD 中的技术要求关键词
3. 与 ability-matrix 交叉比对：
   - JD 中提到、矩阵中 score < 0.7 的技术点优先
   - JD 中提到、矩阵中不存在的技术点次之（新领域）
4. 生成针对该 JD 的 3-5 题

### 基于项目出题（--project）

1. 扫描当前项目技术栈（package.json / requirements.txt）
2. 扫描 `docs/` 目录——设计文档中描述的功能视同已实现
3. 通过 git log 识别用户主要负责的模块
4. 生成三类题目：
   - **设计决策：** "你的 X 模块为什么选择这种架构？"
   - **深挖实现：** "X 系统中的 Y 机制具体怎么实现的？"
   - **假设变更：** "如果 Z 需求变了，你的方案怎么调整？"
5. 与行为面结合：
   - "这个项目中遇到的最大技术挑战是什么？"
   - "有人对你的方案有异议，你怎么处理的？"

### 针对薄弱点（--weak）

1. 读取 ability-matrix 中所有 weak_points
2. 按频次排序，选频次最高的 3-5 个
3. 换角度出题——如果之前是从概念角度答错的，这次从应用角度出

## 矩阵更新算法

一组题目全部答完后执行。逐题更新：

```
// 每题独立更新
evaluation → score_this:
  熟练 = 1.0
  一般 = 0.6
  薄弱 = 0.2

new_score = old_score × 0.7 + score_this × 0.3

// 更新 weak_points
如果 missed_points 非空:
  逐一合并到维度 weak_points
  已存在的点：内部权重 +1
  新点：添加，权重为 1

// 更新时间戳
last_practiced = 今天
total_questions += 1
如果 evaluation == "熟练": correct += 1

// 更新难度等级
如果 score >= 0.8 连续两次: level 升一级
如果 score < 0.3 连续两次: level 降一级
```

## 维度动态创建

当用户练习 profile.tech_stack 中但 ability-matrix 中不存在的维度时：

```json
{
  "<new_dimension>": {
    "level": "与 profile.preferred_difficulty 一致",
    "score": 0.5,
    "total_questions": 1,
    "correct": 0,
    "last_practiced": "<今天>",
    "weak_points": []
  }
}
```
```

---

### 任务 3：创建 evaluation-guide.md 评估标准

**文件：**
- 创建：`.claude/skills/interview-prep/evaluation-guide.md`

- [ ] **步骤 1：编写 evaluation-guide.md**

```markdown
# 评估标准

被 SKILL.md 引用，决定"怎么判分"。

## 评估等级

| 等级 | 判定标准 | 分数映射 |
|------|----------|----------|
| 熟练 | 回答覆盖核心要点 80%+，表述清晰准确 | 1.0 |
| 一般 | 答对主干但遗漏重要细节或边界情况 | 0.6 |
| 薄弱 | 核心概念理解有偏差，或大部分关键点未涉及 | 0.2 |

判定原则：
- 不要求与参考答案逐字一致，判断的是**理解程度**而非记忆准确度
- 行为面题目侧重 STAR 结构的完整性和具体性
- 如果用户回答过于简略（一两句话），可追问"能展开说说吗？"后再判定

## 简洁反馈模板（默认）

```
**判定：** <熟练/一般/薄弱>

<1-2 句关键遗漏点或亮点>
```

示例：

```
**判定：** 一般
遗漏了 flush timing 配置和副作用清理机制，这是实际项目中的重要细节。
```

如果回答评定为"熟练"：

```
**判定：** 熟练
回答全面，核心要点覆盖充分。
```

## 详细反馈模板（用户要求"详细"时展开）

```
## 评估：<熟练/一般/薄弱>

### 参考答案要点
1. <要点1>
2. <要点2>
3. <要点3>

### 你遗漏的关键点
- <遗漏点1> — <补充说明>
- <遗漏点2> — <补充说明>

### 改进建议
<1-2 句 actionable 建议>

### 延伸
> 想深入了解 <相关知识> 吗？我可以继续出题。
```

## 行为面评估

行为面题目额外检查 STAR 结构：

| 要素 | 检查点 |
|------|--------|
| S (情境) | 是否描述了具体背景？ |
| T (任务) | 是否说明了要解决什么问题？ |
| A (行动) | 是否描述了自己采取的具体行动？ |
| R (结果) | 是否有量化或可验证的成果？ |

反馈时特别指出缺失的要素。例如：

```
**判定：** 一般
情境和任务描述清楚，但行动部分太笼统（"我们团队做了XX"），
没有说清楚**你**具体做了什么。另外结果缺少量化数据。
```

## 回答摘要提取

评估后提取 1-2 句回答摘要写入 history：

- 用中文概括用户回答的核心内容
- 不评价，不对比参考答案
- 仅记录"用户说了什么"

示例：

- "回答了 watchEffect 和 watch 的基本区别，提到了 lazy 执行和依赖追踪，但未提到 flush timing"
- "描述了项目中的 Agent 架构，说明了事件驱动的选择原因，但缺少具体实现细节"

## 遗漏点提取

从用户回答中提取未覆盖的关键点，写入 missed_points：

- 每条 3-8 字，简洁具体
- 只记录技术层面的遗漏，不记录表达问题
- 多个遗漏点用数组表示

示例：

- `["flush timing 配置", "副作用清理"]`
- `["多 Agent 通信协议", "任务分配策略"]`

## 复习间隔管理

更新 history 记录中的 review_state：

| 当前状态 | 本次评估 | 更新后状态 |
|----------|----------|------------|
| 首次答题 | 薄弱/一般 | interval=1天, next_review=明天, consecutive=0 |
| 首次答题 | 熟练 | 不进入复习队列 |
| consecutive=0 | 薄弱/一般 | interval=1天（重置）, consecutive=0 |
| consecutive=0 | 熟练 | interval=3天, consecutive=1 |
| consecutive=1 | 薄弱/一般 | interval=1天（重置）, consecutive=0 |
| consecutive=1 | 熟练 | interval=7天, consecutive=2 |
| consecutive=2 | 薄弱/一般 | interval=1天（重置）, consecutive=0 |
| consecutive=2 | 熟练 | 从队列移除（标记已掌握） |

复习间隔规则的口诀：

```
首次答错 → 1 天后复习
答错后再错 → 仍 1 天后（重置）
答对一次 → 3 天后
连续答对两次 → 7 天后
连续答对三次 → 移出队列
```
```

---

### 任务 4：测试验证

**文件：**
- 无新文件（测试通过子代理运行场景）

- [ ] **步骤 1：基线场景 — 首次使用**

使用子代理运行场景，prompt：

> 你是一个求职者，正在准备面试。请说"帮我出几道面试题"。
> 预期行为：skill 应检测到 `~/.interview-prep/` 不存在，引导填写 profile，创建目录结构。

- [ ] **步骤 2：基线场景 — 单组出题**

使用子代理运行场景（前提：已初始化 profile），prompt：

> `/interview vue 中级`
> 预期行为：一次出 3-5 题，覆盖不同角度（概念、对比、应用、踩坑、设计），每题带角度标签。

- [ ] **步骤 3：基线场景 — 答题评估**

使用子代理运行场景（前提：已出题），prompt：

> （对某题给出部分正确但遗漏关键点的回答）
> 预期行为：判定"一般"，指出遗漏点，不展开详细反馈。回复"详细"后展开。

- [ ] **步骤 4：基线场景 — 模拟面试**

使用子代理运行场景，prompt：

> `/interview --mock 10`
> 预期行为：面试官角色，单题问答，由浅入深，结束时给评估报告。

- [ ] **步骤 5：基线场景 — 复习模式**

使用子代理运行场景（前提：history 中有 evaluation 为一般的记录），prompt：

> `/interview --review`
> 预期行为：筛选到期题目，换角度出题，更新间隔状态。

- [ ] **步骤 6：验证数据持久化**

检查 `~/.interview-prep/` 目录：
- `profile.json` 内容完整
- `ability-matrix.json` 维度有更新
- `history/` 下有对应日期的 jsonl 文件
- 答题记录格式正确（含 review_state）
```

---

### 任务 5：提交

- [ ] **步骤 1：提交 skill 文件到 git**

```bash
git add .claude/skills/interview-prep/
git commit -m "feat: add interview-prep skill — 自适应面试出题教练

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```
