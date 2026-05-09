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
        ratios = {0: 0.30, 1: 0.05, 2: 0.05, 3: 0.10, 4: 0.25, 5: 0.25}
        return int(self.model_limit * ratios.get(layer, 0))


@dataclass
class BuildParams:
    identity: dict
    npc_state: any
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


class ContextBuilder:
    def __init__(self, config: ContextConfig | None = None,
                 retriever=None):
        self.config = config or ContextConfig()
        self.retriever = retriever  # MemoryRetriever, set in Task 6
        self._identity_checksum: int | None = None

    def _get_retriever(self):
        if self.retriever is None:
            from server.llm.memory_retriever import SimpleKeywordRetriever
            self.retriever = SimpleKeywordRetriever()
        return self.retriever

    def build(self, params: BuildParams) -> BuildResult:
        from server.llm.token_counter import TokenCounter

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

        # Step 5: Layer 4
        l4_content, l4_meta = self._build_layer_4(params.current_input, params.memory_files)
        l4_tokens = TokenCounter.count(l4_content)
        l4_quota = self.config.quota(4)
        l4_truncated = l4_tokens > l4_quota
        audit["L4"] = {"tokens": min(l4_tokens, l4_quota), "truncated": l4_truncated, "meta": l4_meta}

        # Step 6: Layer 5
        l0_l4_tokens = l0.tokens + l1.tokens + l2.tokens + l3.tokens + audit["L4"]["tokens"]
        remaining = self.config.model_limit - l0_l4_tokens - self.config.output_reserve

        if remaining < self.config.tired_threshold:
            budget_status = "tired"

        l5_result = self._build_layer_5(params.dialogue_history, params.current_input, remaining)
        audit["L5"] = {"tokens": l5_result.tokens, "truncated": l5_result.truncated}

        # Step 7: 组装 + 最终校验
        messages = self._assemble_messages(l0, l1, l2, l3, l4_content, l5_result, budget_status)
        messages = self._sanitize(messages)

        total_tokens = TokenCounter.count_messages(messages)
        if total_tokens > self.config.model_limit - self.config.output_reserve:
            l5_fallback = self._build_layer_5(params.dialogue_history[-3:], params.current_input, remaining)
            messages = self._assemble_messages(l0, l1, l2, l3, l4_content, l5_fallback, budget_status)
            messages = self._sanitize(messages)

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
        quota = self.config.quota(4)
        return self._get_retriever().retrieve(trigger, memory_files, max_tokens=quota)

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

        # 压缩逻辑
        if len(dialogue_history) > self.config.compress_threshold and len(kept) < len(dialogue_history):
            messages.insert(0, {"role": "system", "content": "【当前对话】\n[前情摘要] 之前的对话已省略。"})

        messages = kept + messages
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


# 保持模块级 TokenCounter 引用
from server.llm.token_counter import TokenCounter
