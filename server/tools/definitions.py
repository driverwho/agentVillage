"""NPC 一次性工具定义。

每个工具是一个无状态类，execute() 接收 actor_id、LLM 传入参数和运行时上下文，
返回 ToolResult。状态变更由调用者根据 state_changes 应用。
"""

from typing import Any, Dict

from server.tools.base_tool import NPCTool, ToolCategory, ToolParam, ToolResult


# ============================================================
# 生存类工具
# ============================================================

class EatTool(NPCTool):
    name = "eat"
    category = ToolCategory.SURVIVAL
    description = "进食以恢复饱食度（+30）"
    params = []

    def execute(self, actor_id: str, params: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        state = context["npc_states"][actor_id]
        new_hunger = min(100, state.hunger + 30)
        state.hunger = new_hunger
        return ToolResult(success=True, message="吃了一顿饭", state_changes={"hunger": new_hunger})


class SleepTool(NPCTool):
    name = "sleep"
    category = ToolCategory.SURVIVAL
    description = "睡觉，完全恢复疲劳值"
    params = []

    def execute(self, actor_id: str, params: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        state = context["npc_states"][actor_id]
        state.fatigue = 0
        return ToolResult(success=True, message="睡了一觉", state_changes={"fatigue": 0})


class RestTool(NPCTool):
    name = "rest"
    category = ToolCategory.SURVIVAL
    description = "休息片刻，减少疲劳值（-20）"
    params = []

    def execute(self, actor_id: str, params: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        state = context["npc_states"][actor_id]
        new_fatigue = max(0, state.fatigue - 20)
        state.fatigue = new_fatigue
        return ToolResult(success=True, message="休息了一会儿", state_changes={"fatigue": new_fatigue})


class MoveTool(NPCTool):
    name = "move"
    category = ToolCategory.SURVIVAL
    description = "移动到指定地点"
    params = [
        ToolParam(
            name="destination",
            type="string",
            description="目的地",
            enum=["field", "tavern", "home", "market", "church", "forest"],
        ),
    ]

    def execute(self, actor_id: str, params: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        dest = params.get("destination", "home")
        context.setdefault("locations", {})[actor_id] = dest
        return ToolResult(
            success=True,
            message=f"前往了{dest}",
            state_changes={"location": dest},
            broadcast=True,
        )


# ============================================================
# 职业类工具
# ============================================================

class FarmNPCTool(NPCTool):
    name = "farm"
    category = ToolCategory.PROFESSIONAL
    description = "耕作田地，消耗体力（+15疲劳），改善心情（+5）"
    params = []

    def execute(self, actor_id: str, params: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        state = context["npc_states"][actor_id]
        state.fatigue = min(100, state.fatigue + 15)
        state.mood = min(100, state.mood + 5)
        return ToolResult(
            success=True,
            message="辛勤耕作了一阵",
            state_changes={"fatigue": state.fatigue, "mood": state.mood},
        )


class BrewTool(NPCTool):
    name = "brew"
    category = ToolCategory.PROFESSIONAL
    description = "酿造酒水，消耗体力（+10疲劳）"
    params = []

    def execute(self, actor_id: str, params: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        state = context["npc_states"][actor_id]
        state.fatigue = min(100, state.fatigue + 10)
        return ToolResult(
            success=True,
            message="酿了一桶新酒",
            state_changes={"fatigue": state.fatigue},
        )


class PatrolTool(NPCTool):
    name = "patrol"
    category = ToolCategory.PROFESSIONAL
    description = "巡逻村庄，消耗体力（+10疲劳）"
    params = []

    def execute(self, actor_id: str, params: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        state = context["npc_states"][actor_id]
        state.fatigue = min(100, state.fatigue + 10)
        return ToolResult(
            success=True,
            message="完成了一轮巡逻",
            state_changes={"fatigue": state.fatigue},
            broadcast=True,
        )


class DivineTool(NPCTool):
    name = "divine"
    category = ToolCategory.PROFESSIONAL
    description = "进行占卜，消耗精力（+10疲劳），可能影响心情"
    params = []

    def execute(self, actor_id: str, params: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        state = context["npc_states"][actor_id]
        state.fatigue = min(100, state.fatigue + 10)
        return ToolResult(
            success=True,
            message="完成了一次占卜",
            state_changes={"fatigue": state.fatigue},
        )


class PaintTool(NPCTool):
    name = "paint"
    category = ToolCategory.PROFESSIONAL
    description = "绘画创作，消耗体力（+10疲劳），提升心情（+10）"
    params = []

    def execute(self, actor_id: str, params: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        state = context["npc_states"][actor_id]
        state.fatigue = min(100, state.fatigue + 10)
        state.mood = min(100, state.mood + 10)
        return ToolResult(
            success=True,
            message="画了一幅画",
            state_changes={"fatigue": state.fatigue, "mood": state.mood},
        )


# ============================================================
# 社交类工具（一次性动作，不含 speak 会话工具）
# ============================================================

class GossipTool(NPCTool):
    name = "gossip"
    category = ToolCategory.SOCIAL
    description = "向另一个 NPC 传播消息或八卦"
    params = [
        ToolParam(name="target", type="string", description="传播对象 NPC ID"),
        ToolParam(name="content", type="string", description="八卦内容"),
    ]

    def execute(self, actor_id: str, params: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        target = params.get("target", "")
        content = params.get("content", "")
        return ToolResult(
            success=True,
            message=f"向{target}说了一些关于'{content[:20]}'的八卦",
            state_changes={"gossip_target": target, "gossip_content": content},
            broadcast=True,
        )


class TradeTool(NPCTool):
    name = "trade"
    category = ToolCategory.SOCIAL
    description = "与另一个 NPC 或玩家进行物品交易"
    params = [
        ToolParam(name="target", type="string", description="交易对象 ID"),
        ToolParam(name="item", type="string", description="交易物品描述"),
        ToolParam(name="action", type="string", description="give 或 request", enum=["give", "request"]),
    ]

    def execute(self, actor_id: str, params: Dict[str, Any], context: Dict[str, Any]) -> ToolResult:
        target = params.get("target", "")
        item = params.get("item", "")
        action = params.get("action", "give")
        verb = "给了" if action == "give" else "向其请求"
        return ToolResult(
            success=True,
            message=f"与{target}交易：{verb}'{item}'",
            state_changes={"trade_target": target, "trade_item": item, "trade_action": action},
            broadcast=True,
        )
