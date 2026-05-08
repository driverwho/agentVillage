from server.core.ending_checker import EndingChecker
from server.models.player_state import PlayerState


def test_farmer_joy_ending():
    ps = PlayerState()
    ps.relationships["farmer"] = 80
    ps.crops_harvested = ["wheat", "corn"]
    ps.farm_count = 5
    assert EndingChecker.check_farmer_joy(ps)


def test_no_ending():
    ps = PlayerState()
    assert not EndingChecker.check_farmer_joy(ps)


def test_death_ending():
    ps = PlayerState(health=0)
    result = EndingChecker.check_all(ps)
    assert result == "death"
