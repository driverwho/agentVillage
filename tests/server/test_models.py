import pytest
from server.models.game_time import GameTime
from server.models.npc_state import NPCState
from server.models.player_state import PlayerState


def test_game_time_tick():
    t = GameTime(day=1, hour=23, minute=0)
    t.tick(120)
    assert t.day == 2
    assert t.hour == 1
    assert t.minute == 0


def test_game_time_to_dict():
    t = GameTime(day=3, hour=14, minute=30)
    d = t.to_dict()
    assert d == {"day": 3, "hour": 14, "minute": 30}


def test_game_time_from_dict():
    t = GameTime.from_dict({"day": 2, "hour": 8, "minute": 15})
    assert t.day == 2
    assert t.hour == 8


def test_npc_state_describe():
    state = NPCState(health=80, hunger=30, fatigue=60)
    desc = state.describe()
    assert "身体不错" in desc["health"]
    assert "肚子在咕咕叫" in desc["hunger"]
    assert "有些累了" in desc["fatigue"]


def test_player_state_visibility_basic():
    ps = PlayerState(name="test", gold=100)
    visible = ps.get_visible_state(["basic"])
    assert "basic" in visible
    assert "social" not in visible
    assert "wealth" not in visible


def test_player_state_visibility_social():
    ps = PlayerState(name="test", reputation=80)
    visible = ps.get_visible_state(["basic", "social"])
    assert "social" in visible
    assert visible["social"]["reputation"] == 80


def test_player_state_visibility_wealth():
    ps = PlayerState(name="test", gold=50, items=["seed"])
    visible = ps.get_visible_state(["basic", "wealth"])
    assert "wealth" in visible
    assert visible["wealth"]["gold"] == 50
    assert "seed" in visible["wealth"]["items"]
    assert "social" not in visible
