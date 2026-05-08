from typing import Dict, Callable, Any
from collections import defaultdict


class MessageBus:
    def __init__(self):
        self.handlers: Dict[str, list] = defaultdict(list)

    def subscribe(self, agent_id: str, handler: Callable[[dict], Any]) -> None:
        self.handlers[agent_id].append(handler)

    def send(self, from_id: str, to_id: str, message: dict) -> None:
        msg = {"from": from_id, "to": to_id, **message}
        for handler in self.handlers.get(to_id, []):
            handler(msg)

    def broadcast(self, message: dict) -> None:
        for handlers in self.handlers.values():
            for handler in handlers:
                handler(message)
