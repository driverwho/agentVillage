from typing import Dict, List, Optional

from server.tools.base_tool import NPCTool, ToolCategory


class ToolRegistry:
    """工具注册表。管理所有已注册的 NPC 工具，生成 function calling schema。"""

    def __init__(self):
        self._tools: Dict[str, NPCTool] = {}

    def register(self, tool: NPCTool) -> None:
        if tool.name in self._tools:
            raise ValueError(f"工具 '{tool.name}' 已注册")
        self._tools[tool.name] = tool

    def get(self, name: str) -> Optional[NPCTool]:
        return self._tools.get(name)

    def get_all(self) -> List[NPCTool]:
        return list(self._tools.values())

    def get_by_category(self, category: ToolCategory) -> List[NPCTool]:
        return [t for t in self._tools.values() if t.category == category]

    def generate_schemas(self, tool_names: List[str]) -> List[dict]:
        """为指定工具名列表生成 OpenAI function calling schemas。"""
        schemas = []
        for name in tool_names:
            tool = self._tools.get(name)
            if tool:
                schemas.append(tool.to_function_schema())
        return schemas
