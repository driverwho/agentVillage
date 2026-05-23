import pytest
from unittest.mock import patch
from server.core.event_engine import EventDef, ActiveEvent, EventState, EventEngine
from server.models.game_time import GameTime


def _make_event(id="rain", probability=1.0, duration=4, category="weather",
                conditions=None):
    return EventDef(
        id=id, name="测试事件", category=category,
        probability=probability, duration_hours=duration,
        conditions=conditions or {}, description="测试描述",
    )


def test_tick_generates_event_when_probability_is_1():
    engine = EventEngine(event_defs=[_make_event()], state=EventState())
    game_time = GameTime(day=1, hour=8)
    active = engine.tick(game_time)
    assert len(active) == 1
    assert active[0].id == "rain"


def test_tick_respects_cooldown():
    state = EventState(cooldowns={"rain": 3})
    engine = EventEngine(event_defs=[_make_event()], state=state)
    game_time = GameTime(day=2, hour=8)
    active = engine.tick(game_time)
    assert len(active) == 0


def test_tick_removes_expired_events():
    expired = ActiveEvent(
        id="rain", name="雨", description="下雨",
        started_day=1, started_hour=6, expires_day=1, expires_hour=10,
    )
    state = EventState(active_events=[expired])
    engine = EventEngine(event_defs=[], state=state)
    game_time = GameTime(day=1, hour=10)
    active = engine.tick(game_time)
    assert len(active) == 0


def test_tick_respects_min_day():
    engine = EventEngine(
        event_defs=[_make_event(conditions={"min_day": 3})],
        state=EventState(),
    )
    active = engine.tick(GameTime(day=2, hour=8))
    assert len(active) == 0


def test_tick_respects_hour_range():
    engine = EventEngine(
        event_defs=[_make_event(conditions={"hour_range": [6, 10]})],
        state=EventState(),
    )
    assert len(engine.tick(GameTime(day=1, hour=8))) == 1


def test_tick_rejects_outside_hour_range():
    engine = EventEngine(
        event_defs=[_make_event(conditions={"hour_range": [6, 10]})],
        state=EventState(),
    )
    assert len(engine.tick(GameTime(day=1, hour=12))) == 0


def test_tick_respects_max_active_events():
    events = [_make_event(id=f"e{i}", conditions={"max_active_events": 2})
              for i in range(5)]
    engine = EventEngine(event_defs=events, state=EventState())
    active = engine.tick(GameTime(day=1, hour=8))
    assert len(active) <= 2


def test_get_current_weather_default():
    engine = EventEngine(event_defs=[], state=EventState())
    assert engine.get_current_weather() == "晴"


def test_get_current_weather_with_event():
    state = EventState(active_events=[
        ActiveEvent(id="heavy_rain", name="暴雨", description="倾盆大雨",
                    started_day=1, started_hour=6, expires_day=1, expires_hour=14),
    ])
    engine = EventEngine(event_defs=[], state=state)
    assert engine.get_current_weather() == "暴雨"


def test_get_world_events_text_empty():
    engine = EventEngine(event_defs=[], state=EventState())
    assert engine.get_world_events_text() == "今日无事"


def test_get_world_events_text_with_events():
    state = EventState(active_events=[
        ActiveEvent(id="merchant", name="商人", description="旅行商人在市场",
                    started_day=1, started_hour=8, expires_day=1, expires_hour=16),
    ])
    engine = EventEngine(event_defs=[], state=state)
    text = engine.get_world_events_text()
    assert "旅行商人在市场" in text


def test_load_event_defs(tmp_path):
    import yaml
    yaml_content = {
        "category": "weather",
        "events": [
            {"id": "rain", "name": "雨", "probability": 0.1,
             "duration_hours": 4, "conditions": {}, "description": "下雨了"}
        ]
    }
    (tmp_path / "weather.yaml").write_text(
        yaml.dump(yaml_content, allow_unicode=True), encoding="utf-8"
    )
    from server.core.event_engine import load_event_defs
    defs = load_event_defs(str(tmp_path))
    assert len(defs) == 1
    assert defs[0].id == "rain"
    assert defs[0].category == "weather"


def test_load_event_defs_from_real_data():
    from server.core.event_engine import load_event_defs
    defs = load_event_defs("server/data/events")
    assert len(defs) == 15
    categories = {d.category for d in defs}
    assert categories == {"weather", "visitor", "discovery", "npc_trigger"}
