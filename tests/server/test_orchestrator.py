from server.core.background_manager import BackgroundManager
from server.core.orchestrator import Orchestrator

# 确保测试前已初始化
BackgroundManager.reset()
BackgroundManager.init()


def test_orchestrator_init():
    o = Orchestrator("test_user")
    assert "farmer" in o.npcs
    assert "bartender" in o.npcs
    assert o.time_system.game_time.hour == 6


def test_advance_time():
    o = Orchestrator("test_user")
    initial_day = o.time_system.game_time.day
    o.advance_time(600)  # 10小时
    assert o.time_system.game_time.hour != 6 or o.time_system.game_time.day > initial_day


def test_auto_save():
    o = Orchestrator("test_user")
    o.advance_time(60)
    # 验证存档文件存在
    loaded = o.store.load("world_state")
    assert loaded is not None
    assert "game_time" in loaded
    assert "npcs" not in loaded  # world_state不包含npcs（只在get_world_state中）
