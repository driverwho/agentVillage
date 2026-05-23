from collections import defaultdict
from typing import Any, Dict, List
from server.hooks.base import Hook


class HookRegistry:
    def __init__(self):
        self._hooks: Dict[str, List[Hook]] = defaultdict(list)

    def register(self, hook: Hook) -> None:
        self._hooks[hook.event].append(hook)

    async def fire(self, event: str, context: Dict[str, Any]) -> None:
        for hook in self._hooks.get(event, []):
            await hook.execute(context)
