import os
import pytest
from server.core.state_store import JsonStore


def test_json_store_save_load():
    store = JsonStore(base_path="data/test")
    store.save("test_key", {"a": 1, "b": "hello"})
    loaded = store.load("test_key")
    assert loaded == {"a": 1, "b": "hello"}
    store.delete("test_key")
    assert store.load("test_key") is None
