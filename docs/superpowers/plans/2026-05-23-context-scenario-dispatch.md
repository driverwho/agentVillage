# 上下文场景分流 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 让 ContextBuilder 根据场景类型（自主决策/玩家对话/NPC互动）跳过不需要的上下文层，减少 token 浪费和模型干扰。

**架构：** 新增 ScenarioType 枚举和 SCENARIO_LAYERS 配置表，BuildParams 加 scenario 字段，build() 方法根据配置条件性构建 L3/L4/L5 层。调用方传入场景类型。

**技术栈：** Python 3.11, pytest, dataclasses, enum

---

## 文件结构

| 文件 | 职责 | 操作 |
|------|------|------|
| `server/llm/context_builder.py` | 上下文组装管道 | 修改：加枚举、配置表、条件分支、辅助方法 |
| `server/core/orchestrator.py` | 自主决策调度 | 修改：BuildParams 传入 scenario |
| `server/api/routes.py` | 对话路由 | 修改：BuildParams 传入 scenario |
| `tests/server/test_context_builder.py` | ContextBuilder 测试 | 修改：新增场景分流测试 |

---

## 任务 1：新增 ScenarioType 枚举和 SCENARIO_LAYERS 配置（TDD）

**文件：**
- 修改：`server/llm/context_builder.py:1-5`
- 测试：`tests/server/test_context_builder.py`

- [ ] **步骤 1：编写测试验证枚举和配置表存在**

在 `tests/server/test_context_builder.py` 末尾新增：

```python
class TestScenarioDispatch:
    """验证场景分流机制"""

    def test_scenario_type_enum_exists(self):
        from server.llm.context_builder import ScenarioType
        assert ScenarioType.AUTONOMOUS_DECISION.value == "autonomous"
        assert ScenarioType.PLAYER_DIALOGUE.value == "dialogue"
        assert ScenarioType.NPC_INTERACTION.value == "npc_interaction"

    def test_scenario_layers_config(self):
        from server.llm.context_builder import ScenarioType, SCENARIO_LAYERS
        # 自主决策不需要 L3 和 L5
        auto_cfg = SCENARIO_LAYERS[ScenarioType.AUTONOMOUS_DECISION]
        assert auto_cfg["L3"] is False
        assert auto_cfg["L5"] is False
        assert auto_cfg["L4_scope"] == "agent_only"
        # 玩家对话全部开启
        dlg_cfg = SCENARIO_LAYERS[ScenarioType.PLAYER_DIALOGUE]
        assert dlg_cfg["L3"] is True
        assert dlg_cfg["L5"] is True
        assert dlg_cfg["L4_scope"] == "full"
        # NPC 互动
        npc_cfg = SCENARIO_LAYERS[ScenarioType.NPC_INTERACTION]
        assert npc_cfg["L3"] is True
        assert npc_cfg["L5"] is True
        assert npc_cfg["L4_scope"] == "agent_only"
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd d:/work_ai/agentVillage && python -m pytest tests/server/test_context_builder.py::TestScenarioDispatch -v`
预期：FAIL，ImportError: cannot import name 'ScenarioType'

- [ ] **步骤 3：实现 ScenarioType 和 SCENARIO_LAYERS**

在 `server/llm/context_builder.py` 文件顶部（第 1 行之前）插入：

```python
from enum import Enum


class ScenarioType(Enum):
    AUTONOMOUS_DECISION = "autonomous"
    PLAYER_DIALOGUE = "dialogue"
    NPC_INTERACTION = "npc_interaction"


SCENARIO_LAYERS = {
    ScenarioType.AUTONOMOUS_DECISION: {
        "L3": False,
        "L4_scope": "agent_only",
        "L5": False,
    },
    ScenarioType.PLAYER_DIALOGUE: {
        "L3": True,
        "L4_scope": "full",
        "L5": True,
    },
    ScenarioType.NPC_INTERACTION: {
        "L3": True,
        "L4_scope": "agent_only",
        "L5": True,
    },
}
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd d:/work_ai/agentVillage && python -m pytest tests/server/test_context_builder.py::TestScenarioDispatch -v`
预期：2 tests PASSED

- [ ] **步骤 5：Commit**

```bash
git add server/llm/context_builder.py tests/server/test_context_builder.py
git commit -m "feat(context): 新增 ScenarioType 枚举和 SCENARIO_LAYERS 配置表"
```

---

## 任务 2：BuildParams 新增 scenario 字段（TDD）

**文件：**
- 修改：`server/llm/context_builder.py:10-19`（BuildParams dataclass）
- 测试：`tests/server/test_context_builder.py`

- [ ] **步骤 1：编写测试验证 BuildParams 接受 scenario 参数**

在 `tests/server/test_context_builder.py` 的 `TestScenarioDispatch` 类中追加：

```python
    def test_build_params_default_scenario(self):
        from server.llm.context_builder import BuildParams, ScenarioType
        p = BuildParams(
            identity={"name": "测试"},
            npc_state=None,
            world_state={},
            interlocutor={},
            memory_files={},
            dialogue_history=[],
            current_input="你好",
        )
        assert p.scenario == ScenarioType.PLAYER_DIALOGUE

    def test_build_params_explicit_scenario(self):
        from server.llm.context_builder import BuildParams, ScenarioType
        p = BuildParams(
            scenario=ScenarioType.AUTONOMOUS_DECISION,
            identity={"name": "测试"},
            npc_state=None,
            world_state={},
            interlocutor={},
            memory_files={},
            dialogue_history=[],
            current_input="选择工具",
        )
        assert p.scenario == ScenarioType.AUTONOMOUS_DECISION
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd d:/work_ai/agentVillage && python -m pytest tests/server/test_context_builder.py::TestScenarioDispatch::test_build_params_default_scenario -v`
预期：FAIL，TypeError: unexpected keyword argument 'scenario'

- [ ] **步骤 3：修改 BuildParams dataclass**

将 `server/llm/context_builder.py` 中的 BuildParams 改为：

```python
@dataclass
class BuildParams:
    identity: dict
    npc_state: any = None
    world_state: dict = field(default_factory=dict)
    interlocutor: dict = field(default_factory=dict)
    memory_files: dict = field(default_factory=dict)
    dialogue_history: List[dict] = field(default_factory=list)
    current_input: str = ""
    background: dict = field(default_factory=dict)
    scenario: "ScenarioType" = None

    def __post_init__(self):
        if self.scenario is None:
            self.scenario = ScenarioType.PLAYER_DIALOGUE
```

注意：scenario 放在有默认值的字段中（末尾），用 `__post_init__` 处理默认值赋值以兼容 Python dataclass 字段顺序规则。

- [ ] **步骤 4：运行测试验证通过**

运行：`cd d:/work_ai/agentVillage && python -m pytest tests/server/test_context_builder.py::TestScenarioDispatch -v`
预期：4 tests PASSED

- [ ] **步骤 5：运行全部现有测试确认不破坏**

运行：`cd d:/work_ai/agentVillage && python -m pytest tests/server/test_context_builder.py -v`
预期：ALL PASSED（现有测试不传 scenario，走默认值）

- [ ] **步骤 6：Commit**

```bash
git add server/llm/context_builder.py tests/server/test_context_builder.py
git commit -m "feat(context): BuildParams 新增 scenario 字段，默认 PLAYER_DIALOGUE"
```

---

## 任务 3：新增 _filter_memory_scope 辅助方法（TDD）

**文件：**
- 修改：`server/llm/context_builder.py`（ContextBuilder 类内）
- 测试：`tests/server/test_context_builder.py`

- [ ] **步骤 1：编写测试**

在 `TestScenarioDispatch` 类中追加：

```python
    def test_filter_memory_scope_full(self):
        builder = ContextBuilder(model_limit=4096)
        files = {"agent_mem.md": "关系数据", "user.md": "玩家印象", "self.md": "自我认知"}
        result = builder._filter_memory_scope(files, "full")
        assert result == files

    def test_filter_memory_scope_agent_only(self):
        builder = ContextBuilder(model_limit=4096)
        files = {"agent_mem.md": "关系数据", "user.md": "玩家印象", "self.md": "自我认知"}
        result = builder._filter_memory_scope(files, "agent_only")
        assert "agent_mem.md" in result
        assert "user.md" not in result
        assert "self.md" not in result

    def test_filter_memory_scope_unknown_fallback(self):
        builder = ContextBuilder(model_limit=4096)
        files = {"agent_mem.md": "x", "user.md": "y"}
        result = builder._filter_memory_scope(files, "unknown_scope")
        assert result == files
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd d:/work_ai/agentVillage && python -m pytest tests/server/test_context_builder.py::TestScenarioDispatch::test_filter_memory_scope_full -v`
预期：FAIL，AttributeError: 'ContextBuilder' object has no attribute '_filter_memory_scope'

- [ ] **步骤 3：实现 _filter_memory_scope**

在 `server/llm/context_builder.py` 的 ContextBuilder 类中（`_build_layer_4` 方法之前）添加：

```python
    def _filter_memory_scope(self, memory_files: dict, scope: str) -> dict:
        """根据场景过滤记忆文件子集。"""
        if scope == "full":
            return memory_files
        if scope == "agent_only":
            return {k: v for k, v in memory_files.items() if "agent_mem" in k}
        return memory_files
```

- [ ] **步骤 4：运行测试验证通过**

运行：`cd d:/work_ai/agentVillage && python -m pytest tests/server/test_context_builder.py::TestScenarioDispatch -v`
预期：7 tests PASSED

- [ ] **步骤 5：Commit**

```bash
git add server/llm/context_builder.py tests/server/test_context_builder.py
git commit -m "feat(context): 新增 _filter_memory_scope 辅助方法"
```

---

## 任务 4：build() 方法接入场景分流逻辑（TDD）

**文件：**
- 修改：`server/llm/context_builder.py:106-162`（build 方法）
- 测试：`tests/server/test_context_builder.py`

- [ ] **步骤 1：编写测试验证自主决策场景跳过 L3 和 L5**

在 `TestScenarioDispatch` 类中追加：

```python
    def test_build_autonomous_skips_l3(self):
        """自主决策场景不应包含'对方信息'"""
        from server.models.npc_state import NPCState
        from server.llm.context_builder import ScenarioType
        builder = ContextBuilder(model_limit=4096)
        params = BuildParams(
            scenario=ScenarioType.AUTONOMOUS_DECISION,
            identity={
                "name": "农夫", "daily_habits": "种地",
                "core_motivation": "活着", "speaking_style": "朴实",
                "secret": "无",
            },
            npc_state=NPCState(),
            world_state={"day": 1, "hour": 8, "weather": "晴", "events": "无"},
            interlocutor={},
            memory_files={"agent_mem.md": "与酒保关系不错"},
            dialogue_history=[],
            current_input="【行动指令】\n请选择工具。",
            background={},
        )
        result = builder.build(params)
        all_text = " ".join(m.get("content", "") for m in result.messages)
        assert "【对方信息】" not in all_text
        assert "某人" not in all_text

    def test_build_autonomous_l5_only_current_input(self):
        """自主决策场景 L5 只保留 current_input，不走对话历史拼装"""
        from server.models.npc_state import NPCState
        from server.llm.context_builder import ScenarioType
        builder = ContextBuilder(model_limit=4096)
        params = BuildParams(
            scenario=ScenarioType.AUTONOMOUS_DECISION,
            identity={
                "name": "农夫", "daily_habits": "种地",
                "core_motivation": "活着", "speaking_style": "朴实",
                "secret": "无",
            },
            npc_state=NPCState(),
            world_state={"day": 1, "hour": 8, "weather": "晴", "events": "无"},
            interlocutor={},
            memory_files={"agent_mem.md": ""},
            dialogue_history=[
                {"role": "user", "content": "这条不该出现"},
            ],
            current_input="【行动指令】\n请选择工具。",
            background={},
        )
        result = builder.build(params)
        all_text = " ".join(m.get("content", "") for m in result.messages)
        assert "这条不该出现" not in all_text
        assert "请选择工具" in all_text

    def test_build_autonomous_l4_filters_memory(self):
        """自主决策场景 L4 只检索 agent_mem，不检索 user.md"""
        from server.models.npc_state import NPCState
        from server.llm.context_builder import ScenarioType
        builder = ContextBuilder(model_limit=4096)
        params = BuildParams(
            scenario=ScenarioType.AUTONOMOUS_DECISION,
            identity={
                "name": "农夫", "daily_habits": "种地",
                "core_motivation": "活着", "speaking_style": "朴实",
                "secret": "无",
            },
            npc_state=NPCState(),
            world_state={"day": 1, "hour": 8, "weather": "晴", "events": "无"},
            interlocutor={},
            memory_files={
                "agent_mem.md": "与酒保关系密切，经常一起喝酒",
                "user.md": "玩家是个好人，信任等级5",
            },
            dialogue_history=[],
            current_input="请选择工具",
            background={},
        )
        result = builder.build(params)
        all_text = " ".join(m.get("content", "") for m in result.messages)
        # user.md 内容不应出现在记忆检索中
        assert "玩家是个好人" not in all_text

    def test_build_player_dialogue_unchanged(self):
        """玩家对话场景行为与改动前一致"""
        from server.models.npc_state import NPCState
        from server.llm.context_builder import ScenarioType
        builder = ContextBuilder(model_limit=4096)
        params = BuildParams(
            scenario=ScenarioType.PLAYER_DIALOGUE,
            identity={
                "name": "农夫", "daily_habits": "种地",
                "core_motivation": "活着", "speaking_style": "朴实",
                "secret": "无",
            },
            npc_state=NPCState(),
            world_state={"day": 1, "hour": 8, "weather": "晴", "events": "无"},
            interlocutor={"name": "玩家", "summary": "一个旅行者"},
            memory_files={"agent_mem.md": "", "user.md": "信任等级3"},
            dialogue_history=[
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": "你好啊"},
            ],
            current_input="最近怎么样？",
            background={},
        )
        result = builder.build(params)
        all_text = " ".join(m.get("content", "") for m in result.messages)
        assert "【对方信息】" in all_text
        assert "玩家" in all_text
        assert "你好" in all_text or "最近怎么样" in all_text

    def test_build_npc_interaction(self):
        """NPC 互动场景加载 L3 但 L4 只用 agent_mem"""
        from server.models.npc_state import NPCState
        from server.llm.context_builder import ScenarioType
        builder = ContextBuilder(model_limit=4096)
        params = BuildParams(
            scenario=ScenarioType.NPC_INTERACTION,
            identity={
                "name": "农夫", "daily_habits": "种地",
                "core_motivation": "活着", "speaking_style": "朴实",
                "secret": "无",
            },
            npc_state=NPCState(),
            world_state={"day": 1, "hour": 8, "weather": "晴", "events": "无"},
            interlocutor={"name": "酒保", "id": "bartender"},
            memory_files={
                "agent_mem.md": "与酒保经常交换八卦",
                "user.md": "玩家喜欢钓鱼",
            },
            dialogue_history=[],
            current_input="嘿，酒保，最近有什么新闻？",
            background={},
        )
        result = builder.build(params)
        all_text = " ".join(m.get("content", "") for m in result.messages)
        assert "【对方信息】" in all_text
        assert "酒保" in all_text
        # user.md 不应出现
        assert "玩家喜欢钓鱼" not in all_text
```

- [ ] **步骤 2：运行测试验证失败**

运行：`cd d:/work_ai/agentVillage && python -m pytest tests/server/test_context_builder.py::TestScenarioDispatch::test_build_autonomous_skips_l3 -v`
预期：FAIL（当前 build() 不读取 scenario，L3 仍然输出）

- [ ] **步骤 3：修改 build() 方法**

将 `server/llm/context_builder.py` 中 `build()` 方法修改为：

在 `def build(self, params: BuildParams) -> BuildResult:` 方法体开头（`from server.llm.token_counter import TokenCounter` 之后）加入：

```python
        scenario_config = SCENARIO_LAYERS[params.scenario]
```

将 L3 构建段（原来直接调用 `self._build_layer_3`）改为：

```python
        # Step 2-4: Layers 1-3
        l1 = self._build_layer_1(params.world_state, bg)
        audit["L1"] = {"tokens": l1.tokens, "truncated": l1.truncated}
        l2 = self._build_layer_2(params.npc_state, bg)
        audit["L2"] = {"tokens": l2.tokens, "truncated": l2.truncated}

        if scenario_config["L3"]:
            l3 = self._build_layer_3(params.interlocutor, bg)
        else:
            l3 = LayerResult(content="", tokens=0)
        audit["L3"] = {"tokens": l3.tokens, "truncated": l3.truncated}
```

将 L4 构建段改为：

```python
        # Step 5: Layer 4 — 记忆检索（按场景过滤）
        filtered_files = self._filter_memory_scope(params.memory_files, scenario_config["L4_scope"])
        l4_content, l4_meta = self._build_layer_4(params.current_input, filtered_files, bg)
```

将 L5 构建段改为：

```python
        # Step 6: Layer 5 — 活跃对话（弹性）
        l0_l4_tokens = l0.tokens + l1.tokens + l2.tokens + l3.tokens + audit["L4"]["tokens"]
        remaining = self.model_limit - l0_l4_tokens - self.output_reserve

        if remaining < self.tired_threshold:
            budget_status = "tired"

        if scenario_config["L5"]:
            l5_result = self._build_layer_5(params.dialogue_history, params.current_input, remaining)
        else:
            input_tokens = TokenCounter.count(params.current_input)
            l5_result = LayerResult(
                content=[{"role": "user", "content": params.current_input}],
                tokens=input_tokens,
            )
        audit["L5"] = {"tokens": l5_result.tokens, "truncated": l5_result.truncated}
```

- [ ] **步骤 4：运行场景分流测试**

运行：`cd d:/work_ai/agentVillage && python -m pytest tests/server/test_context_builder.py::TestScenarioDispatch -v`
预期：ALL PASSED（12 tests）

- [ ] **步骤 5：运行全部 context_builder 测试确认不回归**

运行：`cd d:/work_ai/agentVillage && python -m pytest tests/server/test_context_builder.py -v`
预期：ALL PASSED

- [ ] **步骤 6：Commit**

```bash
git add server/llm/context_builder.py tests/server/test_context_builder.py
git commit -m "feat(context): build() 方法接入场景分流，条件性构建 L3/L4/L5"
```

---

## 任务 5：orchestrator.py 传入 AUTONOMOUS_DECISION 场景

**文件：**
- 修改：`server/core/orchestrator.py:175-205`（_single_autonomous_turn 方法）
- 测试：`tests/server/test_autonomous_loop.py`（如有相关测试）

- [ ] **步骤 1：修改 orchestrator.py**

在 `server/core/orchestrator.py` 的 `_single_autonomous_turn` 方法中，修改 BuildParams 调用：

将原来的：
```python
            params = BuildParams(
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

改为：
```python
            params = BuildParams(
                scenario=ScenarioType.AUTONOMOUS_DECISION,
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

同时在文件顶部的 import 区域（约第 175 行处 `from server.llm.context_builder import ContextBuilder, BuildParams`）加入 ScenarioType：

```python
from server.llm.context_builder import ContextBuilder, BuildParams, ScenarioType
```

- [ ] **步骤 2：运行相关测试确认不回归**

运行：`cd d:/work_ai/agentVillage && python -m pytest tests/server/test_autonomous_loop.py tests/server/test_orchestrator.py -v`
预期：ALL PASSED

- [ ] **步骤 3：Commit**

```bash
git add server/core/orchestrator.py
git commit -m "feat(context): orchestrator 自主决策传入 AUTONOMOUS_DECISION 场景"
```

---

## 任务 6：routes.py 传入 PLAYER_DIALOGUE 场景

**文件：**
- 修改：`server/api/routes.py:15-61`（_build_messages 函数）

- [ ] **步骤 1：修改 routes.py**

在 `server/api/routes.py` 的 `_build_messages` 函数中，修改 import 和 BuildParams 调用：

将原 import：
```python
    from server.llm.context_builder import ContextBuilder, BuildParams
```

改为：
```python
    from server.llm.context_builder import ContextBuilder, BuildParams, ScenarioType
```

将 BuildParams 构造改为：
```python
    params = BuildParams(
        scenario=ScenarioType.PLAYER_DIALOGUE,
        identity=npc.identity,
        npc_state=npc.state,
        world_state=world_state,
        interlocutor={
            "name": "玩家",
            "summary": npc.memory.get_user_summary(),
            "visible_state": str(visible_state) if visible_state else "",
        },
        memory_files=memory_files,
        dialogue_history=history_dicts,
        current_input=input_text,
        background=npc.background if hasattr(npc, "background") else {},
    )
```

- [ ] **步骤 2：运行全部测试确认不回归**

运行：`cd d:/work_ai/agentVillage && python -m pytest tests/ -v --timeout=30`
预期：ALL PASSED

- [ ] **步骤 3：Commit**

```bash
git add server/api/routes.py
git commit -m "feat(context): routes 对话路由显式传入 PLAYER_DIALOGUE 场景"
```

---

## 任务 7：端到端验证

- [ ] **步骤 1：运行完整测试套件**

运行：`cd d:/work_ai/agentVillage && python -m pytest tests/ -v`
预期：ALL PASSED，无回归

- [ ] **步骤 2：手动验证自主决策上下文输出**

运行一个快速脚本验证自主决策的 messages 不包含对话相关内容：

```python
# 在项目根目录运行
import sys; sys.path.insert(0, ".")
from server.llm.context_builder import ContextBuilder, BuildParams, ScenarioType
from server.models.npc_state import NPCState

builder = ContextBuilder(model_limit=4096)
params = BuildParams(
    scenario=ScenarioType.AUTONOMOUS_DECISION,
    identity={"name": "农夫", "daily_habits": "种地", "core_motivation": "活着", "speaking_style": "朴实", "secret": "无"},
    npc_state=NPCState(),
    world_state={"day": 1, "hour": 8, "weather": "晴", "events": "无"},
    interlocutor={},
    memory_files={"agent_mem.md": "与酒保关系好", "user.md": "玩家很友善"},
    dialogue_history=[],
    current_input="【行动指令】\n请选择工具。",
    background={},
)
result = builder.build(params)
for i, m in enumerate(result.messages):
    print(f"--- Message {i} ({m['role']}) ---")
    print(m["content"][:200])
    print()
print(f"Audit: {result.audit}")
```

预期输出：
- 不含"【对方信息】"
- 不含"玩家很友善"（user.md 被过滤）
- 最后一条 user message 是"【行动指令】\n请选择工具。"

- [ ] **步骤 3：最终 Commit（如有修复）**

如果步骤 1-2 发现问题并修复，提交修复。否则跳过。
