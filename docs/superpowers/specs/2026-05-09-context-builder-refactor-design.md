# ContextBuilder 重构设计

基于 `2026-05-08-context-management-design.md` 的 6 层上下文架构，对 `server/llm/context_builder.py` 进行完整重构。

## 1. 目标

将当前 48 行的字符串拼接式 `ContextBuilder` 重构为符合设计文档的 6 层上下文组装管道，增加 Token 配额管理、记忆检索、对话压缩、审计日志和熔断机制。

## 2. 文件结构

```
server/llm/
  ├── context_builder.py      # 主类（~300 行），6 层管道编排
  ├── token_counter.py        # Token 计数工具（新增）
  ├── memory_retriever.py     # 记忆检索抽象 + 简单实现（新增）
  ├── context_audit.py        # 审计日志（新增）
  └── client.py               # 不变
```

原则：核心逻辑集中在 context_builder.py，Token 计数、记忆检索、审计日志三个可独立替换的模块抽出去。

## 3. 核心接口

### 3.1 数据结构

```python
@dataclass
class ContextConfig:
    model_limit: int = 4096        # 模型上下文上限（环境变量 LLM_CONTEXT_LIMIT）
    output_reserve: int = 500      # 预留输出空间
    compress_threshold: int = 10   # 对话超过此轮数触发压缩
    tired_threshold: int = 200     # 剩余 token 低于此值触发疲倦模式
    decay_rate: float = 0.05       # 记忆时间衰减率

@dataclass
class BuildParams:
    identity: dict                 # NPC 角色设定
    npc_state: NPCState            # 自身状态
    world_state: dict              # 世界状态（时间/天气/事件）
    interlocutor: dict             # 交互对象可见信息（Orchestrator 已过滤）
    memory_files: dict             # {user.md, self.md, agent_mem.md, world.md}
    dialogue_history: list[dict]   # 对话历史
    current_input: str             # 当前玩家输入

@dataclass
class LayerResult:
    content: str | list[dict]      # 该层产出的文本或消息列表
    tokens: int                    # 消耗的 token 数
    truncated: bool = False        # 是否触发截断
    errors: list[str] = field(default_factory=list)

@dataclass
class BuildResult:
    messages: list[dict]           # 最终发给 LLM 的消息列表
    audit: dict                    # 每层统计 {layer, tokens, truncated, ...}
    budget_status: str             # normal | warning | tired
```

### 3.2 主入口

```python
class ContextBuilder:
    def __init__(self, config: ContextConfig | None = None, 
                 retriever: MemoryRetriever | None = None):
        ...

    def build(self, params: BuildParams) -> BuildResult:
        """执行 7 步管道，返回最终消息列表和审计信息"""
```

## 4. 六层组装管道

7 步执行（Layer 0-5 + 最终校验），每步有校验点，配额超出触发截断。

### 4.1 Layer 0 — 不可变核心（30%）

- 组装 NPC 角色设定：name + daily_habits + core_motivation + speaking_style + secret
- Checksum 校验：首次调用时 `hash(frozenset(identity.items()))`，后续比对
- 校验失败 → 熔断该 NPC 当前轮次
- 超配额 → 不可截断，触发熔断

### 4.2 Layer 1 — 世界注入（5%）

- 当前时间（Day + Hour）、天气、近期全局事件
- 由 Orchestrator 广播统一注入
- 超配额 → 截断事件描述文本

### 4.3 Layer 2 — 自身状态（5%）

- 复用 `NPCState.describe()`：health + hunger + fatigue + mood
- 只注入自然语言映射，不暴露数值
- 超配额 → 截断（保留 health 和 mood，丢弃 hunger 和 fatigue）

### 4.4 Layer 3 — 交互对象上下文（10%）

- 对方名称 + 对方可见状态 + 与该 NPC 的关系摘要
- 数据已由 Orchestrator 在上游按权限过滤，此处只格式化
- 不做跨 NPC 敏感信息扫描（隔离由架构保证）
- 超配额 → 截断关系摘要文本

### 4.5 Layer 4 — 记忆检索（25%）

接口：

```python
class MemoryRetriever(ABC):
    @abstractmethod
    def retrieve(self, trigger: str, files: dict, max_tokens: int) -> tuple[str, list]:
        ...
```

当前实现 `SimpleKeywordRetriever`：
- 固定加载：self.md 最近 3 条摘要 + user.md 顶部 200 字
- 动态检索：从 trigger 提取关键词 → 匹配记忆文件段落 → 权重排序 → 取前 K 条
- 权重公式：`score = match_score × e^(-0.05 × age_days) × importance`
- 超配额 → 按 score 降序逐条加入，累计 token 接近配额时停止

### 4.6 Layer 5 — 活跃对话（25%，弹性）

Token 计算顺序：
1. 累计 Layer 0-4 Token → `T_used`
2. `T_remaining = model_limit - T_used - output_reserve`
3. 保留当前输入 → 从最新轮次往前取历史 → 直到 token 用尽

截断优先级：

| 优先级 | 内容 | 规则 |
|--------|------|------|
| 1 | 当前玩家输入 | 永不丢弃 |
| 2 | 最近 3 轮 | 保证连续性 |
| 3 | 3 轮以外 | 从最早开始丢弃 |
| 4 | 超过 10 轮 | 压缩前 N 轮为摘要 |

对话压缩（compress，后续升级为 compact）：
- Prompt："将以下对话压缩为一段 100 字以内的摘要，保留关键信息和人物态度。"
- 压缩结果作为 system 消息插入对话历史之前

疲倦模式：
- 触发：`T_remaining < tired_threshold(200)`
- Layer 0 追加"请简短回复，不超过一句话"
- 返回 `budget_status: "tired"`，调用方可用预设模板替代 LLM 调用

## 5. 最终校验

1. 注入关键词过滤：扫描 "ignore previous"、"system prompt" 等注入攻击关键词
2. Token 总数确认：不超过 `model_limit - output_reserve`
3. 异常 → 剥离 → 重新组装

不做跨 NPC 敏感信息扫描 —— 隔离由架构保证。

## 6. 审计日志

路径：`logs/context/{npc_id}/{timestamp}.md`

格式：每层单独列出（内容 + token 数），末尾统计总量、截断状态、压缩状态、预算状态。

写入方式：异步后台任务（`asyncio.create_task`），不阻塞 LLM 调用响应。

## 7. 熔断策略

| 异常 | 处理 |
|------|------|
| Layer 0 checksum 失败 | NPC 当前轮次熔断，返回通用回复 |
| Layer 4 检索超配额 | 截断结果，告警日志标记 |
| Layer 5 Token 溢出 | 回退 3 轮重新计算，仍失败则压缩 |
| 最终校验异常 | 剥离异常内容，重新组装 |
| LLM 调用异常 | 重试 1 次；仍失败返回通用回复 |
| 连续 3 次调用失败 | 熔断该 NPC 直到下一游戏小时 |

## 8. Token 计数

字符近似法：

```python
chinese_chars / 1.5 + other_chars / 4
```

### 8.1 配额比例

| 层 | 比例 | 硬/弹性 |
|----|------|---------|
| L0 | 30% | 硬（不可截断，超即熔断） |
| L1 | 5% | 硬 |
| L2 | 5% | 硬 |
| L3 | 10% | 硬 |
| L4 | 25% | 硬 |
| L5 | 25% | 弹性（用满剩余） |

## 9. 配置项

| 配置 | 默认值 | 环境变量 |
|------|--------|---------|
| model_limit | 4096 | `LLM_CONTEXT_LIMIT` |
| output_reserve | 500 | `LLM_OUTPUT_RESERVE` |
| compress_threshold | 10 | — |
| tired_threshold | 200 | — |
| decay_rate | 0.05 | — |

## 10. 与 routes.py 的集成

```python
builder = ContextBuilder(config)
result = builder.build(BuildParams(...))

if result.budget_status == "tired":
    return {"reply": FALLBACK_REPLIES[npc_id], "options": []}

asyncio.create_task(audit_logger.write(npc_id, result.audit))
resp = await client.chat_with_retry(result.messages)
```

## 11. 变更范围

| 文件 | 变更 |
|------|------|
| `server/llm/context_builder.py` | 重写：48 行 → ~300 行 |
| `server/llm/token_counter.py` | 新增 |
| `server/llm/memory_retriever.py` | 新增（抽象类 + SimpleKeywordRetriever） |
| `server/llm/context_audit.py` | 新增 |
| `server/api/routes.py` | 修改：适配新接口，增加疲倦模式路由 |
| `tests/server/test_context_builder.py` | 重写：对应 6 层各层测试 |

## 12. 后续扩展点

- `compress` → `compact`：对话压缩升级为标准 compact 方法
- `SimpleKeywordRetriever` → `JiebaRetriever`：中文分词检索
- `MemoryRetriever` → 向量检索：嵌入 embedding 检索
- 字符近似 Token → tiktoken 精确计数
