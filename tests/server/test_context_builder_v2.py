import pytest
from server.llm.context_builder import ContextBuilder, BuildParams, ScenarioType
from server.models.npc_state import NPCState
from server.models.belief import Belief


def _make_beliefs():
    return [
        Belief(
            content="昨天下午你在田里看到一个陌生商人往市场方向走去",
            source="witnessed", confidence="high",
            acquired_at={"day": 2, "hour": 14}, about=["world"],
        ),
        Belief(
            content="盖斯上周告诉你最近有外地人在打听村子的事",
            source="told_by:bartender", confidence="medium",
            acquired_at={"day": 1, "hour": 18}, about=["world"],
        ),
        Belief(
            content="你今早决定去市场看看，想亲眼确认商人是否真在卖违禁品",
            source="witnessed", confidence="high",
            acquired_at={"day": 3, "hour": 7}, about=["farmer"],
        ),
    ]


def _make_interlocutor_beliefs():
    return [
        Belief(
            content="盖斯是酒馆老板，你和他认识三年了",
            source="witnessed", confidence="high",
            acquired_at={"day": 1, "hour": 0}, about=["bartender"],
        ),
        Belief(
            content="盖斯最近似乎心事重重",
            source="witnessed", confidence="high",
            acquired_at={"day": 2, "hour": 20}, about=["bartender"],
        ),
    ]


class TestContextBuilderV2:
    def setup_method(self):
        self.builder = ContextBuilder(model_limit=4096, output_reserve=500)
        self.identity = {
            "name": "乔治",
            "daily_habits": "每天清晨起来先去田地查看庄稼。",
            "core_motivation": "你热爱土地，靠双手养活自己。",
            "speaking_style": "朴实直率，偶尔用农谚。",
            "secret": "你曾在森林里发现过一个隐秘洞穴",
        }

    def test_belief_injection_in_l1(self):
        """L1 不再注入事件文本，只保留时间和天气。"""
        params = BuildParams(
            identity=self.identity,
            npc_state=NPCState(),
            world_state={"day": 3, "hour": 10, "weather": "晴", "events": "旅行商人到来"},
            beliefs=_make_beliefs(),
            scenario=ScenarioType.AUTONOMOUS_DECISION,
            current_input="你正在思考接下来做什么。",
        )
        result = self.builder.build(params)
        # 找到 L1 所在的系统消息（第二个 system message）
        system_msgs = [m for m in result.messages if m["role"] == "system"]
        assert len(system_msgs) >= 2
        l1_l4_text = system_msgs[1]["content"]
        # 事件文本不应直接出现在世界信息中（由信念提供）
        assert "旅行商人到来" not in l1_l4_text.split("【你确定的事】")[0] if "【你确定的事】" in l1_l4_text else True

    def test_belief_categories_in_context(self):
        """信念按 confidence 分级呈现。"""
        params = BuildParams(
            identity=self.identity,
            npc_state=NPCState(),
            world_state={"day": 3, "hour": 10, "weather": "晴"},
            beliefs=_make_beliefs(),
            scenario=ScenarioType.AUTONOMOUS_DECISION,
            current_input="你正在思考接下来做什么。",
        )
        result = self.builder.build(params)
        messages_text = " ".join(m["content"] for m in result.messages)
        assert "你确定的事" in messages_text
        assert "你听说的" in messages_text
        assert "陌生商人" in messages_text

    def test_interlocutor_beliefs_in_l3(self):
        """L3 使用对对方的信念而非 YAML 静态数据。"""
        params = BuildParams(
            identity=self.identity,
            npc_state=NPCState(),
            world_state={"day": 3, "hour": 14, "weather": "晴"},
            beliefs=_make_beliefs(),
            interlocutor_beliefs=_make_interlocutor_beliefs(),
            interlocutor={"id": "bartender", "name": "盖斯"},
            scenario=ScenarioType.PLAYER_DIALOGUE,
            current_input="你好啊乔治",
            dialogue_history=[],
        )
        result = self.builder.build(params)
        messages_text = " ".join(m["content"] for m in result.messages)
        assert "认识三年" in messages_text
        assert "心事重重" in messages_text

    def test_reasoning_beliefs_in_l2(self):
        """L2 包含最近的 reasoning 信念。"""
        reasoning_beliefs = [
            Belief(
                content="你今早决定去市场是因为想确认违禁品的事",
                source="witnessed", confidence="high",
                acquired_at={"day": 3, "hour": 7}, about=["farmer"],
            ),
        ]
        params = BuildParams(
            identity=self.identity,
            npc_state=NPCState(),
            world_state={"day": 3, "hour": 10, "weather": "晴"},
            beliefs=_make_beliefs(),
            reasoning_beliefs=reasoning_beliefs,
            scenario=ScenarioType.AUTONOMOUS_DECISION,
            current_input="你正在思考。",
        )
        result = self.builder.build(params)
        messages_text = " ".join(m["content"] for m in result.messages)
        assert "你的近期决策" in messages_text
        assert "确认违禁品" in messages_text

    def test_backward_compat_no_beliefs(self):
        """beliefs 为空时退化为旧行为（不崩溃）。"""
        params = BuildParams(
            identity=self.identity,
            npc_state=NPCState(),
            world_state={"day": 1, "hour": 8, "weather": "晴", "events": "无特殊事件"},
            scenario=ScenarioType.AUTONOMOUS_DECISION,
            current_input="你正在思考。",
        )
        result = self.builder.build(params)
        assert len(result.messages) >= 2
        assert result.audit["L0"]["tokens"] > 0

    def test_empty_beliefs_no_header(self):
        """没有信念时不注入空的分类标题。"""
        params = BuildParams(
            identity=self.identity,
            npc_state=NPCState(),
            world_state={"day": 1, "hour": 8, "weather": "晴"},
            beliefs=[],
            scenario=ScenarioType.AUTONOMOUS_DECISION,
            current_input="你正在思考。",
        )
        result = self.builder.build(params)
        messages_text = " ".join(m["content"] for m in result.messages)
        assert "你确定的事" not in messages_text
