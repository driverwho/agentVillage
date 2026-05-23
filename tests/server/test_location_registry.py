from server.core.location_registry import LocationRegistry


def test_initial_empty():
    reg = LocationRegistry()
    assert reg.get_npcs_at("tavern") == set()


def test_initial_from_dict():
    reg = LocationRegistry(initial={"tavern": ["bartender"], "field": ["farmer"]})
    assert reg.get_npcs_at("tavern") == {"bartender"}
    assert reg.get_npcs_at("field") == {"farmer"}


def test_move_adds_to_new_location():
    reg = LocationRegistry()
    reg.move("farmer", None, "field")
    assert reg.get_npcs_at("field") == {"farmer"}


def test_move_removes_from_old_location():
    reg = LocationRegistry(initial={"field": ["farmer"]})
    reg.move("farmer", "field", "tavern")
    assert reg.get_npcs_at("field") == set()
    assert reg.get_npcs_at("tavern") == {"farmer"}


def test_get_location():
    reg = LocationRegistry(initial={"tavern": ["bartender"]})
    assert reg.get_location("bartender") == "tavern"
    assert reg.get_location("unknown") is None


def test_to_dict():
    reg = LocationRegistry(initial={"tavern": ["bartender", "farmer"]})
    d = reg.to_dict()
    assert d == {"tavern": ["bartender", "farmer"]}


def test_to_dict_excludes_empty():
    reg = LocationRegistry(initial={"tavern": ["bartender"]})
    reg.move("bartender", "tavern", "field")
    d = reg.to_dict()
    assert "tavern" not in d
    assert d == {"field": ["bartender"]}
