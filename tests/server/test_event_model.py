import pytest
from server.models.event import GameEvent


class TestEventModel:
    def test_create_action_event(self):
        e = GameEvent(
            type="action",
            timestamp={"day": 2, "hour": 10},
            actor="farmer",
            location="field",
            content="乔治在田地里劳作了4小时",
            witnesses=["farmer"],
            visibility="location",
        )
        assert e.type == "action"
        assert e.actor == "farmer"
        assert e.id

    def test_create_dialogue_event(self):
        e = GameEvent(
            type="dialogue",
            timestamp={"day": 2, "hour": 14},
            actor="farmer",
            location="tavern",
            content="乔治和盖斯讨论了市场的陌生商人",
            witnesses=["farmer", "bartender"],
            visibility="location",
            reasoning="因为想确认违禁品的事",
        )
        assert e.witnesses == ["farmer", "bartender"]
        assert e.reasoning == "因为想确认违禁品的事"

    def test_create_public_event(self):
        e = GameEvent(
            type="world",
            timestamp={"day": 3, "hour": 6},
            actor="world",
            location="village",
            content="村口钟声响起，宣布新的一天",
            witnesses=[],
            visibility="public",
        )
        assert e.visibility == "public"

    def test_event_to_dict_roundtrip(self):
        e = GameEvent(
            type="movement",
            timestamp={"day": 1, "hour": 18},
            actor="farmer",
            location="tavern",
            content="乔治从田地来到了酒馆",
            witnesses=["farmer", "bartender"],
            visibility="location",
        )
        data = e.to_dict()
        restored = GameEvent.from_dict(data)
        assert restored.id == e.id
        assert restored.type == e.type
        assert restored.witnesses == e.witnesses

    def test_event_private_visibility(self):
        e = GameEvent(
            type="action",
            timestamp={"day": 2, "hour": 23},
            actor="farmer",
            location="forest",
            content="乔治独自在森林里挖东西",
            witnesses=["farmer"],
            visibility="private",
        )
        assert e.visibility == "private"
