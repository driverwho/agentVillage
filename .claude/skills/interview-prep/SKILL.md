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
2. 逐项询问（每次一个问题），填写 profile.json：
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
2. 读取 `question-engine.md`（本 skill 目录下），按出题策略选择维度和角度
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
5. 每题作答后，读取 `evaluation-guide.md`（本 skill 目录下）评估：
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
5. 反问环节结束后做简短收尾（"感谢你的时间，我会基于整体表现给出评估"），然后给出评估报告，包含：
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

- **出题策略细节** → 读取 `question-engine.md`（本 skill 目录下）
- **评估标准与反馈模板** → 读取 `evaluation-guide.md`（本 skill 目录下）
- 在需要做出题决策或评分时，必须读取对应子文件
