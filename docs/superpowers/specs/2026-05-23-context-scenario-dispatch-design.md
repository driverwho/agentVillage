# 上下文场景分流设计

> 日期：2026-05-23
> 状态：设计中
> 范围：最小改动（仅 context_builder.py + 调用方传参）

## 背景

当前 `ContextBuilder.build()` 无论什么场景都组装全部 6 层（L0-L5）。自主决策场景中，L3（对方信息）输出"你正在与某人对话"造成干扰，L5（对话历史）为空但仍走拼装逻辑，L4（记忆检索）加载了不需要的 user.md。

## 目标

- NPC 自主决策时不加载对话相关上下文，减少 token 浪费和模型干扰
- NPC 间互动时加载关系记忆但不加载玩家记忆
- 玩家对话时保持现有行为不变
- 最小改动，向后兼容

## 设计

### 1. 新增 ScenarioType 枚举

位置：`server/llm/context_builder.py` 顶部

```python
from enum import Enum

class ScenarioType(Enum):
    AUTONOMOUS_DECISION = "autonomous"
    PLAYER_DIALOGUE = "dialogue"
    NPC_INTERACTION = "npc_interaction"
```

### 2. 场景配置表

```python
SCENARIO_LAYERS = {
    ScenarioType.AUTONOMOUS_DECISION: {
        "L3": False,
        "L4_scope": "agent_only",   # 只加载 agent_mem.md
        "L5": False,
    },
    ScenarioType.PLAYER_DIALOGUE: {
        "L3": True,
        "L4_scope": "full",         # 加载全部记忆文件
        "L5": True,
    },
    ScenarioType.NPC_INTERACTION: {
        "L3": True,
        "L4_scope": "agent_only",   # 只加载 agent_mem.md（关系记忆）
        "L5": True,
    },
}
```

说明：
- L0（身份）、L1（世界）、L2（自身状态）所有场景都需要，不纳入配置
- `L4_scope` 控制传给 `_build_layer_4` 的 memory_files 子集
  - `"full"`: 传入所有 memory_files（user.md + agent_mem.md + background knowledge）
  - `"agent_only"`: 只保留 key 包含 "agent_mem" 的文件

### 3. BuildParams 新增字段

```python
@dataclass
class BuildParams:
    scenario: ScenarioType = ScenarioType.PLAYER_DIALOGUE  # 默认值保证向后兼容
    identity: dict
    npc_state: any = None
    world_state: dict = field(default_factory=dict)
    interlocutor: dict = field(default_factory=dict)
    memory_files: dict = field(default_factory=dict)
    dialogue_history: List[dict] = field(default_factory=list)
    current_input: str = ""
    background: dict = field(default_factory=dict)
```

### 4. build() 方法改动

在 `build()` 中根据 scenario 配置决定是否构建某层：

```python
def build(self, params: BuildParams) -> BuildResult:
    config = SCENARIO_LAYERS[params.scenario]
    
    # ... L0, L1, L2 不变 ...

    # L3: 条件构建
    if config["L3"]:
        l3 = self._build_layer_3(params.interlocutor, bg)
    else:
        l3 = LayerResult(content="", tokens=0)

    # L4: 根据 scope 过滤 memory_files
    filtered_files = self._filter_memory_scope(params.memory_files, config["L4_scope"])
    l4_content, l4_meta = self._build_layer_4(params.current_input, filtered_files, bg)

    # L5: 条件构建
    if config["L5"]:
        l5_result = self._build_layer_5(params.dialogue_history, params.current_input, remaining)
    else:
        # 仅保留 current_input 作为 user message（触发工具选择）
        input_tokens = TokenCounter.count(params.current_input)
        l5_result = LayerResult(
            content=[{"role": "user", "content": params.current_input}],
            tokens=input_tokens,
        )
    
    # ... 组装和校验不变 ...
```

### 5. 新增辅助方法

```python
def _filter_memory_scope(self, memory_files: dict, scope: str) -> dict:
    if scope == "full":
        return memory_files
    if scope == "agent_only":
        return {k: v for k, v in memory_files.items() if "agent_mem" in k}
    return memory_files
```

### 6. 调用方改动

**orchestrator.py `_single_autonomous_turn`**（约第 194 行）：

```python
params = BuildParams(
    scenario=ScenarioType.AUTONOMOUS_DECISION,  # 新增
    identity=npc.identity,
    npc_state=npc.state,
    world_state=world_state,
    interlocutor={},
    memory_files={"agent_mem.md": npc.memory._read("agent_mem.md")},
    dialogue_history=[],
    current_input=autonomous_input,
    background=npc.background,
)
```

**routes.py `_build_messages`**（约第 45 行）：

```python
params = BuildParams(
    scenario=ScenarioType.PLAYER_DIALOGUE,  # 新增（等同默认值，显式声明）
    identity=npc.identity,
    # ... 其余不变
)
```

**未来 NPC 互动调用点**（gossip/trade 工具执行时）：

```python
params = BuildParams(
    scenario=ScenarioType.NPC_INTERACTION,
    identity=npc.identity,
    interlocutor={"name": target_npc.identity["name"], "id": target_npc.agent_id},
    memory_files={"agent_mem.md": npc.memory._read("agent_mem.md")},
    # ...
)
```

## 行为对比

| 场景 | 改动前 | 改动后 |
|------|--------|--------|
| 自主决策 | L3 输出"你正在与某人对话"，L5 空数组走拼装 | L3 跳过，L5 只保留 current_input |
| 玩家对话 | 全部加载 | 行为不变 |
| NPC 互动 | 未实现 | L3 填入对方 NPC 信息，L4 只检索关系记忆 |

## 向后兼容

- `BuildParams.scenario` 默认值为 `PLAYER_DIALOGUE`，未传 scenario 的现有代码行为不变
- `_filter_memory_scope` 对未知 scope 值 fallback 到返回全部文件
- 不改动 MemoryManager、工具系统、agent 基类

## 设计决策备注

- `_build_layer_4` 内部会从 `background.dialogue_topics` 注入合成记忆。自主决策场景中这些对话话题不会被 keyword retriever 匹配到（trigger 是工具选择指令），因此无需额外过滤。如果未来 retriever 升级为语义匹配，需要重新审视此处。

## 不做的事

- 不引入模型驱动的记忆路由（记忆文件少，hardcode 足够）
- 不改 MemoryManager 接口
- 不新增文件（所有改动在现有文件内）
