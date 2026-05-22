"""工具策略管道 — 五层过滤。

每层是一个 PolicyGate，接收当前可用工具列表 + 上下文，返回过滤后的列表。
ToolPolicyPipeline 按顺序执行所有门，每层结果作为下层输入。
"""

from typing import List, Dict, Any, Protocol

from server.tools.base_tool import NPCTool, ToolCategory


class PolicyGate(Protocol):
    def filter(self, tools: List[NPCTool], context: Dict[str, Any]) -> List[NPCTool]: ...


class IdentityGate:
    """第 1 层：身份门。只允许 NPC 使用其角色对应的职业工具。"""

    def filter(self, tools: List[NPCTool], context: Dict[str, Any]) -> List[NPCTool]:
        allowed_prof = set(context.get("allowed_professional", []))
        result = []
        for tool in tools:
            if tool.category == ToolCategory.PROFESSIONAL:
                if tool.name in allowed_prof:
                    result.append(tool)
            else:
                result.append(tool)
        return result


class StateGate:
    """第 2 层：状态门。根据 NPC 当前状态过滤不适合的工具。"""

    def filter(self, tools: List[NPCTool], context: Dict[str, Any]) -> List[NPCTool]:
        state = context.get("npc_state")
        if state is None:
            return tools

        result = []
        for tool in tools:
            if state.fatigue > 80 and tool.category == ToolCategory.SOCIAL:
                continue
            if state.mood < 20 and tool.category == ToolCategory.PROFESSIONAL:
                continue
            result.append(tool)
        return result


class RelationshipGate:
    """第 3 层：关系门。信任度不足时限制社交工具。"""

    SOCIAL_TRUST_THRESHOLD = 3

    def filter(self, tools: List[NPCTool], context: Dict[str, Any]) -> List[NPCTool]:
        trust = context.get("trust_level")
        if trust is None or trust >= self.SOCIAL_TRUST_THRESHOLD:
            return tools

        return [t for t in tools if t.category != ToolCategory.SOCIAL]


class TimeGate:
    """第 4 层：时间门。22:00-06:00 禁止职业工具。"""

    def filter(self, tools: List[NPCTool], context: Dict[str, Any]) -> List[NPCTool]:
        hour = context.get("hour")
        if hour is None:
            return tools

        is_night = hour >= 22 or hour < 6
        if not is_night:
            return tools

        return [t for t in tools if t.category != ToolCategory.PROFESSIONAL]


class QuotaGate:
    """第 5 层：配额门。每日使用次数超限的工具被移除。"""

    def filter(self, tools: List[NPCTool], context: Dict[str, Any]) -> List[NPCTool]:
        daily_usage = context.get("daily_usage", {})
        daily_limits = context.get("daily_limits", {})
        if not daily_limits:
            return tools

        result = []
        for tool in tools:
            limit = daily_limits.get(tool.name)
            if limit is not None:
                used = daily_usage.get(tool.name, 0)
                if used >= limit:
                    continue
            result.append(tool)
        return result


class ToolPolicyPipeline:
    """工具策略管道。顺序执行所有门。"""

    def __init__(self, gates: List[PolicyGate] | None = None):
        self.gates = gates or [
            IdentityGate(),
            StateGate(),
            RelationshipGate(),
            TimeGate(),
            QuotaGate(),
        ]

    def filter(self, tools: List[NPCTool], context: Dict[str, Any]) -> List[NPCTool]:
        result = list(tools)
        for gate in self.gates:
            result = gate.filter(result, context)
        return result
