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


def build_autonomous_context(agent, game_time, location_registry=None,
                             event_engine=None, belief_store=None) -> str:
    """构建 NPC 自主决策时的 current_input 文本。

    当 belief_store 提供时，精简 input——信念由 ContextBuilder 的 L1-L4 层负责注入。
    """
    location_cn = LOCATION_NAMES.get(agent.location, agent.location)
    idle_reason = agent.activity_state.idle_reason

    if idle_reason is None:
        status_text = "刚起床" if game_time.hour == 6 else "空闲"
        last_activity_text = ""
    else:
        status_text = "空闲"
        last_activity_text = f"\n上一个活动：{idle_reason}"

    # 当前环境（客观即时感知，两种模式都需要）
    env_parts = []
    if event_engine:
        weather = event_engine.get_current_weather()
        events_text = event_engine.get_world_events_text()
        env_parts.append(f"天气：{weather}")
        if events_text != "今日无事":
            env_parts.append(f"今日事件：{events_text}")
    env_parts.append(f"当前地点：{location_cn}")
    if location_registry:
        colocated = location_registry.get_npcs_at(agent.location) - {agent.agent_id}
        if colocated:
            names = [_get_npc_name(nid) for nid in colocated]
            env_parts.append(f"同处此地的人：{'、'.join(names)}")
    env_section = "\n【当前环境】\n" + "\n".join(env_parts)

    # 信念系统模式：精简 input，信念由 ContextBuilder 注入
    if belief_store is not None:
        return (
            f"【行动指令】\n"
            f"当前时间：Day {game_time.day}, {game_time.hour}:00\n"
            f"你的状态：{status_text}"
            f"{last_activity_text}"
            f"{env_section}\n"
            f"你正在独自思考接下来做什么，不需要说话或与任何人对话。"
            f"请直接调用一个工具，不要生成对话文本。"
        )

    # 旧模式：保持原有逻辑不变
    # 今日活动日志
    if agent.activity_log:
        today_log = "\n【今日已完成】\n" + "\n".join(agent.activity_log)
    else:
        today_log = "\n【今日已完成】\n（刚开始新的一天）"

    # 近日回顾（最近2天的 daily_summary）
    recent = agent.memory.read_recent_summaries(game_time.day, count=2)
    recent_section = f"\n【近日回顾】\n{recent}" if recent else ""

    # 近期社交
    social_section = ""
    if hasattr(agent, "recent_social") and agent.recent_social:
        social_lines = []
        for s in agent.recent_social[-3:]:
            social_lines.append(f"Day {s['day']} {s['hour']}:00 — 与{s['partner']}交谈：{s['summary']}")
        social_section = "\n【近期社交】\n" + "\n".join(social_lines)

    return (
        f"【行动指令】\n"
        f"当前时间：Day {game_time.day}, {game_time.hour}:00\n"
        f"你的状态：{status_text}"
        f"{last_activity_text}"
        f"{env_section}"
        f"{today_log}"
        f"{recent_section}"
        f"{social_section}\n"
        f"你正在独自思考接下来做什么，不需要说话或与任何人对话。"
        f"请直接调用一个工具，不要生成对话文本。"
    )


# NPC ID → 中文名映射（用于社交信息）
_NPC_NAMES = {
    "farmer": "农夫·乔治",
    "bartender": "酒馆老板·Gus",
}


def _get_npc_name(npc_id: str) -> str:
    return _NPC_NAMES.get(npc_id, npc_id)
