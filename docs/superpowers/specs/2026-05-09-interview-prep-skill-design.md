# 面试出题 Skill 设计规格

## 概述

构建 `interview-prep` skill，为求职者提供自适应的面试练习功能。支持技术问答和行为面题目，基于能力画像自动调整出题策略，记忆用户的答题历史和薄弱点。

## 触发命令

| 命令 | 说明 |
|------|------|
| `/interview` | 自动选题，一次出 3-5 题（不同角度） |
| `/interview <维度> <难度>` | 指定维度和难度，如 `/interview vue 高级` |
| `/interview --jd <name>` | 基于已保存的 JD 出题 |
| `/interview --project` | 基于当前项目出题（可选模块） |
| `/interview --weak` | 专攻薄弱点 |
| `/interview --mock [时长]` | 模拟面试模式 |
| `/interview --review` | 复习模式 |
| `/interview --setup` | 初始化/修改用户画像 |

## 存储结构

所有数据存储于 `~/.interview-prep/`，跨项目通用：

```
~/.interview-prep/
├── profile.json          # 用户画像
├── ability-matrix.json   # 能力矩阵
├── history/
│   └── YYYY-MM-DD.jsonl  # 按日期追加的答题记录
├── jds/
│   └── *.md              # 保存的 JD 文件
└── sessions/
    └── YYYY-MM-DD-mock.md  # 模拟面试完整记录
```

### profile.json

```json
{
  "target_role": "全栈工程师（Agent方向）",
  "experience_years": 3,
  "tech_stack": ["Vue", "TypeScript", "Python", "LangChain", "FastAPI"],
  "focus_areas": ["agent-architecture", "prompt-engineering", "system-design"],
  "preferred_difficulty": "中级",
  "feedback_mode": "concise",
  "active_jd": null
}
```

### ability-matrix.json

```json
{
  "dimensions": {
    "vue": {
      "level": "中级",
      "score": 0.72,
      "total_questions": 15,
      "correct": 11,
      "last_practiced": "2026-05-08",
      "weak_points": ["composition API 高级用法", "性能优化"]
    }
  },
  "behavioral": {
    "score": 0.6,
    "weak_points": ["量化成果描述", "冲突处理场景"],
    "last_practiced": "2026-05-05"
  }
}
```

Score 为 0-1 的浮点数，基于近 N 次答题的加权平均（近期权重更高）。维度可动态增加。

### history/YYYY-MM-DD.jsonl

每行一条答题记录：

```json
{
  "id": "q-20260509-001",
  "timestamp": "2026-05-09T14:30:00",
  "mode": "single",
  "dimension": "vue",
  "difficulty": "中级",
  "question": "Vue3 的 watchEffect 和 watch 的区别是什么？什么场景下选择哪个？",
  "answer_summary": "回答了基本区别，但未提到 flush timing",
  "evaluation": "一般",
  "missed_points": ["flush timing 配置", "副作用清理"],
  "source": "jd:bytedance-fe",
  "review_state": {
    "interval_days": 1,
    "next_review": "2026-05-10",
    "consecutive_correct": 0
  }
}
```

## Skill 文件结构

```
.claude/skills/interview-prep/
├── SKILL.md              # 主入口：触发条件、核心流程、命令路由
├── question-engine.md    # 出题引擎策略规则
└── evaluation-guide.md   # 评估与反馈标准
```

## 交互流程

### 首次使用

1. 检测 `~/.interview-prep/` 不存在
2. 引导用户填写 profile：目标岗位、技术栈、工作年限、重点方向
3. 创建目录结构和初始化文件
4. 开始第一组题目

### 单组模式（默认）

1. 读取 profile + ability-matrix
2. 按出题策略选择维度和角度，生成 3-5 题
3. 一次性展示全部题目
4. 用户逐题作答
5. 每题评估（默认简洁判定：熟练/一般/薄弱 + 关键遗漏点）
6. 用户可选：对某题展开详细反馈 / 下一组 / 结束
7. 更新 ability-matrix + 写入 history

### 模拟面试模式

1. 读取 profile + JD + ability-matrix
2. 生成面试大纲（不展示）：
   - 开场寒暄（1min）
   - 项目深挖（10-15min）
   - 技术问答 3-5 题，由浅入深（15-20min）
   - 行为面 1-2 题（5-10min）
   - 反问环节提示
3. 以面试官角色连续对话，根据回答实时追问/转向
4. 结束后给出整体评估报告
5. 写入 sessions/ + 更新 ability-matrix

### 复习模式

1. 从 history 筛选 evaluation 为"一般"或"薄弱"的题目
2. 按间隔重复排序，取 3-5 题
3. 换角度重新出题（不原题重出，避免背答案）
4. 评估 + 更新间隔状态
5. 连续答对三次从复习队列移除

### 间隔重复规则

| 状态 | 间隔 |
|------|------|
| 首次答错 | 1 天后复习 |
| 第二次仍错 | 1 天后复习 |
| 答对一次 | 3 天后复习 |
| 连续答对两次 | 7 天后复习 |
| 连续答对三次 | 从队列移除，标记"已掌握" |

### 详细反馈

用户要求详细反馈时展开，包含：
- 参考答案要点
- 用户遗漏的关键点
- 改进建议
- 相关延伸知识点（可选提问"要深入了解这个吗？"）

## 出题引擎

### 出题策略优先级

1. **用户显式指定** — 维度/难度直接遵循
2. **JD 驱动** — active_jd 中提到的技术点 ∩ 能力矩阵低分区
3. **遗忘曲线** — 超过 7 天未练且 score < 0.7 的维度优先
4. **薄弱点深挖** — weak_points 中频次最高的点，换角度再考
5. **均衡覆盖** — 练习次数最少的维度

### 难度自适应

| 当前维度 score | 动作 |
|----------------|------|
| >= 0.8 | 升一级难度 |
| 0.5 - 0.8 | 保持当前难度 |
| < 0.5 | 降一级，侧重基础巩固 |

### 3-5 题角度分配

每组从以下角度中选择 3-5 个（根据维度和难度匹配）：

| 角度 | 说明 |
|------|------|
| 概念理解 | 解释核心概念和原理 |
| 对比分析 | 相似技术/方案的对比选择 |
| 实践应用 | 具体场景下的用法和配置 |
| 踩坑经验 | 常见问题和边界情况处理 |
| 系统设计 | 架构决策和扩展性考量 |

### 矩阵更新算法

```
evaluation → 分数映射：熟练=1.0, 一般=0.6, 薄弱=0.2
new_score = old_score × 0.7 + this_score × 0.3
missed_points → 合并到 weak_points（重复出现权重+1）
last_practiced → 更新为当前日期
```

### 反馈模式

- **简洁（默认）：** 判定等级 + 1-2 句关键遗漏点
- **详细（按需展开）：** 参考答案 + 遗漏点详解 + 改进建议 + 延伸方向

## 题目类型

### 技术问答

- 概念原理（"解释 X 是什么"）
- 对比分析（"X vs Y，各自适用场景"）
- 实践应用（"如何配置/实现 X"）
- 踩坑经验（"X 出问题时怎么排查"）
- 系统设计（"设计一个 X，关键考虑点"）
- 性能优化（"X 慢了你如何优化"）

### 行为面

- 项目经历（STAR 法则导向）
- 团队协作与冲突处理
- 技术决策与 trade-off
- 失败/教训复盘
- 职业动机与发展规划

### 不包含

- 手写代码题（不在本次范围）

## 难度体系

| 等级 | 对标 | 特征 |
|------|------|------|
| 初级 | 1-3 年 | 基础概念、常规用法、标准场景 |
| 中级 | 3-5 年 | 原理理解、方案选型、性能优化、踩坑经验 |
| 高级 | 5 年+ | 架构设计、系统权衡、技术决策、跨领域整合 |

## 项目分析模块（可选）

### 触发

在项目目录中使用 `/interview --project` 时激活。

### 分析范围

- 技术栈：从 package.json / requirements.txt / 配置文件推断
- 架构模式：目录结构、核心模块划分
- 关键设计决策：从代码结构识别
- **设计文档视同已实现：** 扫描 `docs/` 下的规格说明和设计文档，其描述的功能视为用户的已实现经验
- 用户贡献：通过 git log 识别主要负责的模块

### 题目类型

| 类型 | 示例 |
|------|------|
| 设计决策 | "你的 orchestrator 为什么用事件驱动？" |
| 深挖实现 | "这个 memory 系统的持久化策略怎么考虑的？" |
| 假设变更 | "如果并发量增加 10 倍，架构哪里先出问题？" |
| 复盘改进 | "如果重新做这个模块，你会改什么？" |

### 与行为面结合

- "这个项目中遇到的最大技术挑战是什么？怎么解决的？"
- "团队中有人对你的架构方案有异议，你怎么处理的？"

### 限制

- 只读分析，不修改项目文件
- 不在 `~/.interview-prep/` 中存储项目代码内容，只存分析摘要
- 可通过 `--no-project` 显式关闭

## Skill 触发条件

### 描述（CSO 优化）

```
面试准备：出题练习、模拟面试、薄弱点复习。支持技术问答和行为面题目，基于能力画像自适应调整难度。Use when user: 准备面试、要求出题、模拟面试、评估技术掌握程度、复习知识点。
```

### 触发关键词

面试、出题、模拟面试、mock interview、复习、查漏补缺、技术面、行为面、JD分析、项目深挖

## 边界与限制

- 不生成手写代码题
- 数据仅本地存储，不联网
- 项目分析模式下对项目只读
- 单次出题 3-5 题，模拟面试可更长
- 首次使用必须完成 profile 初始化
