import pytest
from server.hooks import HookRegistry
from server.hooks.base import Hook


class FakeHook(Hook):
    event = "post_move"

    def __init__(self):
        self.calls = []

    async def execute(self, context):
        self.calls.append(context)


class AnotherHook(Hook):
    event = "post_sleep"

    def __init__(self):
        self.calls = []

    async def execute(self, context):
        self.calls.append(context)


@pytest.mark.asyncio
async def test_register_and_fire():
    registry = HookRegistry()
    hook = FakeHook()
    registry.register(hook)
    await registry.fire("post_move", {"actor_id": "farmer", "location": "tavern"})
    assert len(hook.calls) == 1
    assert hook.calls[0]["actor_id"] == "farmer"


@pytest.mark.asyncio
async def test_fire_only_matching_event():
    registry = HookRegistry()
    move_hook = FakeHook()
    sleep_hook = AnotherHook()
    registry.register(move_hook)
    registry.register(sleep_hook)
    await registry.fire("post_move", {"actor_id": "farmer"})
    assert len(move_hook.calls) == 1
    assert len(sleep_hook.calls) == 0


@pytest.mark.asyncio
async def test_fire_no_hooks_registered():
    registry = HookRegistry()
    await registry.fire("post_move", {"actor_id": "farmer"})


@pytest.mark.asyncio
async def test_multiple_hooks_same_event():
    registry = HookRegistry()
    h1 = FakeHook()
    h2 = FakeHook()
    registry.register(h1)
    registry.register(h2)
    await registry.fire("post_move", {"x": 1})
    assert len(h1.calls) == 1
    assert len(h2.calls) == 1
