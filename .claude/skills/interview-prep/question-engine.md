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
