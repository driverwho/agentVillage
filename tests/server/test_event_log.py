import pytest
import tempfile
from server.models.event import GameEvent
from server.core.event_log import EventLog


class TestEventLog:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.log = EventLog(base_path=self.tmpdir)

    def test_append_and_get_by_id(self):
        e = GameEvent(
            type="action", timestamp={"day": 1, "hour": 8},
            actor="farmer", location="field",
            content="乔治开始耕地", witnesses=["farmer"],
            visibility="location",
        )
        self.log.append(e)
        retrieved = self.log.get_by_id(e.id)
        assert retrieved is not None
        assert retrieved.content == "乔治开始耕地"

    def test_query_by_day(self):
        for hour in [8, 10, 14]:
            self.log.append(GameEvent(
                type="action", timestamp={"day": 2, "hour": hour},
                actor="farmer", location="field",
                content=f"活动 hour={hour}", witnesses=["farmer"],
                visibility="location",
            ))
        self.log.append(GameEvent(
            type="action", timestamp={"day": 3, "hour": 8},
            actor="farmer", location="field",
            content="第三天活动", witnesses=["farmer"],
            visibility="location",
        ))
        day2_events = self.log.query(day=2)
        assert len(day2_events) == 3

    def test_query_by_actor(self):
        self.log.append(GameEvent(
            type="action", timestamp={"day": 1, "hour": 8},
            actor="farmer", location="field",
            content="农夫活动", witnesses=["farmer"],
            visibility="location",
        ))
        self.log.append(GameEvent(
            type="action", timestamp={"day": 1, "hour": 9},
            actor="bartender", location="tavern",
            content="酒保活动", witnesses=["bartender"],
            visibility="location",
        ))
        farmer_events = self.log.query(actor="farmer")
        assert len(farmer_events) == 1
        assert farmer_events[0].actor == "farmer"

    def test_query_by_location(self):
        self.log.append(GameEvent(
            type="action", timestamp={"day": 1, "hour": 8},
            actor="farmer", location="tavern",
            content="农夫在酒馆", witnesses=["farmer", "bartender"],
            visibility="location",
        ))
        tavern_events = self.log.query(location="tavern")
        assert len(tavern_events) == 1

    def test_query_by_witness(self):
        self.log.append(GameEvent(
            type="dialogue", timestamp={"day": 1, "hour": 14},
            actor="farmer", location="tavern",
            content="农夫和酒保聊天", witnesses=["farmer", "bartender"],
            visibility="location",
        ))
        self.log.append(GameEvent(
            type="action", timestamp={"day": 1, "hour": 15},
            actor="farmer", location="field",
            content="农夫独自耕地", witnesses=["farmer"],
            visibility="location",
        ))
        bartender_witnessed = self.log.query(witness="bartender")
        assert len(bartender_witnessed) == 1
        assert "聊天" in bartender_witnessed[0].content

    def test_persistence_across_instances(self):
        e = GameEvent(
            type="action", timestamp={"day": 1, "hour": 8},
            actor="farmer", location="field",
            content="持久化测试", witnesses=["farmer"],
            visibility="location",
        )
        self.log.append(e)

        log2 = EventLog(base_path=self.tmpdir)
        retrieved = log2.get_by_id(e.id)
        assert retrieved is not None
        assert retrieved.content == "持久化测试"

    def test_get_recent(self):
        for i in range(10):
            self.log.append(GameEvent(
                type="action", timestamp={"day": 1, "hour": i},
                actor="farmer", location="field",
                content=f"事件{i}", witnesses=["farmer"],
                visibility="location",
            ))
        recent = self.log.get_recent(limit=3)
        assert len(recent) == 3
        assert recent[0].content == "事件9"
