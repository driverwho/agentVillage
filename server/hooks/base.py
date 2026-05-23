from typing import Any, Dict


class Hook:
    event: str = ""

    async def execute(self, context: Dict[str, Any]) -> None:
        raise NotImplementedError
