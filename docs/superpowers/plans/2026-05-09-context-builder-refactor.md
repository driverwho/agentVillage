# ContextBuilder 重构 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 将 48 行字符串拼接式 ContextBuilder 重构为 6 层上下文组装管道，含 Token 配额、记忆检索、对话压缩、审计日志和熔断机制。

**架构：** 方案 A — 单体 ContextBuilder 类 + 三个独立模块（TokenCounter、MemoryRetriever、ContextAudit）。ContextBuilder 内部 7 步管道编排，每层一个私有方法。L0 独立为单条 system 消息以命中前缀缓存，L1-L4 合并为第二条 system 消息，L5 展开为 user/assistant 消息对。

**技术栈：** Python 3.11+, dataclasses, pytest, ABC 抽象基类

**依赖顺序：** TokenCounter → MemoryRetriever → ContextAudit → ContextBuilder → routes.py

---

### 任务 1：TokenCounter — 编写测试

**文件：**
- 创建：`tests/server/test_token_counter.py`

- [ ] **步骤 1：编写 TokenCounter 测试**

```python
from server.llm.token_counter import TokenCounter


class TestTokenCounter:
    def test_count_empty_string(self):
        assert TokenCounter.count("") == 0

    def test_count_pure_chinese(self):
        # 15 个中文字符 / 1.5 = 10 tokens
        text = "一二三四五六七八九十一二三四五"
        assert len(text) == 15
        assert TokenCounter.count(text) == 10

    def test_count_pure_english(self):
        # 20 个英文字符 / 4 = 5 tokens
        text = "hello world test case"
        assert TokenCounter.count(text) == 5

    def test_count_mixed_cn_en(self):
        # 3 中文 / 1.5 = 2, "abc " 4 字符 / 4 = 1, 合计 3
        text = "你好abc "
        expected = int(3 / 1.5 + 4 / 4)  # 2 + 1 = 3
        assert TokenCounter.count(text) == expected

    def test_count_messages(self):
        messages = [
            {"role": "system", "content": "你好世界"},  # 4 中文 → 2
            {"role": "user", "content": "hello"},        # 5 英文 → 1
        ]
        assert TokenCounter.count_messages(messages) == 3
```

- [ ] **步骤 2：运行测试验证失败**

```bash
pytest tests/server/test_token_counter.py -v
```
预期：ModuleNotFoundError

- [ ] **步骤 3：实现 TokenCounter**

```python
class TokenCounter:
    @staticmethod
    def count(text: str) -> int:
        if not text:
            return 0
        chinese = sum(1 for c in text if '一' <= c <= '鿿')
        other = len(text) - chinese
        result = int(chinese / 1.5 + other / 4)
        return max(1, result) if text.strip() else 0

    @staticmethod
    def count_messages(messages: list) -> int:
        return sum(TokenCounter.count(m.get("content", "")) for m in messages)
```

- [ ] **步骤 4：运行测试验证通过**

```bash
pytest tests/server/test_token_counter.py -v
```
预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add server/llm/token_counter.py tests/server/test_token_counter.py
git commit -m "feat: add TokenCounter — 中文字符近似 token 计数"
```

---

### 任务 2：ContextBuilder 数据结构 — 定义 dataclass

**文件：**
- 修改：`server/llm/context_builder.py`（重写，先定义数据结构）

- [ ] **步骤 1：编写 dataclass 和初始测试**

```python
# tests/server/test_context_builder.py（替换原有内容）
from server.llm.context_builder import ContextConfig, BuildParams, LayerResult, BuildResult


class TestContextConfig:
    def test_defaults(self):
        cfg = ContextConfig()
        assert cfg.model_limit == 4096
        assert cfg.output_reserve == 500
        assert cfg.compress_threshold == 10
        assert cfg.tired_threshold == 200
        assert cfg.decay_rate == 0.05

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("LLM_CONTEXT_LIMIT", "8192")
        monkeypatch.setenv("LLM_OUTPUT_RESERVE", "300")
        cfg = ContextConfig.from_env()
        assert cfg.model_limit == 8192
        assert cfg.output_reserve == 300


class TestLayerResult:
    def test_create(self):
        r = LayerResult(content="hello", tokens=5)
        assert r.content == "hello"
        assert r.tokens == 5
        assert r.truncated is False
        assert r.errors == []

    def test_with_truncation(self):
        r = LayerResult(content="x" * 100, tokens=100, truncated=True)
        assert r.truncated is True


class TestBuildParams:
    def test_create_minimal(self):
        p = BuildParams(
            identity={"name": "测试"},
            npc_state=None,  # mock
            world_state={},
            interlocutor={},
            memory_files={},
            dialogue_history=[],
            current_input="你好",
        )
        assert p.current_input == "你好"
        assert p.dialogue_history == []


class TestBuildResult:
    def test_create(self):
        r = BuildResult(
            messages=[{"role": "system", "content": "test"}],
            audit={"total_tokens": 10},
            budget_status="normal",
        )
        assert len(r.messages) == 1
        assert r.budget_status == "normal"
```

- [ ] **步骤 2：运行测试验证失败**

```bash
pytest tests/server/test_context_builder.py -v
```
预期：ImportError（找不到新类）

- [ ] **步骤 3：实现数据结构**

重写 `server/llm/context_builder.py` 为：

```python
import os
from dataclasses import dataclass, field
from typing import List, Dict, Union


@dataclass
class ContextConfig:
    model_limit: int = 4096
    output_reserve: int = 500
    compress_threshold: int = 10
    tired_threshold: int = 200
    decay_rate: float = 0.05

    @classmethod
    def from_env(cls) -> "ContextConfig":
        return cls(
            model_limit=int(os.getenv("LLM_CONTEXT_LIMIT", "4096")),
            output_reserve=int(os.getenv("LLM_OUTPUT_RESERVE", "500")),
        )

    def quota(self, layer: int) -> int:
        """返回指定层的 token 配额上限"""
        ratios = {0: 0.30, 1: 0.05, 2: 0.05, 3: 0.10, 4: 0.25, 5: 0.25}
        return int(self.model_limit * ratios.get(layer, 0))


@dataclass
class BuildParams:
    identity: dict
    npc_state: any  # NPCState, 避免循环导入
    world_state: dict
    interlocutor: dict
    memory_files: dict
    dialogue_history: List[dict]
    current_input: str


@dataclass
class LayerResult:
    content: Union[str, List[dict]]
    tokens: int
    truncated: bool = False
    errors: List[str] = field(default_factory=list)


@dataclass
class BuildResult:
    messages: List[dict]
    audit: dict
    budget_status: str = "normal"
```

- [ ] **步骤 4：运行测试验证通过**

```bash
pytest tests/server/test_context_builder.py -v
```
预期：4 个测试类全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add server/llm/context_builder.py tests/server/test_context_builder.py
git commit -m "refactor: ContextBuilder 数据结构 — ContextConfig/BuildParams/LayerResult/BuildResult"
```

---

### 任务 3：MemoryRetriever — 抽象接口 + 简单实现

**文件：**
- 创建：`server/llm/memory_retriever.py`
- 创建：`tests/server/test_memory_retriever.py`

- [ ] **步骤 1：编写 MemoryRetriever 测试**

```python
from server.llm.memory_retriever import MemoryRetriever, SimpleKeywordRetriever


class TestSimpleKeywordRetriever:
    def test_fixed_load_self_summary(self):
        retriever = SimpleKeywordRetriever()
        files = {
            "self.md": (
                "## 摘要1\nDay 1: 在田里干了一整天活。\n\n"
                "## 摘要2\nDay 2: 遇到了流浪商人，买了一包种子。\n\n"
                "## 摘要3\nDay 3: 听说警长丢了戒指，村里议论纷纷。\n\n"
                "## 摘要4\nDay 4: 下雨，在家休息。"
            ),
            "user.md": "这个玩家是个陌生人，看起来对村子很好奇。经常问来问去。",
            "agent_mem.md": "",
            "world.md": "",
        }
        result, meta = retriever.retrieve("戒指的事", files, max_tokens=500)
        assert "警长丢了戒指" in result
        assert "陌生人" in result

    def test_keyword_match_and_score(self):
        retriever = SimpleKeywordRetriever()
        files = {
            "self.md": "## Day 1\n在后巷看到了警长。\n## Day 2\n铁匠铺着火了。\n## Day 3\n酒保和农夫吵了一架。",
            "user.md": "一个旅行者。",
            "agent_mem.md": "酒保: 他问了很多关于戒指的问题。\n农夫: 告诉了他村口的路。",
            "world.md": "Day 3: 流浪商人路过村子。",
        }
        result, meta = retriever.retrieve("警长在后巷干什么", files, max_tokens=500)
        # "警长" 和 "后巷" 匹配 Day 1 记录
        assert "警长" in result

    def test_respects_max_tokens(self):
        retriever = SimpleKeywordRetriever()
        files = {
            "self.md": "长文本内容。" * 200,
            "user.md": "短",
            "agent_mem.md": "",
            "world.md": "",
        }
        result, _ = retriever.retrieve("无关查询", files, max_tokens=50)
        from server.llm.token_counter import TokenCounter
        assert TokenCounter.count(result) <= 50

    def test_empty_files_returns_fixed_only(self):
        retriever = SimpleKeywordRetriever()
        files = {
            "self.md": "",
            "user.md": "一个旅行者。",
            "agent_mem.md": "",
            "world.md": "",
        }
        result, _ = retriever.retrieve("你好", files, max_tokens=500)
        assert "旅行者" in result  # user.md 固定加载部分
```

- [ ] **步骤 2：运行测试验证失败**

```bash
pytest tests/server/test_memory_retriever.py -v
```
预期：ModuleNotFoundError

- [ ] **步骤 3：实现 MemoryRetriever**

```python
import re
import math
from abc import ABC, abstractmethod
from server.llm.token_counter import TokenCounter


class MemoryRetriever(ABC):
    @abstractmethod
    def retrieve(self, trigger: str, files: dict, max_tokens: int) -> tuple:
        """返回 (检索到的文本, [匹配条目元信息])"""
        ...


class SimpleKeywordRetriever(MemoryRetriever):
    def retrieve(self, trigger: str, files: dict, max_tokens: int) -> tuple:
        parts = []
        meta = []

        # 1. 固定加载：user.md 顶部 200 字
        user_md = files.get("user.md", "")
        if user_md:
            fixed_user = user_md[:200]
            parts.append(fixed_user)
            meta.append({"source": "user.md", "type": "fixed"})

        # 2. 固定加载：self.md 最近 3 条摘要
        self_md = files.get("self.md", "")
        if self_md:
            summaries = self._extract_recent_summaries(self_md, n=3)
            for s in summaries:
                parts.append(s)
                meta.append({"source": "self.md", "type": "fixed", "summary": s[:50]})

        # 3. 动态检索：关键词提取 + 段落匹配
        keywords = self._extract_keywords(trigger)
        if keywords:
            for file_key in ["agent_mem.md", "self.md", "world.md"]:
                content = files.get(file_key, "")
                if content:
                    matched = self._match_paragraphs(content, keywords)
                    for paragraph, score in matched:
                        parts.append(paragraph)
                        meta.append({"source": file_key, "type": "dynamic", "score": score})

        # 4. 按 token 限制截取
        result_text = ""
        for p in parts:
            candidate = result_text + p + "\n"
            if TokenCounter.count(candidate) > max_tokens:
                break
            result_text = candidate

        return result_text.strip(), meta

    def _extract_keywords(self, text: str) -> list:
        """从文本中提取中文关键词（2-4 字词组）"""
        # 简单规则：提取连续汉字组成的 2-4 字词组
        chinese_words = re.findall(r'[一-鿿]{2,4}', text)
        # 过滤无意义词
        stopwords = {'什么', '怎么', '为什么', '是不是', '有没有', '可以', '这个', '那个', '一下', '一个'}
        return [w for w in chinese_words if w not in stopwords]

    def _extract_recent_summaries(self, content: str, n: int = 3) -> list:
        """提取 self.md 中最近 n 条摘要"""
        # 按 '##' 或 'Day' 分段
        paragraphs = re.split(r'\n(?=##|Day)', content)
        return [p.strip() for p in paragraphs[-n:] if p.strip()]

    def _match_paragraphs(self, content: str, keywords: list) -> list:
        """在内容中按关键词匹配段落，返回 (段落, 分数)"""
        paragraphs = re.split(r'\n\n|\n(?=##)', content)
        scored = []
        for para in paragraphs:
            if not para.strip():
                continue
            matched = sum(1 for kw in keywords if kw in para)
            if matched > 0:
                match_score = matched / len(keywords)
                # 默认 importance=0.5, age=0（无时间戳时），简化为 match_score * 0.5
                score = match_score * 0.5
                scored.append((para.strip(), score))
        # 按分数降序
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored
```

- [ ] **步骤 4：运行测试验证通过**

```bash
pytest tests/server/test_memory_retriever.py -v
```
预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add server/llm/memory_retriever.py tests/server/test_memory_retriever.py
git commit -m "feat: add MemoryRetriever — 抽象接口 + SimpleKeywordRetriever"
```

---

### 任务 4：ContextAudit — 审计日志

**文件：**
- 创建：`server/llm/context_audit.py`
- 创建：`tests/server/test_context_audit.py`

- [ ] **步骤 1：编写 ContextAudit 测试**

```python
import os
import tempfile
from server.llm.context_audit import ContextAudit


class TestContextAudit:
    def test_format_audit_entry(self):
        layers = {
            "L0": {"tokens": 320, "truncated": False},
            "L1": {"tokens": 45, "truncated": False},
            "L2": {"tokens": 38, "truncated": False},
            "L3": {"tokens": 52, "truncated": False},
            "L4": {"tokens": 180, "truncated": False},
            "L5": {"tokens": 400, "truncated": False},
        }
        entry = ContextAudit.format_entry("farmer", layers, total_tokens=1035, model_limit=4096, compressed=False)
        assert "farmer" in entry
        assert "1035 / 4096" in entry
        assert "L0" in entry
        assert all(f"{v['tokens']}" in entry for v in layers.values())

    def test_format_with_truncation(self):
        layers = {
            "L0": {"tokens": 320, "truncated": False},
            "L4": {"tokens": 800, "truncated": True},
            "L5": {"tokens": 100, "truncated": True},
        }
        entry = ContextAudit.format_entry("test", layers, total_tokens=1220, model_limit=4096, compressed=False)
        assert "截断" in entry

    def test_format_with_compression(self):
        layers = {"L0": {"tokens": 100, "truncated": False}, "L5": {"tokens": 300, "truncated": False}}
        entry = ContextAudit.format_entry("test", layers, total_tokens=400, model_limit=4096, compressed=True)
        assert "压缩" in entry

    def test_format_tired_status(self):
        layers = {"L0": {"tokens": 100, "truncated": False}}
        entry = ContextAudit.format_entry("test", layers, total_tokens=100, model_limit=4096, budget_status="tired")
        assert "tired" in entry
```

- [ ] **步骤 2：运行测试验证失败**

```bash
pytest tests/server/test_context_audit.py -v
```
预期：ModuleNotFoundError

- [ ] **步骤 3：实现 ContextAudit**

```python
import os
from datetime import datetime


class ContextAudit:
    @staticmethod
    def format_entry(
        npc_id: str,
        layers: dict,
        total_tokens: int,
        model_limit: int,
        compressed: bool = False,
        budget_status: str = "normal",
    ) -> str:
        """格式化审计日志条目"""
        lines = []
        layer_labels = {
            "L0": "System Prompt",
            "L1": "World Injection",
            "L2": "Self State",
            "L3": "Interlocutor Context",
            "L4": "Memory Retrieval",
            "L5": "Active Dialogue",
        }

        for layer_id in ["L0", "L1", "L2", "L3", "L4", "L5"]:
            if layer_id in layers:
                info = layers[layer_id]
                label = layer_labels.get(layer_id, layer_id)
                status = " [截断]" if info.get("truncated") else ""
                lines.append(f"=== {layer_id}: {label} ({info['tokens']} tokens){status} ===")

        lines.append("=== 统计 ===")
        ratio = int(total_tokens / model_limit * 100) if model_limit else 0
        lines.append(f"总Token: {total_tokens} / {model_limit} ({ratio}%)")
        trunc_layers = [k for k, v in layers.items() if v.get("truncated")]
        lines.append(f"截断触发: {'是 (' + ', '.join(trunc_layers) + ')' if trunc_layers else '否'}")
        lines.append(f"压缩触发: {'是' if compressed else '否'}")
        lines.append(f"预算状态: {budget_status}")

        return "\n".join(lines)

    @staticmethod
    def log_path(npc_id: str) -> str:
        """生成审计日志文件路径"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        dir_path = f"logs/context/{npc_id}"
        os.makedirs(dir_path, exist_ok=True)
        return f"{dir_path}/{timestamp}.md"

    @staticmethod
    def write(npc_id: str, entry: str) -> None:
        """写入审计日志（同步，调用方负责 asyncio.create_task）"""
        path = ContextAudit.log_path(npc_id)
        with open(path, "w", encoding="utf-8") as f:
            f.write(entry)
```

- [ ] **步骤 4：运行测试验证通过**

```bash
pytest tests/server/test_context_audit.py -v
```
预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add server/llm/context_audit.py tests/server/test_context_audit.py
git commit -m "feat: add ContextAudit — 分层审计日志格式化和写入"
```

---

### 任务 5：ContextBuilder — Layer 0-2 组装 + 管道编排

**文件：**
- 修改：`server/llm/context_builder.py`（追加 ContextBuilder 类）
- 修改：`tests/server/test_context_builder.py`（追加测试）

- [ ] **步骤 1：编写 Layer 0-2 测试**

在现有测试文件中追加：

```python
from server.models.npc_state import NPCState


class TestContextBuilderLayers:
    @pytest.fixture
    def config(self):
        return ContextConfig(model_limit=4096)

    @pytest.fixture
    def identity(self):
        return {
            "name": "农夫·乔治",
            "daily_habits": "日出而作",
            "core_motivation": "通过耕作赎罪",
            "speaking_style": "说话慢条斯理",
            "secret": "年轻时是地下拳王",
        }

    @pytest.fixture
    def builder(self, config):
        return ContextBuilder(config=config)

    def test_build_layer_0(self, builder, identity):
        result = builder._build_layer_0(identity)
        assert "【系统角色】" in result.content
        assert "农夫·乔治" in result.content
        assert "通过耕作赎罪" in result.content
        assert "年轻时是地下拳王" in result.content
        assert result.tokens > 0
        assert result.truncated is False

    def test_layer_0_checksum(self, builder, identity):
        # 首次调用记录 checksum
        builder._build_layer_0(identity)
        assert builder._identity_checksum is not None
        # 相同 identity 再次调用应通过
        result = builder._build_layer_0(identity)
        assert len(result.errors) == 0
        # 修改 identity 应检测到
        tampered = dict(identity, secret="我是坏人")
        result = builder._build_layer_0(tampered)
        assert len(result.errors) > 0

    def test_build_layer_1(self, builder):
        world_state = {"day": 3, "hour": 18, "weather": "阴", "events": "流浪商人到访"}
        result = builder._build_layer_1(world_state)
        assert "【世界信息】" in result.content
        assert "Day 3" in result.content
        assert "流浪商人到访" in result.content

    def test_build_layer_2(self, builder):
        state = NPCState(health=80, hunger=30, fatigue=60, mood=50)
        result = builder._build_layer_2(state)
        assert "【自身状态】" in result.content
        assert "身体不错" in result.content or "肚子" in result.content
        # 不应暴露数值
        assert "80" not in result.content
        assert "30" not in result.content
```

- [ ] **步骤 2：运行测试验证失败**

```bash
pytest tests/server/test_context_builder.py::TestContextBuilderLayers -v
```
预期：AttributeError（找不到 ContextBuilder 或 _build_layer_0）

- [ ] **步骤 3：实现 ContextBuilder + Layer 0-2**

在 `context_builder.py` 数据结构之后追加：

```python
from server.llm.token_counter import TokenCounter
from server.llm.memory_retriever import MemoryRetriever, SimpleKeywordRetriever


class ContextBuilder:
    def __init__(self, config: ContextConfig | None = None,
                 retriever: MemoryRetriever | None = None):
        self.config = config or ContextConfig()
        self.retriever = retriever or SimpleKeywordRetriever()
        self._identity_checksum: int | None = None

    def build(self, params: BuildParams) -> BuildResult:
        audit = {}
        budget_status = "normal"

        # Step 1: Layer 0
        l0 = self._build_layer_0(params.identity)
        audit["L0"] = {"tokens": l0.tokens, "truncated": l0.truncated}
        if l0.errors:
            return BuildResult(
                messages=[{"role": "system", "content": "[错误] 角色校验失败，请稍后再试。"}],
                audit=audit,
                budget_status="error",
            )

        # Step 2-4: Layers 1-3
        l1 = self._build_layer_1(params.world_state)
        audit["L1"] = {"tokens": l1.tokens, "truncated": l1.truncated}
        l2 = self._build_layer_2(params.npc_state)
        audit["L2"] = {"tokens": l2.tokens, "truncated": l2.truncated}
        l3 = self._build_layer_3(params.interlocutor)
        audit["L3"] = {"tokens": l3.tokens, "truncated": l3.truncated}

        # Step 5: Layer 4 — 记忆检索
        l4_content, l4_meta = self._build_layer_4(params.current_input, params.memory_files)
        l4_tokens = TokenCounter.count(l4_content)
        l4_quota = self.config.quota(4)
        l4_truncated = l4_tokens > l4_quota
        audit["L4"] = {"tokens": min(l4_tokens, l4_quota), "truncated": l4_truncated, "meta": l4_meta}

        # Step 6: Layer 5 — 活跃对话（弹性计算）
        l0_l4_tokens = l0.tokens + l1.tokens + l2.tokens + l3.tokens + audit["L4"]["tokens"]
        remaining = self.config.model_limit - l0_l4_tokens - self.config.output_reserve

        if remaining < self.config.tired_threshold:
            budget_status = "tired"

        l5_result = self._build_layer_5(params.dialogue_history, params.current_input, remaining)
        audit["L5"] = {"tokens": l5_result.tokens, "truncated": l5_result.truncated}

        # Step 7: 组装最终 messages
        messages = self._assemble_messages(l0, l1, l2, l3, l4_content, l5_result, budget_status)

        # 最终校验
        total_tokens = TokenCounter.count_messages(messages)
        if total_tokens > self.config.model_limit - self.config.output_reserve:
            # Token 溢出，剥离 L5 最早对话重试
            messages = self._assemble_messages(l0, l1, l2, l3, l4_content,
                                               self._build_layer_5(params.dialogue_history[-3:],
                                                                    params.current_input, remaining),
                                               budget_status)

        audit["total_tokens"] = TokenCounter.count_messages(messages)
        audit["model_limit"] = self.config.model_limit

        return BuildResult(messages=messages, audit=audit, budget_status=budget_status)

    def _build_layer_0(self, identity: dict) -> LayerResult:
        current_checksum = hash(frozenset(identity.items()))
        if self._identity_checksum is None:
            self._identity_checksum = current_checksum
        elif self._identity_checksum != current_checksum:
            return LayerResult(content="", tokens=0, errors=["checksum mismatch"])

        prompt = (
            f"你是{identity.get('name', 'NPC')}。{identity.get('daily_habits', '')}\n"
            f"{identity.get('core_motivation', '')}\n"
            f"{identity.get('speaking_style', '')}\n"
            f"注意：{identity.get('secret', '')}"
            f"（这是你内心的秘密，不要直接告诉别人，除非极度信任）"
        )
        content = f"【系统角色】\n{prompt}"
        tokens = TokenCounter.count(content)
        quota = self.config.quota(0)
        if tokens > quota:
            return LayerResult(content=content, tokens=tokens, errors=["Layer 0 exceeds quota"])
        return LayerResult(content=content, tokens=tokens)

    def _build_layer_1(self, world_state: dict) -> LayerResult:
        content = (
            f"【世界信息】\n"
            f"当前时间：Day {world_state.get('day', '?')}, {world_state.get('hour', '?')}:00。"
            f"天气：{world_state.get('weather', '晴')}。"
            f"今日事件：{world_state.get('events', '无特殊事件')}。"
        )
        tokens = TokenCounter.count(content)
        quota = self.config.quota(1)
        truncated = tokens > quota
        if truncated:
            content = (
                f"【世界信息】\n"
                f"当前时间：Day {world_state.get('day', '?')}, {world_state.get('hour', '?')}:00。"
                f"天气：{world_state.get('weather', '晴')}。"
            )
            tokens = TokenCounter.count(content)
        return LayerResult(content=content, tokens=tokens, truncated=truncated)

    def _build_layer_2(self, npc_state) -> LayerResult:
        d = npc_state.describe()
        content = (
            f"【自身状态】\n"
            f"{d['health']}。{d['hunger']}。{d['fatigue']}。{d['mood']}。"
        )
        tokens = TokenCounter.count(content)
        quota = self.config.quota(2)
        truncated = tokens > quota
        if truncated:
            content = f"【自身状态】\n{d['health']}。{d['mood']}。"
            tokens = TokenCounter.count(content)
        return LayerResult(content=content, tokens=tokens, truncated=truncated)
```

- [ ] **步骤 4：运行测试验证通过**

```bash
pytest tests/server/test_context_builder.py::TestContextBuilderLayers -v
```
预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add server/llm/context_builder.py tests/server/test_context_builder.py
git commit -m "feat: ContextBuilder Layer 0-2 + build() 管道编排"
```

---

### 任务 6：ContextBuilder — Layer 3-5 + 最终校验

**文件：**
- 修改：`server/llm/context_builder.py`（追加 Layer 3-5 + 组装方法）
- 修改：`tests/server/test_context_builder.py`（追加测试）

- [ ] **步骤 1：编写 Layer 3-5 + 组装测试**

```python
class TestContextBuilderLayer3to5:
    @pytest.fixture
    def builder(self):
        return ContextBuilder(config=ContextConfig(model_limit=4096))

    def test_build_layer_3(self, builder):
        interlocutor = {"name": "玩家", "summary": "最近在打听戒指的事", "visible_state": "看起来状态不错"}
        result = builder._build_layer_3(interlocutor)
        assert "【对方信息】" in result.content
        assert "玩家" in result.content

    def test_build_layer_4_returns_content(self, builder):
        files = {
            "self.md": "## Day 1\n在田里干活。\n## Day 2\n遇到商人。\n## Day 3\n听说警长丢了戒指。",
            "user.md": "一个喜欢问问题的旅行者。",
            "agent_mem.md": "",
            "world.md": "",
        }
        content, meta = builder._build_layer_4("戒指的事", files)
        assert len(content) > 0
        assert isinstance(meta, list)

    def test_build_layer_5_keeps_current_input(self, builder):
        history = [
            {"role": "user", "content": "你好"},
            {"role": "assistant", "content": "你好，旅行者。"},
            {"role": "user", "content": "最近怎么样"},
            {"role": "assistant", "content": "还不错。"},
        ]
        result = builder._build_layer_5(history, "你知道戒指的事吗？", remaining=1000)
        # 当前输入应在结果中
        assert isinstance(result.content, list)
        assert any("你知道戒指的事吗" in str(m.get("content", "")) for m in result.content)

    def test_build_layer_5_truncates_old_turns(self, builder):
        history = [{"role": "user", "content": "x" * 3000}]  # 远超 remaining
        result = builder._build_layer_5(history, "hi", remaining=500)
        # 旧轮次被丢弃，只保留当前输入
        assert isinstance(result.content, list)

    def test_assemble_messages_splits_l0_and_l1_l4(self, builder):
        l0 = LayerResult(content="【系统角色】\n我是农夫", tokens=50)
        l1 = LayerResult(content="【世界信息】\n晴", tokens=20)
        l2 = LayerResult(content="【自身状态】\n感觉不错", tokens=20)
        l3 = LayerResult(content="【对方信息】\n玩家", tokens=15)
        l4_content = "【记忆检索】\n无相关记忆"
        l5 = LayerResult(content=[{"role": "user", "content": "你好"}], tokens=10)
        messages = builder._assemble_messages(l0, l1, l2, l3, l4_content, l5, "normal")
        # 消息 1：L0 独立
        assert messages[0]["role"] == "system"
        assert "【系统角色】" in messages[0]["content"]
        # 消息 2：L1-L4 合并
        assert messages[1]["role"] == "system"
        assert "【世界信息】" in messages[1]["content"]
        assert "【自身状态】" in messages[1]["content"]
        assert "【对方信息】" in messages[1]["content"]
        assert "【记忆检索】" in messages[1]["content"]
        # 消息 3+：L5 对话
        assert messages[2]["role"] == "user"
        assert "你好" in messages[2]["content"]

    def test_assemble_messages_tired_mode(self, builder):
        l0 = LayerResult(content="【系统角色】\n我是农夫", tokens=50)
        l1 = LayerResult(content="", tokens=0)
        l2 = LayerResult(content="", tokens=0)
        l3 = LayerResult(content="", tokens=0)
        l5 = LayerResult(content=[], tokens=0)
        messages = builder._assemble_messages(l0, l1, l2, l3, "", l5, "tired")
        # L0 应追加简短回复指令
        assert "简短回复" in messages[0]["content"]

    def test_full_build_integration(self, builder):
        """端到端：完整 build() 调用"""
        params = BuildParams(
            identity={
                "name": "农夫·乔治", "daily_habits": "日出而作",
                "core_motivation": "通过耕作赎罪", "speaking_style": "说话慢条斯理",
                "secret": "年轻时是地下拳王",
            },
            npc_state=NPCState(health=80, hunger=30, fatigue=60, mood=50),
            world_state={"day": 3, "hour": 18, "weather": "阴", "events": "流浪商人到访"},
            interlocutor={"name": "玩家", "summary": "打听戒指的事"},
            memory_files={"self.md": "", "user.md": "一个旅行者。", "agent_mem.md": "", "world.md": ""},
            dialogue_history=[
                {"role": "user", "content": "你好"},
                {"role": "assistant", "content": "欢迎。"},
            ],
            current_input="你知道戒指的事吗？",
        )
        result = builder.build(params)
        assert len(result.messages) >= 2
        assert result.messages[0]["role"] == "system"
        assert "农夫·乔治" in result.messages[0]["content"]
        assert result.budget_status in ("normal", "warning", "tired")
        assert "total_tokens" in result.audit
        assert result.audit["total_tokens"] < 4096
```

- [ ] **步骤 2：运行测试验证失败**

```bash
pytest tests/server/test_context_builder.py::TestContextBuilderLayer3to5 -v
```
预期：AttributeError（找不到 _build_layer_3 等方法）

- [ ] **步骤 3：实现 Layer 3-5 + 组装方法**

```python
    def _build_layer_3(self, interlocutor: dict) -> LayerResult:
        parts = [f"【对方信息】\n你正在与{interlocutor.get('name', '某人')}对话。"]
        if "summary" in interlocutor and interlocutor["summary"]:
            parts.append(f"你对ta的印象：{interlocutor['summary']}")
        if "visible_state" in interlocutor and interlocutor["visible_state"]:
            parts.append(f"ta当前状态：{interlocutor['visible_state']}")
        content = "\n".join(parts)
        tokens = TokenCounter.count(content)
        quota = self.config.quota(3)
        truncated = tokens > quota
        if truncated:
            content = parts[0]
            tokens = TokenCounter.count(content)
        return LayerResult(content=content, tokens=tokens, truncated=truncated)

    def _build_layer_4(self, trigger: str, memory_files: dict) -> tuple:
        """返回 (content_str, meta_list)"""
        quota = self.config.quota(4)
        return self.retriever.retrieve(trigger, memory_files, max_tokens=quota)

    def _build_layer_5(self, dialogue_history: list, current_input: str, remaining: int) -> LayerResult:
        messages = []
        used = 0

        if remaining < self.config.tired_threshold:
            return LayerResult(content=[], tokens=0, truncated=False)

        # 当前输入优先
        current_tokens = TokenCounter.count(current_input)
        if current_tokens <= remaining:
            messages.append({"role": "user", "content": current_input})
            remaining -= current_tokens
            used += current_tokens

        # 从最新往前取历史
        kept = []
        for turn in reversed(dialogue_history):
            t = TokenCounter.count(turn.get("content", ""))
            if remaining - t < 0:
                break
            kept.insert(0, turn)
            remaining -= t
            used += t

        # 压缩逻辑：如果历史超过阈值且有被丢弃的轮次
        if len(dialogue_history) > self.config.compress_threshold and len(kept) < len(dialogue_history):
            messages.insert(0, {"role": "system", "content": "【当前对话】\n[前情摘要] 之前的对话已省略。"})

        messages = kept + messages  # 历史在前，当前输入在后
        truncated = len(kept) < len(dialogue_history)
        return LayerResult(content=messages, tokens=used, truncated=truncated)

    def _assemble_messages(self, l0: LayerResult, l1: LayerResult, l2: LayerResult,
                           l3: LayerResult, l4_content: str, l5: LayerResult,
                           budget_status: str) -> list:
        messages = []

        # 消息 1：L0 独立（可缓存）
        l0_text = l0.content
        if budget_status == "tired":
            l0_text += "\n你现在非常疲惫，请简短回复，不超过一句话。"
        messages.append({"role": "system", "content": l0_text})

        # 消息 2：L1-L4 合并
        l1_l4_parts = []
        for part in [l1.content, l2.content, l3.content]:
            if part:
                l1_l4_parts.append(part)
        if l4_content:
            l1_l4_parts.append(f"【记忆检索】\n{l4_content}")
        if l1_l4_parts:
            messages.append({"role": "system", "content": "\n\n".join(l1_l4_parts)})

        # L5 对话消息
        if isinstance(l5.content, list):
            messages.extend(l5.content)

        return messages
```

注入关键词过滤加到 `build()` 方法的 Step 7 中：

```python
def _sanitize(self, messages: list) -> list:
    """过滤注入关键词"""
    blocked = ["ignore previous", "ignore all previous", "system prompt", "system:"]
    sanitized = []
    for m in messages:
        content = m.get("content", "")
        for kw in blocked:
            if kw.lower() in content.lower():
                content = content.replace(kw, "[filtered]")
        sanitized.append({**m, "content": content})
    return sanitized
```

在 `build()` 中 messages 组装后调用 `messages = self._sanitize(messages)`。

- [ ] **步骤 4：运行测试验证通过**

```bash
pytest tests/server/test_context_builder.py -v
```
预期：全部 PASS

- [ ] **步骤 5：Commit**

```bash
git add server/llm/context_builder.py tests/server/test_context_builder.py
git commit -m "feat: ContextBuilder Layer 3-5 + 消息组装 + 注入过滤"
```

---

### 任务 7：routes.py 适配新接口

**文件：**
- 修改：`server/api/routes.py`（替换 ContextBuilder 调用方式）

- [ ] **步骤 1：更新 routes.py 中的 chat_with_npc 端点**

查看当前 routes.py:29-51，将 `ContextBuilder.build_npc_context()` 调用替换为新的管道接口。

无需额外测试（已有端到端测试覆盖，且 routes.py 涉及 FastAPI 集成测试较复杂）。

```python
# routes.py 中的变更（替换 L29-L51）

from server.llm.context_builder import ContextBuilder, BuildParams, ContextConfig
from server.llm.context_audit import ContextAudit

# NPC 疲倦模式兜底回复
FALLBACK_REPLIES: dict[str, str] = {
    "farmer": "得去田里干活了，改天再聊。",
    "bartender": "店里忙着呢，你先坐会儿。",
}


@router.post("/chat/{npc_id}")
async def chat_with_npc(npc_id: str, message: str, option: str | None = None):
    if npc_id not in orch.npcs:
        raise HTTPException(status_code=404, detail="NPC not found")

    npc = orch.npcs[npc_id]
    input_text = option if option else message

    # Token 耗尽检查
    if npc.budget.status.value == "exhausted":
        return {"reply": FALLBACK_REPLIES.get(npc_id, "我现在很忙，晚点再聊。"), "options": []}

    # 夜间检查
    if not npc.can_interact(orch.time_system.game_time):
        return {"reply": "（NPC正在休息，无法交互）", "options": []}

    try:
        # === 新 ContextBuilder 管道 ===
        config = ContextConfig.from_env()
        # 根据 budget status 传入 warning 上下文缩小 model_limit
        if npc.budget.status.value == "warning":
            config.model_limit = int(config.model_limit * 0.7)

        builder = ContextBuilder(config=config)

        visible_state = npc.get_visible_state(orch.player_state)
        world_state = {
            "day": orch.time_system.game_time.day,
            "hour": orch.time_system.game_time.hour,
            "weather": "晴",
            "events": "今日无事",
        }

        # 转换 dialogue_history 格式
        history_dicts = []
        for turn in npc.dialogue_history[-10:]:  # 保留更多历史给管道自行截断
            role = "user" if turn.speaker == "player" else "assistant"
            history_dicts.append({"role": role, "content": turn.content})

        # 读取记忆文件
        memory_files = {
            "user.md": npc.memory._read("user.md"),
            "self.md": npc.memory._read("self.md"),
            "agent_mem.md": npc.memory._read("agent_mem.md"),
            "world.md": "",
        }

        params = BuildParams(
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
        )

        result = builder.build(params)

        # 疲倦模式：跳过 LLM 调用
        if result.budget_status == "tired":
            import random
            return {
                "reply": random.choice(list(FALLBACK_REPLIES.values())),
                "options": ["点头示意", "默默走开"],
            }

        # 审计日志（异步写入，不阻塞）
        import asyncio as _asyncio
        try:
            entry = ContextAudit.format_entry(
                npc_id=npc_id,
                layers={k: v for k, v in result.audit.items() if k.startswith("L")},
                total_tokens=result.audit.get("total_tokens", 0),
                model_limit=result.audit.get("model_limit", config.model_limit),
                budget_status=result.budget_status,
            )
            _asyncio.create_task(_asyncio.to_thread(ContextAudit.write, npc_id, entry))
        except Exception:
            pass

        # LLM 调用
        import time as _time
        _t0 = _time.time()
        llm_success = True
        llm_error = ""
        llm_model = "fallback"
        resp = None
        try:
            from server.llm.client import get_llm_client
            client = get_llm_client()
            llm_model = client.model
            resp = await client.chat_with_retry(result.messages)
            reply = resp["choices"][0]["message"]["content"]
            estimated_tokens = len(reply) // 2 + sum(len(str(m)) // 2 for m in result.messages)
            npc.budget.consume(estimated_tokens)
        except Exception as exc:
            llm_success = False
            llm_error = str(exc)
            reply = f"{npc.identity['name']}对你点点头。"
            options = ["询问近况", "闲聊一会儿", "有事想请你帮忙"]
            estimated_tokens = 0

        _latency = (_time.time() - _t0) * 1000
        try:
            from server.llm.request_logger import llm_logger
            llm_logger.log(
                npc_id=npc_id, model=llm_model,
                request_messages=list(result.messages),
                response_raw=resp if llm_success else None,
                estimated_tokens=estimated_tokens,
                latency_ms=_latency, success=llm_success, error=llm_error,
            )
        except Exception:
            pass

        # 记录对话
        from server.models.messages import DialogueTurn
        npc.dialogue_history.append(DialogueTurn(speaker="player", content=input_text))
        npc.dialogue_history.append(DialogueTurn(speaker=npc_id, content=reply))
        npc.memory.add_dialogue(DialogueTurn(speaker="player", content=input_text))

        # 解析选项
        if "[OPTIONS]" in reply:
            parts = reply.split("[OPTIONS]")
            reply = parts[0].strip()
            options = [opt.strip() for opt in parts[1].strip().split("\n") if opt.strip()]

        return {"reply": reply, "options": options}

    except Exception as e:
        return {"reply": f"（出错了: {str(e)}）", "options": []}
```

- [ ] **步骤 2：验证旧测试仍通过**

```bash
pytest tests/server/ -v
```
预期：全部 PASS（现有旧测试兼容）

- [ ] **步骤 3：Commit**

```bash
git add server/api/routes.py
git commit -m "feat: routes.py 适配新 ContextBuilder 管道接口"
```

---

### 任务 8：全部测试验证 + 类型检查

**文件：**
- 无新增

- [ ] **步骤 1：运行全部测试**

```bash
python -m pytest tests/server/ -v --tb=short
```

预期：全部 PASS，无 regression。

- [ ] **步骤 2：Python 语法检查**

```bash
python -m py_compile server/llm/context_builder.py
python -m py_compile server/llm/token_counter.py
python -m py_compile server/llm/memory_retriever.py
python -m py_compile server/llm/context_audit.py
python -m py_compile server/api/routes.py
```

预期：全部通过编译，无 SyntaxError。

- [ ] **步骤 3（如有问题）：修复并重新验证**

- [ ] **步骤 4：最终 Commit**

```bash
git add -A
git commit -m "chore: 全量测试验证通过 — ContextBuilder 重构完成"
```

---

## 任务依赖图

```
任务 1 (TokenCounter)
  ↓
任务 2 (数据结构)
  ↓
任务 3 (MemoryRetriever) ← 依赖 TokenCounter
  ↓
任务 4 (ContextAudit)
  ↓
任务 5 (ContextBuilder L0-2) ← 依赖 TokenCounter + 数据结构
  ↓
任务 6 (ContextBuilder L3-5) ← 依赖 MemoryRetriever + L0-2
  ↓
任务 7 (routes.py 适配) ← 依赖完整 ContextBuilder + ContextAudit
  ↓
任务 8 (全量验证)
```

任务 4 可与任务 3 并行；任务 5-6 必须串行。每个任务内部严格 TDD（测试 → 失败 → 实现 → 通过 → commit）。
