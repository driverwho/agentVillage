import pytest
from server.models.belief import Belief


class TestBeliefModel:
    def test_create_witnessed_belief(self):
        b = Belief(
            content="乔治昨天深夜独自去了森林",
            source="witnessed",
            confidence="high",
            acquired_at={"day": 3, "hour": 14},
            about=["farmer"],
        )
        assert b.content == "乔治昨天深夜独自去了森林"
        assert b.source == "witnessed"
        assert b.confidence == "high"
        assert b.id

    def test_create_told_by_belief(self):
        b = Belief(
            content="市场来了一个陌生商人",
            source="told_by:farmer",
            confidence="medium",
            acquired_at={"day": 2, "hour": 10},
            about=["world"],
        )
        assert b.source == "told_by:farmer"
        assert b.confidence == "medium"

    def test_belief_to_dict_roundtrip(self):
        b = Belief(
            content="盖斯在酿酒",
            source="witnessed",
            confidence="high",
            acquired_at={"day": 1, "hour": 8},
            about=["bartender"],
        )
        data = b.to_dict()
        restored = Belief.from_dict(data)
        assert restored.content == b.content
        assert restored.id == b.id
        assert restored.source == b.source

    def test_belief_is_expired_low_confidence(self):
        b = Belief(
            content="听说有人在森林出没",
            source="overheard",
            confidence="low",
            acquired_at={"day": 1, "hour": 10},
            about=["world"],
        )
        assert not b.is_expired(current_day=2)
        assert b.is_expired(current_day=5)

    def test_belief_is_expired_high_never(self):
        b = Belief(
            content="我亲眼看到商人卖违禁品",
            source="witnessed",
            confidence="high",
            acquired_at={"day": 1, "hour": 10},
            about=["world"],
        )
        assert not b.is_expired(current_day=100)

    def test_belief_propagate_downgrades_confidence(self):
        original = Belief(
            content="商人在卖违禁品",
            source="witnessed",
            confidence="high",
            acquired_at={"day": 2, "hour": 14},
            about=["world"],
        )
        propagated = original.propagate(teller_id="farmer", new_content="听说商人在卖违禁品")
        assert propagated.confidence == "medium"
        assert propagated.source == "told_by:farmer"
        assert propagated.content == "听说商人在卖违禁品"
        assert propagated.id != original.id

    def test_belief_propagate_medium_to_low(self):
        b = Belief(
            content="听说有违禁品",
            source="told_by:farmer",
            confidence="medium",
            acquired_at={"day": 2, "hour": 14},
            about=["world"],
        )
        propagated = b.propagate(teller_id="bartender", new_content="据说有违禁品")
        assert propagated.confidence == "low"

    def test_belief_propagate_low_stays_low(self):
        b = Belief(
            content="也许有违禁品",
            source="overheard",
            confidence="low",
            acquired_at={"day": 2, "hour": 14},
            about=["world"],
        )
        propagated = b.propagate(teller_id="bartender", new_content="可能有违禁品")
        assert propagated.confidence == "low"
