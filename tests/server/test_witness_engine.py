import pytest
import tempfile
from server.models.event import GameEvent
from server.models.belief import Belief
from server.core.belief_store import BeliefStore
from server.core.witness_engine import WitnessEngine


class TestWitnessEngine:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.stores = {
            "farmer": BeliefStore(npc_id="farmer", base_path=self.tmpdir),
            "bartender": BeliefStore(npc_id="bartender", base_path=self.tmpdir),
        }
        self.engine = WitnessEngine(belief_stores=self.stores)

    def test_location_event_only_witnesses_get_belief(self):
        event = GameEvent(
            type="action", timestamp={"day": 1, "hour": 10},
            actor="farmer", location="field",
            content="乔治在田地里发现了一把生锈的剑",
            witnesses=["farmer"],
            visibility="location",
        )
        self.engine.process_event(event)

        farmer_beliefs = self.stores["farmer"].get_all()
        bartender_beliefs = self.stores["bartender"].get_all()
        assert len(farmer_beliefs) == 1
        assert farmer_beliefs[0].content == "乔治在田地里发现了一把生锈的剑"
        assert farmer_beliefs[0].confidence == "high"
        assert farmer_beliefs[0].source == "witnessed"
        assert len(bartender_beliefs) == 0

    def test_public_event_all_get_belief(self):
        event = GameEvent(
            type="world", timestamp={"day": 2, "hour": 6},
            actor="world", location="village",
            content="暴风雨即将来临",
            witnesses=[],
            visibility="public",
        )
        self.engine.process_event(event)

        for store in self.stores.values():
            beliefs = store.get_all()
            assert len(beliefs) == 1
            assert beliefs[0].content == "暴风雨即将来临"
            assert beliefs[0].confidence == "high"
            assert beliefs[0].source == "witnessed"

    def test_private_event_only_actor_gets_belief(self):
        event = GameEvent(
            type="action", timestamp={"day": 1, "hour": 23},
            actor="farmer", location="forest",
            content="乔治偷偷在森林挖了宝箱",
            witnesses=["farmer", "bartender"],
            visibility="private",
        )
        self.engine.process_event(event)

        farmer_beliefs = self.stores["farmer"].get_all()
        bartender_beliefs = self.stores["bartender"].get_all()
        assert len(farmer_beliefs) == 1
        assert len(bartender_beliefs) == 0

    def test_reasoning_becomes_actor_belief(self):
        event = GameEvent(
            type="action", timestamp={"day": 2, "hour": 14},
            actor="farmer", location="market",
            content="乔治去了市场",
            witnesses=["farmer"],
            visibility="location",
            reasoning="我想亲眼确认商人是否在卖违禁品",
        )
        self.engine.process_event(event)

        farmer_beliefs = self.stores["farmer"].get_all()
        assert len(farmer_beliefs) == 2
        reasoning_belief = [b for b in farmer_beliefs if "确认" in b.content][0]
        assert reasoning_belief.source == "witnessed"
        assert reasoning_belief.confidence == "high"

    def test_dialogue_event_both_witnesses_get_belief(self):
        event = GameEvent(
            type="dialogue", timestamp={"day": 1, "hour": 14},
            actor="farmer", location="tavern",
            content="乔治和盖斯讨论了天气",
            witnesses=["farmer", "bartender"],
            visibility="location",
        )
        self.engine.process_event(event)

        assert len(self.stores["farmer"].get_all()) == 1
        assert len(self.stores["bartender"].get_all()) == 1

    def test_unknown_npc_in_witnesses_ignored(self):
        event = GameEvent(
            type="action", timestamp={"day": 1, "hour": 10},
            actor="unknown_npc", location="field",
            content="神秘人出现了",
            witnesses=["unknown_npc", "farmer"],
            visibility="location",
        )
        self.engine.process_event(event)
        assert len(self.stores["farmer"].get_all()) == 1

    def test_duplicate_event_not_duplicated_belief(self):
        event = GameEvent(
            type="action", timestamp={"day": 1, "hour": 10},
            actor="farmer", location="field",
            content="乔治耕地",
            witnesses=["farmer"],
            visibility="location",
        )
        self.engine.process_event(event)
        self.engine.process_event(event)
        assert len(self.stores["farmer"].get_all()) == 1
