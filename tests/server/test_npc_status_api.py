"""测试 NPC 状态 API 端点。"""
import pytest
from server.core.background_manager import BackgroundManager
from server.core.orchestrator import Orchestrator

BackgroundManager.reset()
BackgroundManager.init()


def test_get_npcs_status():
    """GET /api/npcs/status 返回所有 NPC 快照"""
    from server.api.routes import get_npcs_status
    import server.core.orchestrator as orch_mod

    orch_mod.orch = Orchestrator("test_status")
    result = get_npcs_status()

    assert "npcs" in result
    assert "game_time" in result
    assert "farmer" in result["npcs"]
    assert "bartender" in result["npcs"]

    farmer = result["npcs"]["farmer"]
    assert "name" in farmer
    assert "location" in farmer
    assert "activity" in farmer
    assert "state" in farmer
    assert "llm_status" in farmer
    assert "history" in farmer

    assert farmer["activity"]["status"] in ("idle", "active")
    assert isinstance(farmer["state"]["health"], int)


def test_npcs_status_activity_fields():
    """活动字段包含正确的键"""
    from server.api.routes import get_npcs_status
    import server.core.orchestrator as orch_mod

    orch_mod.orch = Orchestrator("test_status2")
    result = get_npcs_status()
    farmer = result["npcs"]["farmer"]

    activity = farmer["activity"]
    assert "status" in activity
    assert "current_tool" in activity
    assert "end_day" in activity
    assert "end_hour" in activity
    assert "idle_reason" in activity
