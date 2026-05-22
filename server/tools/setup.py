"""全局工具注册表初始化。

启动时调用 init_tool_system()，为所有 NPC 配置工具系统。
"""

from server.tools.registry import ToolRegistry
from server.tools.policy import ToolPolicyPipeline
from server.tools.executor import ToolExecutor
from server.tools.definitions import (
    EatTool, SleepTool, RestTool, MoveTool,
    FarmNPCTool, BrewTool, PatrolTool, DivineTool, PaintTool,
    GossipTool, TradeTool,
)

# NPC ID → 允许的职业工具名列表
NPC_PROFESSIONAL_TOOLS = {
    "farmer": ["farm"],
    "bartender": ["brew"],
    "sheriff": ["patrol"],
    "fortune_teller": ["divine"],
    "painter": ["paint"],
    "beggar": [],
}

# 每日工具使用上限
DEFAULT_DAILY_LIMITS = {
    "gossip": 5,
    "trade": 3,
}


def create_registry() -> ToolRegistry:
    """创建并注册所有工具的注册表。"""
    reg = ToolRegistry()
    for tool_cls in [
        EatTool, SleepTool, RestTool, MoveTool,
        FarmNPCTool, BrewTool, PatrolTool, DivineTool, PaintTool,
        GossipTool, TradeTool,
    ]:
        reg.register(tool_cls())
    return reg


def init_tool_system(npcs: dict) -> None:
    """为所有 NPC Agent 配置工具系统。

    Args:
        npcs: {npc_id: NPCAgent} 字典
    """
    registry = create_registry()
    pipeline = ToolPolicyPipeline()

    for npc_id, agent in npcs.items():
        agent.tool_registry = registry
        agent.tool_pipeline = pipeline
        agent.tool_executor = ToolExecutor(registry)
        bg_tools = agent.background.get("tools", [])
        agent._allowed_professional = bg_tools or NPC_PROFESSIONAL_TOOLS.get(npc_id, [])
        agent._daily_limits = dict(DEFAULT_DAILY_LIMITS)
        agent._daily_usage = {}


def build_policy_context(agent, game_time, trust_level: float = 5.0) -> dict:
    """构建策略管道所需的上下文。"""
    return {
        "actor_id": agent.agent_id,
        "allowed_professional": getattr(agent, "_allowed_professional", []),
        "npc_state": agent.state,
        "trust_level": trust_level,
        "hour": game_time.hour,
        "daily_usage": getattr(agent, "_daily_usage", {}),
        "daily_limits": getattr(agent, "_daily_limits", {}),
    }


# 位置 ID → 中文名映射
LOCATION_NAMES = {
    "home": "家",
    "field": "田地",
    "tavern": "酒馆",
    "market": "市场",
    "church": "教堂",
    "forest": "森林",
}


def build_autonomous_context(agent, game_time) -> str:
    """构建 NPC 自主决策时的 current_input 文本。"""
    location_cn = LOCATION_NAMES.get(agent.location, agent.location)
    idle_reason = agent.activity_state.idle_reason

    if idle_reason is None:
        status_text = "刚起床" if game_time.hour == 6 else "空闲"
        last_activity_text = ""
    else:
        status_text = "空闲"
        last_activity_text = f"\n上一个活动：{idle_reason}"

    return (
        f"【行动指令】\n"
        f"当前时间：Day {game_time.day}, {game_time.hour}:00\n"
        f"你的位置：{location_cn}\n"
        f"你的状态：{status_text}"
        f"{last_activity_text}\n"
        f"请从可用工具中选择你接下来要做的事情。"
    )
