import pytest
import tempfile
from server.models.belief import Belief
from server.core.belief_store import BeliefStore


class TestBeliefStore:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.store = BeliefStore(npc_id="farmer", base_path=self.tmpdir)

    def test_add_and_get(self):
        b = Belief(
            content="盖斯今天在酿啤酒",
            source="witnessed",
            confidence="high",
            acquired_at={"day": 1, "hour": 10},
            about=["bartender"],
        )
        self.store.add(b)
        retrieved = self.store.get(b.id)
        assert retrieved is not None
        assert retrieved.content == b.content

    def test_get_by_about(self):
        self.store.add(Belief(
            content="农夫在田里",
            source="witnessed", confidence="high",
            acquired_at={"day": 1, "hour": 8}, about=["farmer"],
        ))
        self.store.add(Belief(
            content="酒保在酿酒",
            source="witnessed", confidence="high",
            acquired_at={"day": 1, "hour": 9}, about=["bartender"],
        ))
        farmer_beliefs = self.store.get_by_about("farmer")
        assert len(farmer_beliefs) == 1
        assert "农夫" in farmer_beliefs[0].content

    def test_get_active_filters_expired(self):
        self.store.add(Belief(
            content="新鲜消息",
            source="overheard", confidence="low",
            acquired_at={"day": 5, "hour": 10}, about=["world"],
        ))
        self.store.add(Belief(
            content="过期消息",
            source="overheard", confidence="low",
            acquired_at={"day": 1, "hour": 10}, about=["world"],
        ))
        active = self.store.get_active(current_day=5)
        assert len(active) == 1
        assert active[0].content == "新鲜消息"

    def test_high_confidence_never_expires(self):
        self.store.add(Belief(
            content="亲眼所见",
            source="witnessed", confidence="high",
            acquired_at={"day": 1, "hour": 10}, about=["world"],
        ))
        active = self.store.get_active(current_day=100)
        assert len(active) == 1

    def test_duplicate_detection(self):
        self.store.add(Belief(
            content="盖斯在酿酒",
            source="told_by:player", confidence="medium",
            acquired_at={"day": 1, "hour": 10}, about=["bartender"],
        ))
        duplicate = Belief(
            content="盖斯在酿酒",
            source="told_by:player", confidence="medium",
            acquired_at={"day": 1, "hour": 11}, about=["bartender"],
        )
        added = self.store.add(duplicate)
        assert added is False
        assert len(self.store.get_all()) == 1

    def test_conflict_detection(self):
        b1 = Belief(
            content="商人是好人",
            source="witnessed", confidence="high",
            acquired_at={"day": 1, "hour": 10}, about=["traveler"],
        )
        b2 = Belief(
            content="商人在卖违禁品",
            source="told_by:farmer", confidence="medium",
            acquired_at={"day": 2, "hour": 10}, about=["traveler"],
        )
        self.store.add(b1)
        self.store.add(b2)
        all_beliefs = self.store.get_by_about("traveler")
        assert len(all_beliefs) == 2

    def test_persistence(self):
        b = Belief(
            content="持久化测试",
            source="witnessed", confidence="high",
            acquired_at={"day": 1, "hour": 8}, about=["world"],
        )
        self.store.add(b)

        store2 = BeliefStore(npc_id="farmer", base_path=self.tmpdir)
        assert store2.get(b.id) is not None

    def test_get_for_context_priority(self):
        self.store.add(Belief(
            content="低优先级旧消息",
            source="overheard", confidence="low",
            acquired_at={"day": 1, "hour": 8}, about=["world"],
        ))
        self.store.add(Belief(
            content="高优先级新消息",
            source="witnessed", confidence="high",
            acquired_at={"day": 3, "hour": 14}, about=["world"],
        ))
        self.store.add(Belief(
            content="中优先级消息",
            source="told_by:farmer", confidence="medium",
            acquired_at={"day": 2, "hour": 10}, about=["world"],
        ))
        ordered = self.store.get_for_context(current_day=3, max_count=10)
        assert ordered[0].content == "高优先级新消息"
        assert ordered[1].content == "中优先级消息"
