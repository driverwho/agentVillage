from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple


class Tool(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def check_preconditions(self, player_state, npc_state=None) -> Tuple[bool, str]: ...

    @abstractmethod
    def execute(self, player_state, npc_state=None) -> Dict[str, Any]: ...
