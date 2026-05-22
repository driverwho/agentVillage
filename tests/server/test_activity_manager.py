import pytest
from server.core.activity_manager import ActivityState, ActivityManager
from server.models.npc_state import NPCState
from server.models.game_time import GameTime


# ============================================================
# ActivityState 基础
# ============================================================

def test_activity_state_default_is_idle():
    state = ActivityState()
    assert state.status == "idle"
    assert state.current_tool is None
    assert state.end_hour is None
    assert state.end_day is None
    assert state.idle_reason is None


def test_activity_state_set_active():
    state = ActivityState()
    state.status = "active"
    state.current_tool = "farm"
    state.end_day = 1
    state.end_hour = 12
    assert state.status == "active"
    assert state.current_tool == "farm"


# ============================================================
# ActivityManager — 活动完成检查
# ============================================================

def test_check_completion_not_done():
    mgr = ActivityManager()
    activity = ActivityState(status="active", current_tool="farm", end_day=1, end_hour=12)
    game_time = GameTime(day=1, hour=10, minute=0)
    assert mgr.check_completion(activity, game_time) is False


def test_check_completion_done():
    mgr = ActivityManager()
    activity = ActivityState(status="active", current_tool="farm", end_day=1, end_hour=12)
    game_time = GameTime(day=1, hour=12, minute=0)
    assert mgr.check_completion(activity, game_time) is True


def test_check_completion_past_due():
    mgr = ActivityManager()
    activity = ActivityState(status="active", current_tool="farm", end_day=1, end_hour=12)
    game_time = GameTime(day=1, hour=14, minute=0)
    assert mgr.check_completion(activity, game_time) is True


def test_check_completion_cross_day():
    mgr = ActivityManager()
    activity = ActivityState(status="active", current_tool="sleep", end_day=2, end_hour=6)
    assert mgr.check_completion(activity, GameTime(day=1, hour=23, minute=0)) is False
    assert mgr.check_completion(activity, GameTime(day=2, hour=5, minute=0)) is False
    assert mgr.check_completion(activity, GameTime(day=2, hour=6, minute=0)) is True


def test_check_completion_idle_returns_false():
    mgr = ActivityManager()
    activity = ActivityState(status="idle")
    assert mgr.check_completion(activity, GameTime(day=1, hour=10, minute=0)) is False


# ============================================================
# ActivityManager — 中断检查
# ============================================================

def test_check_interrupts_hunger():
    mgr = ActivityManager()
    npc_state = NPCState(hunger=15)
    activity = ActivityState(status="active", current_tool="farm")
    result = mgr.check_interrupts(activity, npc_state)
    assert result is not None
    assert "饥饿" in result


def test_check_interrupts_fatigue():
    mgr = ActivityManager()
    npc_state = NPCState(fatigue=95)
    activity = ActivityState(status="active", current_tool="farm")
    result = mgr.check_interrupts(activity, npc_state)
    assert result is not None
    assert "疲惫" in result


def test_check_interrupts_health():
    mgr = ActivityManager()
    npc_state = NPCState(health=15)
    activity = ActivityState(status="active", current_tool="farm")
    result = mgr.check_interrupts(activity, npc_state)
    assert result is not None
    assert "虚弱" in result


def test_check_interrupts_none_when_ok():
    mgr = ActivityManager()
    npc_state = NPCState(hunger=50, fatigue=50, health=80)
    activity = ActivityState(status="active", current_tool="farm")
    result = mgr.check_interrupts(activity, npc_state)
    assert result is None


def test_check_interrupts_idle_returns_none():
    mgr = ActivityManager()
    npc_state = NPCState(hunger=5)
    activity = ActivityState(status="idle")
    result = mgr.check_interrupts(activity, npc_state)
    assert result is None


# ============================================================
# ActivityManager — 决策点检查
# ============================================================

def test_is_decision_point_true():
    mgr = ActivityManager()
    assert mgr.is_decision_point(6) is True
    assert mgr.is_decision_point(12) is True
    assert mgr.is_decision_point(18) is True
    assert mgr.is_decision_point(20) is True


def test_is_decision_point_false():
    mgr = ActivityManager()
    assert mgr.is_decision_point(7) is False
    assert mgr.is_decision_point(0) is False
    assert mgr.is_decision_point(15) is False


# ============================================================
# ActivityManager — 状态转换
# ============================================================

def test_transition_to_idle():
    mgr = ActivityManager()
    activity = ActivityState(status="active", current_tool="farm", end_day=1, end_hour=12)
    mgr.transition_to_idle(activity, reason="完成了farm")
    assert activity.status == "idle"
    assert activity.idle_reason == "完成了farm"
    assert activity.current_tool is None
    assert activity.end_hour is None
    assert activity.end_day is None


def test_transition_to_active():
    mgr = ActivityManager()
    activity = ActivityState(status="idle")
    game_time = GameTime(day=1, hour=8, minute=0)
    mgr.transition_to_active(activity, tool_name="farm", duration_hours=4, game_time=game_time)
    assert activity.status == "active"
    assert activity.current_tool == "farm"
    assert activity.end_day == 1
    assert activity.end_hour == 12
    assert activity.idle_reason is None


def test_transition_to_active_cross_day():
    mgr = ActivityManager()
    activity = ActivityState(status="idle")
    game_time = GameTime(day=1, hour=22, minute=0)
    mgr.transition_to_active(activity, tool_name="sleep", duration_hours=8, game_time=game_time)
    assert activity.end_day == 2
    assert activity.end_hour == 6


# ============================================================
# ActivityManager — sleep 时长计算
# ============================================================

def test_calculate_sleep_duration():
    mgr = ActivityManager()
    assert mgr.calculate_sleep_duration(22) == 8
    assert mgr.calculate_sleep_duration(23) == 7
    assert mgr.calculate_sleep_duration(0) == 6
    assert mgr.calculate_sleep_duration(20) == 10
    assert mgr.calculate_sleep_duration(3) == 6
