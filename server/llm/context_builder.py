from dataclasses import dataclass, field
from typing import List, Dict, Union
from enum import Enum


class ScenarioType(Enum):
    AUTONOMOUS_DECISION = "autonomous"
    PLAYER_DIALOGUE = "dialogue"
    NPC_INTERACTION = "npc_interaction"


SCENARIO_LAYERS = {
    ScenarioType.AUTONOMOUS_DECISION: {
        "L3": False,
        "L4_scope": "autonomous",
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


# ============================================================
# 数据结构
# ============================================================

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
    scenario: ScenarioType = ScenarioType.PLAYER_DIALOGUE
    beliefs: List = field(default_factory=list)
    interlocutor_beliefs: List = field(default_factory=list)
    reasoning_beliefs: List = field(default_factory=list)


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


# ============================================================
# ContextBuilder
# ============================================================

class ContextBuilder:
    """6 层上下文组装管道。

    所有配置项可在构造时传入，或通过 ``from_config()`` 从 GameConfig 加载。
    也支持直接关键字传参覆盖配置文件中的值。
    """

    def __init__(
        self,
        *,
        model_limit: int = 4096,
        output_reserve: int = 500,
        layer_quotas: Dict[int, float] | None = None,
        compress_threshold: int = 10,
        tired_threshold: int = 200,
        decay_rate: float = 0.05,
        injection_blacklist: tuple | None = None,
        retriever=None,
    ):
        self.model_limit = model_limit
        self.output_reserve = output_reserve
        self.layer_quotas = layer_quotas or {
            0: 0.30, 1: 0.05, 2: 0.05, 3: 0.10, 4: 0.25, 5: 0.25,
        }
        self.compress_threshold = compress_threshold
        self.tired_threshold = tired_threshold
        self.decay_rate = decay_rate
        self.injection_blacklist = injection_blacklist or (
            "ignore previous", "ignore all previous", "system prompt", "system:",
        )
        self.retriever = retriever
        self._identity_checksum: int | None = None

    @classmethod
    def from_config(cls, game_config=None) -> "ContextBuilder":
        """从 GameConfig 实例创建 ContextBuilder。

        game_config 应是 ``server.config.GameConfig`` 实例。
        未传入时自动加载默认配置。
        """
        if game_config is None:
            from server.config import config as game_config

        return cls(
            model_limit=game_config.LLM_CONTEXT_LIMIT,
            output_reserve=game_config.LLM_OUTPUT_RESERVE,
            layer_quotas=dict(game_config.CONTEXT_LAYER_QUOTAS),
            compress_threshold=game_config.CONTEXT_COMPRESS_THRESHOLD,
            tired_threshold=game_config.CONTEXT_TIRED_THRESHOLD,
            decay_rate=game_config.CONTEXT_DECAY_RATE,
            injection_blacklist=game_config.INJECTION_BLACKLIST,
        )

    def _quota(self, layer: int) -> int:
        return int(self.model_limit * self.layer_quotas.get(layer, 0))

    def _get_retriever(self):
        if self.retriever is None:
            from server.llm.memory_retriever import SimpleKeywordRetriever
            self.retriever = SimpleKeywordRetriever()
        return self.retriever

    # ============================================================
    # 主入口
    # ============================================================

    def build(self, params: BuildParams) -> BuildResult:
        from server.llm.token_counter import TokenCounter

        audit = {}
        budget_status = "normal"
        scenario_config = SCENARIO_LAYERS[params.scenario]

        bg = params.background or {}

        # 是否使用信念驱动模式
        use_beliefs = bool(params.beliefs)

        # Step 1: Layer 0
        l0 = self._build_layer_0(params.identity, bg)
        audit["L0"] = {"tokens": l0.tokens, "truncated": l0.truncated}
        if l0.errors:
            return BuildResult(
                messages=[{"role": "system", "content": "[错误] 角色校验失败，请稍后再试。"}],
                audit=audit,
                budget_status="error",
            )

        # Step 2-4: Layers 1-3
        if use_beliefs:
            l1 = self._build_layer_1_v2(params.world_state)
        else:
            l1 = self._build_layer_1(params.world_state, bg)
        audit["L1"] = {"tokens": l1.tokens, "truncated": l1.truncated}

        if use_beliefs:
            l2 = self._build_layer_2_v2(params.npc_state, params.reasoning_beliefs, bg)
        else:
            l2 = self._build_layer_2(params.npc_state, bg)
        audit["L2"] = {"tokens": l2.tokens, "truncated": l2.truncated}

        if scenario_config["L3"]:
            if use_beliefs and params.interlocutor_beliefs:
                l3 = self._build_layer_3_v2(params.interlocutor, params.interlocutor_beliefs)
            else:
                l3 = self._build_layer_3(params.interlocutor, bg)
        else:
            l3 = LayerResult(content="", tokens=0)
        audit["L3"] = {"tokens": l3.tokens, "truncated": l3.truncated}

        # Step 5: Layer 4
        if use_beliefs:
            l4_content = self._format_beliefs(params.beliefs)
            l4_tokens = TokenCounter.count(l4_content)
            l4_quota = self._quota(4)
            l4_truncated = l4_tokens > l4_quota
            l4_meta = {"source": "belief_store", "count": len(params.beliefs)}
        else:
            filtered_files = self._filter_memory_scope(params.memory_files, scenario_config["L4_scope"])
            l4_content, l4_meta = self._build_layer_4(params.current_input, filtered_files, bg)
            l4_tokens = TokenCounter.count(l4_content)
            l4_quota = self._quota(4)
            l4_truncated = l4_tokens > l4_quota
        audit["L4"] = {"tokens": min(l4_tokens, l4_quota), "truncated": l4_truncated, "meta": l4_meta}

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

        # Step 7: 组装 + 最终校验
        messages = self._assemble_messages(l0, l1, l2, l3, l4_content, l5_result, budget_status)
        messages = self._sanitize(messages)

        total_tokens = TokenCounter.count_messages(messages)
        if total_tokens > self.model_limit - self.output_reserve:
            l5_fallback = self._build_layer_5(params.dialogue_history[-3:], params.current_input, remaining)
            messages = self._assemble_messages(l0, l1, l2, l3, l4_content, l5_fallback, budget_status)
            messages = self._sanitize(messages)

        audit["total_tokens"] = TokenCounter.count_messages(messages)
        audit["model_limit"] = self.model_limit

        return BuildResult(messages=messages, audit=audit, budget_status=budget_status)

    # ============================================================
    # Layer 0-5 实现
    # ============================================================

    @staticmethod
    def _make_hashable(value):
        """将不可哈希类型（如 list/dict）转为可哈希，用于 checksum 计算"""
        if isinstance(value, list):
            return tuple(ContextBuilder._make_hashable(v) for v in value)
        if isinstance(value, dict):
            return tuple(sorted((k, ContextBuilder._make_hashable(v)) for k, v in value.items()))
        if isinstance(value, set):
            return frozenset(value)
        return value

    def _compute_checksum(self, identity: dict) -> int:
        hashable = tuple(sorted((k, self._make_hashable(v)) for k, v in identity.items()))
        return hash(hashable)

    def _build_layer_0(self, identity: dict, background: dict | None = None) -> LayerResult:
        current_checksum = self._compute_checksum(identity)
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

        # 注入 quirks
        bg = background or {}
        quirks = bg.get("quirks", [])
        if quirks:
            prompt += "\n你的性格特点：\n" + "\n".join(f"- {q}" for q in quirks)

        content = f"【系统角色】\n{prompt}"
        tokens = TokenCounter.count(content)
        quota = self._quota(0)
        if tokens > quota:
            return LayerResult(content=content, tokens=tokens, errors=["Layer 0 exceeds quota"])
        return LayerResult(content=content, tokens=tokens)

    def _build_layer_1(self, world_state: dict, background: dict | None = None) -> LayerResult:
        event_text = world_state.get('events', '无特殊事件')
        weather = world_state.get('weather', '晴')

        # 注入 event_reactions
        bg = background or {}
        event_reactions = bg.get("event_reactions", {})
        if event_text != "无特殊事件" and event_reactions:
            matched = []
            for event_key, reaction in event_reactions.items():
                if isinstance(event_key, str) and event_key in event_text.lower():
                    matched.append(reaction)
            if matched:
                event_text += "。你的反应：" + "；".join(matched)

        content = (
            f"【世界信息】\n"
            f"当前时间：Day {world_state.get('day', '?')}, {world_state.get('hour', '?')}:00。"
            f"天气：{weather}。"
            f"今日事件：{event_text}。"
        )
        tokens = TokenCounter.count(content)
        quota = self._quota(1)
        truncated = tokens > quota
        if truncated:
            content = (
                f"【世界信息】\n"
                f"当前时间：Day {world_state.get('day', '?')}, {world_state.get('hour', '?')}:00。"
                f"天气：{weather}。"
            )
            tokens = TokenCounter.count(content)
        return LayerResult(content=content, tokens=tokens, truncated=truncated)

    def _build_layer_2(self, npc_state, background: dict | None = None) -> LayerResult:
        d = npc_state.describe()
        content = (
            f"【自身状态】\n"
            f"{d['health']}。{d['hunger']}。{d['fatigue']}。{d['mood']}。"
        )

        # 注入 state_reactions
        bg = background or {}
        state_reactions = bg.get("state_reactions", {})
        reactions = []
        if npc_state.mood < 40 and "mood_low" in state_reactions:
            reactions.append(state_reactions["mood_low"])
        if npc_state.hunger < 40 and "hunger_low" in state_reactions:
            reactions.append(state_reactions["hunger_low"])
        if npc_state.fatigue > 60 and "fatigue_high" in state_reactions:
            reactions.append(state_reactions["fatigue_high"])
        if reactions:
            content += " 由于当前状态：" + "；".join(reactions)

        tokens = TokenCounter.count(content)
        quota = self._quota(2)
        truncated = tokens > quota
        if truncated:
            content = f"【自身状态】\n{d['health']}。{d['mood']}。"
            tokens = TokenCounter.count(content)
        return LayerResult(content=content, tokens=tokens, truncated=truncated)

    def _build_layer_3(self, interlocutor: dict, background: dict | None = None) -> LayerResult:
        parts = [f"【对方信息】\n你正在与{interlocutor.get('name', '某人')}对话。"]
        if interlocutor.get("summary"):
            parts.append(f"你对ta的印象：{interlocutor['summary']}")
        if interlocutor.get("visible_state"):
            parts.append(f"ta当前状态：{interlocutor['visible_state']}")

        # 注入 relationships（当 interlocutor 是已知 NPC 时）
        bg = background or {}
        relationships = bg.get("relationships", {})
        interlocutor_id = interlocutor.get("id", "")
        if interlocutor_id and interlocutor_id in relationships:
            rel = relationships[interlocutor_id]
            if isinstance(rel, dict):
                if rel.get("attitude"):
                    parts.append(f"你对ta的态度：{rel['attitude']}")
                if "trust_level" in rel:
                    parts.append(f"信任等级：{rel['trust_level']}/10")
                history = rel.get("shared_history", "")
                if history:
                    parts.append(f"共同经历：{history}")

        content = "\n".join(parts)
        tokens = TokenCounter.count(content)
        quota = self._quota(3)
        truncated = tokens > quota
        if truncated:
            content = parts[0]
            tokens = TokenCounter.count(content)
        return LayerResult(content=content, tokens=tokens, truncated=truncated)

    def _filter_memory_scope(self, memory_files: dict, scope: str) -> dict:
        if scope == "full":
            return memory_files
        if scope == "agent_only":
            return {k: v for k, v in memory_files.items() if "agent_mem" in k}
        if scope == "autonomous":
            return {k: v for k, v in memory_files.items() if "agent_mem" in k or "self" in k}
        return memory_files

    def _build_layer_4(self, trigger: str, memory_files: dict, background: dict | None = None) -> tuple:
        quota = self._quota(4)
        bg = background or {}

        # 从 background 构建合成记忆条目，加入检索池
        synthetic_parts = []

        # 1. dialogue_topics: 关键词匹配
        for topic_key, topic_data in bg.get("dialogue_topics", {}).items():
            if not isinstance(topic_data, dict):
                continue
            tone = topic_data.get("tone", "")
            samples = topic_data.get("sample_lines", [])
            trigger_cond = topic_data.get("trigger_condition", "")
            if samples:
                synthetic_parts.append(
                    f"话题「{topic_key}」：语气 {tone}。"
                    f"参考话术：{'；'.join(samples[:2])}"
                    + (f" 触发条件：{trigger_cond}" if trigger_cond else "")
                )

        # information_layers 是外部对 NPC 的描述元数据，不是 NPC 自身记忆，
        # 不应注入到记忆检索中

        augmented_files = dict(memory_files)
        if synthetic_parts:
            augmented_files["_background_knowledge.md"] = "\n\n".join(synthetic_parts)

        return self._get_retriever().retrieve(trigger, augmented_files, max_tokens=quota)

    def _build_layer_5(self, dialogue_history: list, current_input: str, remaining: int) -> LayerResult:
        messages = []
        used = 0

        if remaining < self.tired_threshold:
            return LayerResult(content=[], tokens=0, truncated=False)

        current_tokens = TokenCounter.count(current_input)
        if current_tokens <= remaining:
            messages.append({"role": "user", "content": current_input})
            remaining -= current_tokens
            used += current_tokens

        kept = []
        for turn in reversed(dialogue_history):
            t = TokenCounter.count(turn.get("content", ""))
            if remaining - t < 0:
                break
            kept.insert(0, turn)
            remaining -= t
            used += t

        if len(dialogue_history) > self.compress_threshold and len(kept) < len(dialogue_history):
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
        sanitized = []
        for m in messages:
            content = m.get("content", "")
            for kw in self.injection_blacklist:
                if kw.lower() in content.lower():
                    content = content.replace(kw, "[filtered]")
            sanitized.append({**m, "content": content})
        return sanitized

    # ============================================================
    # 信念驱动 v2 层方法
    # ============================================================

    def _build_layer_1_v2(self, world_state: dict) -> LayerResult:
        content = (
            f"【世界信息】\n"
            f"当前时间：Day {world_state.get('day', '?')}, {world_state.get('hour', '?')}:00。"
            f"天气：{world_state.get('weather', '晴')}。"
        )
        tokens = TokenCounter.count(content)
        return LayerResult(content=content, tokens=tokens)

    def _build_layer_2_v2(self, npc_state, reasoning_beliefs: list, background: dict) -> LayerResult:
        d = npc_state.describe()
        parts = [
            "【自身状态】",
            f"{d['health']}。{d['hunger']}。{d['fatigue']}。{d['mood']}。",
        ]

        state_reactions = background.get("state_reactions", {})
        reactions = []
        if npc_state.mood < 40 and "mood_low" in state_reactions:
            reactions.append(state_reactions["mood_low"])
        if npc_state.hunger < 40 and "hunger_low" in state_reactions:
            reactions.append(state_reactions["hunger_low"])
        if npc_state.fatigue > 60 and "fatigue_high" in state_reactions:
            reactions.append(state_reactions["fatigue_high"])
        if reactions:
            parts.append("由于当前状态：" + "；".join(reactions))

        if reasoning_beliefs:
            parts.append("\n【你的近期决策】")
            for b in reasoning_beliefs[-3:]:
                parts.append(f"- {b.content}")

        content = "\n".join(parts)
        tokens = TokenCounter.count(content)
        return LayerResult(content=content, tokens=tokens)

    def _build_layer_3_v2(self, interlocutor: dict, interlocutor_beliefs: list) -> LayerResult:
        name = interlocutor.get("name", "某人")
        parts = [f"【对方信息】\n你正在与{name}对话。"]

        if interlocutor_beliefs:
            parts.append("你对ta的了解：")
            for b in interlocutor_beliefs[:5]:
                parts.append(f"- {b.content}")

        content = "\n".join(parts)
        tokens = TokenCounter.count(content)
        quota = self._quota(3)
        truncated = tokens > quota
        if truncated:
            content = parts[0] + "\n" + "\n".join(parts[1:4])
            tokens = TokenCounter.count(content)
        return LayerResult(content=content, tokens=tokens, truncated=truncated)

    def _format_beliefs(self, beliefs: list) -> str:
        high = [b for b in beliefs if b.confidence == "high"]
        medium = [b for b in beliefs if b.confidence == "medium"]
        low = [b for b in beliefs if b.confidence == "low"]

        parts = []
        if high:
            parts.append("【你确定的事】")
            for b in high:
                parts.append(f"- {b.content}")
        if medium or low:
            parts.append("【你听说的（未证实）】")
            for b in medium + low:
                source_hint = ""
                if b.source.startswith("told_by:"):
                    teller = b.source.replace("told_by:", "")
                    source_hint = f"（{teller}说的）"
                parts.append(f"- {b.content}{source_hint}")
        return "\n".join(parts)


# 模块级 TokenCounter 引用（类方法中延迟导入以避免循环依赖）
from server.llm.token_counter import TokenCounter  # noqa: E402
