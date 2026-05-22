from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Tuple


class ToolCategory(Enum):
    SOCIAL = "social"
    PROFESSIONAL = "professional"
    SURVIVAL = "survival"


@dataclass
class ToolParam:
    name: str
    type: str  # "string" | "integer" | "boolean"
    description: str
    required: bool = True
    enum: List[str] | None = None


@dataclass
class ToolResult:
    success: bool
    message: str = ""
    state_changes: Dict[str, Any] = field(default_factory=dict)
    broadcast: bool = False


class NPCTool(ABC):
    """NPC 工具基类。所有 NPC 行为工具继承此类。"""

    name: str
    category: ToolCategory
    description: str
    params: List[ToolParam] = []
    duration_hours: int = 1  # 执行时长（游戏小时），-1 表示动态计算

    @abstractmethod
    def execute(self, actor_id: str, params: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        ...

    def to_function_schema(self) -> Dict[str, Any]:
        """生成 OpenAI function calling schema。"""
        properties = {}
        required = []
        for p in self.params:
            prop: Dict[str, Any] = {"type": p.type, "description": p.description}
            if p.enum:
                prop["enum"] = p.enum
            properties[p.name] = prop
            if p.required:
                required.append(p.name)

        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required,
                },
            },
        }


# 保留旧接口兼容（玩家工具）
class Tool(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def check_preconditions(self, player_state, npc_state=None) -> Tuple[bool, str]: ...

    @abstractmethod
    def execute(self, player_state, npc_state=None) -> Dict[str, Any]: ...
