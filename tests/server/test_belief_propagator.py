import pytest
import tempfile
from server.models.belief import Belief
from server.core.belief_store import BeliefStore
from server.core.belief_propagator import BeliefPropagator


class TestBeliefPropagator:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.stores = {
            "farmer": BeliefStore(npc_id="farmer", base_path=self.tmpdir),
            "bartender": BeliefStore(npc_id="bartender", base_path=self.tmpdir),
        }
        self.propagator = BeliefPropagator(belief_stores=self.stores)

    def test_propagate_dialogue_summary(self):
        """对话摘要作为 told_by 信念传递给双方。"""
        self.propagator.propagate_from_dialogue(
            speaker_id="farmer",
            listener_id="bartender",
            summary="乔治告诉盖斯他在田里发现了一把生锈的剑",
            game_time={"day": 2, "hour": 14},
        )
        bartender_beliefs = self.stores["bartender"].get_all()
        assert len(bartender_beliefs) == 1
        assert bartender_beliefs[0].source == "told_by:farmer"
        assert bartender_beliefs[0].confidence == "medium"
        assert "生锈的剑" in bartender_beliefs[0].content

    def test_both_participants_get_dialogue_belief(self):
        """双方都获得关于此对话的信念。"""
        self.propagator.propagate_from_dialogue(
            speaker_id="farmer",
            listener_id="bartender",
            summary="两人讨论了最近的天气和收成",
            game_time={"day": 2, "hour": 14},
        )
        farmer_beliefs = self.stores["farmer"].get_all()
        assert len(farmer_beliefs) == 1
        assert farmer_beliefs[0].source == "witnessed"
        assert farmer_beliefs[0].confidence == "high"

        bartender_beliefs = self.stores["bartender"].get_all()
        assert len(bartender_beliefs) == 1
        assert bartender_beliefs[0].source == "told_by:farmer"

    def test_share_specific_belief(self):
        """NPC 主动分享一条已有信念给对方。"""
        original = Belief(
            content="商人在卖违禁品",
            source="witnessed", confidence="high",
            acquired_at={"day": 1, "hour": 10}, about=["world"],
        )
        self.stores["farmer"].add(original)

        self.propagator.share_belief(
            from_npc="farmer",
            to_npc="bartender",
            belief=original,
            new_content="听说商人在卖违禁品",
            game_time={"day": 2, "hour": 14},
        )

        bartender_beliefs = self.stores["bartender"].get_all()
        assert len(bartender_beliefs) == 1
        assert bartender_beliefs[0].confidence == "medium"
        assert bartender_beliefs[0].source == "told_by:farmer"

    def test_duplicate_share_ignored(self):
        """重复分享同一信念不产生新条目。"""
        self.propagator.propagate_from_dialogue(
            speaker_id="farmer",
            listener_id="bartender",
            summary="乔治说天气不好",
            game_time={"day": 2, "hour": 14},
        )
        self.propagator.propagate_from_dialogue(
            speaker_id="farmer",
            listener_id="bartender",
            summary="乔治说天气不好",
            game_time={"day": 2, "hour": 15},
        )
        bartender_beliefs = self.stores["bartender"].get_all()
        assert len(bartender_beliefs) == 1

    def test_unknown_npc_safe(self):
        """未知 NPC ID 不崩溃。"""
        self.propagator.propagate_from_dialogue(
            speaker_id="unknown",
            listener_id="bartender",
            summary="神秘人说了什么",
            game_time={"day": 1, "hour": 10},
        )
        bartender_beliefs = self.stores["bartender"].get_all()
        assert len(bartender_beliefs) == 1
