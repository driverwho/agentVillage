import pytest
from unittest.mock import MagicMock, AsyncMock
from server.hooks.interaction_hook import InteractionHook, InteractionCounter, should_interact
from server.models.game_time import GameTime
from server.core.location_registry import LocationRegistry


def _make_npc(npc_id, location="home", status="idle", relationships=None):
    npc = MagicMock()
    npc.id = npc_id
    npc.agent_id = npc_id
    npc.location = location
    npc.activity_state = MagicMock()
    npc.activity_state.status = status
    npc.background = {"relationships": relationships or {}}
    return npc


def test_interaction_counter_initial_zero():
    counter = InteractionCounter()
    pair = ("bartender", "farmer")
    assert counter.get_today_count(pair, day=1) == 0


def test_interaction_counter_increment():
    counter = InteractionCounter()
    pair = ("bartender", "farmer")
    counter.increment(pair, day=1)
    assert counter.get_today_count(pair, day=1) == 1
    counter.increment(pair, day=1)
    assert counter.get_today_count(pair, day=1) == 2


def test_interaction_counter_different_day():
    counter = InteractionCounter()
    pair = ("bartender", "farmer")
    counter.increment(pair, day=1)
    assert counter.get_today_count(pair, day=2) == 0


def test_should_interact_no_relationship():
    initiator = _make_npc("farmer", relationships={})
    target = _make_npc("bartender")
    counter = InteractionCounter()
    assert should_interact(initiator, target, GameTime(day=1, hour=12), counter) is False


def test_should_interact_low_trust():
    initiator = _make_npc("farmer", relationships={
        "bartender": {"trust_level": 3, "attitude": "neutral"}
    })
    target = _make_npc("bartender")
    counter = InteractionCounter()
    assert should_interact(initiator, target, GameTime(day=1, hour=12), counter) is False


def test_should_interact_passes():
    initiator = _make_npc("farmer", relationships={
        "bartender": {"trust_level": 8, "attitude": "friendly"}
    })
    target = _make_npc("bartender")
    counter = InteractionCounter()
    assert should_interact(initiator, target, GameTime(day=1, hour=12), counter) is True


def test_should_interact_exceeds_daily_limit():
    initiator = _make_npc("farmer", relationships={
        "bartender": {"trust_level": 8, "attitude": "friendly"}
    })
    target = _make_npc("bartender")
    counter = InteractionCounter()
    counter.increment(("bartender", "farmer"), day=1)
    counter.increment(("bartender", "farmer"), day=1)
    assert should_interact(initiator, target, GameTime(day=1, hour=12), counter) is False


def test_should_interact_target_not_idle():
    initiator = _make_npc("farmer", relationships={
        "bartender": {"trust_level": 8, "attitude": "friendly"}
    })
    target = _make_npc("bartender", status="active")
    counter = InteractionCounter()
    assert should_interact(initiator, target, GameTime(day=1, hour=12), counter) is False


@pytest.mark.asyncio
async def test_interaction_hook_execute_triggers_conversation():
    loc_reg = LocationRegistry(initial={"tavern": ["bartender"]})
    farmer = _make_npc("farmer", relationships={
        "bartender": {"trust_level": 8, "attitude": "friendly"}
    })
    bartender = _make_npc("bartender")
    npc_registry = {"farmer": farmer, "bartender": bartender}

    runner = AsyncMock()
    runner.run_conversation = AsyncMock()

    hook = InteractionHook(
        npc_registry=npc_registry,
        location_registry=loc_reg,
        interaction_runner=runner,
    )
    await hook.execute({
        "actor_id": "farmer",
        "location": "tavern",
        "game_time": GameTime(day=1, hour=12),
    })
    runner.run_conversation.assert_called_once()


@pytest.mark.asyncio
async def test_interaction_hook_respects_daily_limit():
    loc_reg = LocationRegistry(initial={"tavern": ["bartender"]})
    farmer = _make_npc("farmer", relationships={
        "bartender": {"trust_level": 8, "attitude": "friendly"}
    })
    bartender = _make_npc("bartender")
    npc_registry = {"farmer": farmer, "bartender": bartender}

    runner = AsyncMock()
    runner.run_conversation = AsyncMock()

    hook = InteractionHook(
        npc_registry=npc_registry,
        location_registry=loc_reg,
        interaction_runner=runner,
    )
    # First two interactions succeed
    await hook.execute({"actor_id": "farmer", "location": "tavern", "game_time": GameTime(day=1, hour=10)})
    await hook.execute({"actor_id": "farmer", "location": "tavern", "game_time": GameTime(day=1, hour=14)})
    # Third should be blocked
    await hook.execute({"actor_id": "farmer", "location": "tavern", "game_time": GameTime(day=1, hour=18)})
    assert runner.run_conversation.call_count == 2
