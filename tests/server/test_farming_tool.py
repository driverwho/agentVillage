from server.tools.farming import FarmingTool
from server.models.player_state import PlayerState


def test_farming_success():
    ps = PlayerState(fatigue=0, hunger=100)
    tool = FarmingTool()
    ok, msg = tool.check_preconditions(ps)
    assert ok
    result = tool.execute(ps)
    assert result["success"]
    assert ps.fatigue == 20
    assert ps.farm_count == 1


def test_farming_too_tired():
    ps = PlayerState(fatigue=90)
    tool = FarmingTool()
    ok, msg = tool.check_preconditions(ps)
    assert not ok


def test_farming_too_hungry():
    ps = PlayerState(fatigue=0, hunger=10)
    tool = FarmingTool()
    ok, msg = tool.check_preconditions(ps)
    assert not ok
