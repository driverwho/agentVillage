from abc import ABC, abstractmethod
import json
import os
from typing import Any, Dict


class StateStore(ABC):
    @abstractmethod
    def save(self, key: str, data: Dict[str, Any]) -> None: ...

    @abstractmethod
    def load(self, key: str) -> Dict[str, Any] | None: ...

    @abstractmethod
    def delete(self, key: str) -> None: ...


class JsonStore(StateStore):
    def __init__(self, base_path: str = "data/users/default"):
        self.base_path = base_path
        os.makedirs(self.base_path, exist_ok=True)

    def _path(self, key: str) -> str:
        return os.path.join(self.base_path, f"{key}.json")

    def save(self, key: str, data: Dict[str, Any]) -> None:
        with open(self._path(key), "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load(self, key: str) -> Dict[str, Any] | None:
        p = self._path(key)
        if not os.path.exists(p):
            return None
        with open(p, "r", encoding="utf-8") as f:
            return json.load(f)

    def delete(self, key: str) -> None:
        p = self._path(key)
        if os.path.exists(p):
            os.remove(p)
