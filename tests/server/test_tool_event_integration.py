import pytest
from unittest.mock import MagicMock
from server.models.event import GameEvent
from server.models.npc_state import NPCState
from server.tools.executor import ToolExecutor
from server.tools.registry import ToolRegistry
from server.tools.definitions import FarmNPCTool, EatTool, MoveTool


class TestToolExecutorEvents:
    def setup_method(self):
        self.registry = ToolRegistry()
        self.registry.register(FarmNPCTool())
        self.registry.register(EatTool())
        self.registry.register(MoveTool())
        self.events_collected = []
        self.executor = ToolExecutor(
            registry=self.registry,
            on_event=lambda e: self.events_collected.append(e),
        )
        self.npc_states = {"farmer": NPCState()}

    def test_farm_produces_action_event(self):
        context = {
            "actor_id": "farmer",
            "location": "field",
            "game_time": {"day": 1, "hour": 8},
            "location_registry": None,
            "npc_states": self.npc_states,
        }
        results = self.executor.execute_tool_calls(
            actor_id="farmer",
            tool_calls=[{"call_id": "c1", "name": "farm", "arguments": {}}],
            context=context,
        )
        assert results[0]["success"]
        assert len(self.events_collected) == 1
        event = self.events_collected[0]
        assert event.type == "action"
        assert event.actor == "farmer"
        assert event.location == "field"
        assert event.visibility == "location"

    def test_move_produces_movement_event(self):
        loc_reg = MagicMock()
        loc_reg.get_npcs_at.return_value = {"farmer", "bartender"}
        context = {
            "actor_id": "farmer",
            "location": "field",
            "game_time": {"day": 1, "hour": 10},
            "location_registry": loc_reg,
            "npc_states": self.npc_states,
        }
        results = self.executor.execute_tool_calls(
            actor_id="farmer",
            tool_calls=[{"call_id": "c1", "name": "move", "arguments": {"destination": "tavern"}}],
            context=context,
        )
        assert len(self.events_collected) == 1
        event = self.events_collected[0]
        assert event.type == "movement"
        assert event.location == "tavern"

    def test_no_event_callback_still_works(self):
        """on_event 为 None 时不崩溃。"""
        executor = ToolExecutor(registry=self.registry, on_event=None)
        context = {
            "actor_id": "farmer",
            "location": "field",
            "game_time": {"day": 1, "hour": 8},
            "location_registry": None,
            "npc_states": self.npc_states,
        }
        results = executor.execute_tool_calls(
            actor_id="farmer",
            tool_calls=[{"call_id": "c1", "name": "farm", "arguments": {}}],
            context=context,
        )
        assert results[0]["success"]

    def test_failed_tool_no_event(self):
        """工具执行失败时不产生事件。"""
        context = {
            "actor_id": "farmer",
            "location": "field",
            "game_time": {"day": 1, "hour": 8},
            "location_registry": None,
            "npc_states": self.npc_states,
        }
        results = self.executor.execute_tool_calls(
            actor_id="farmer",
            tool_calls=[{"call_id": "c1", "name": "nonexistent", "arguments": {}}],
            context=context,
        )
        assert not results[0]["success"]
        assert len(self.events_collected) == 0

    def test_eat_produces_event(self):
        context = {
            "actor_id": "farmer",
            "location": "home",
            "game_time": {"day": 1, "hour": 12},
            "location_registry": None,
            "npc_states": self.npc_states,
        }
        results = self.executor.execute_tool_calls(
            actor_id="farmer",
            tool_calls=[{"call_id": "c1", "name": "eat", "arguments": {}}],
            context=context,
        )
        assert results[0]["success"]
        assert len(self.events_collected) == 1
        assert self.events_collected[0].type == "action"
        assert self.events_collected[0].actor == "farmer"
