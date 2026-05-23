from typing import List, Dict, Any, Optional
from server.models.npc_state import NPCState
from server.models.messages import DialogueTurn
from server.memory.memory_manager import MemoryManager
from server.llm.token_budget import TokenBudget
from server.core.activity_manager import ActivityState


class NPCAgent:
    def __init__(self, agent_id: str, background: dict, memory_base: str, budget: TokenBudget):
        self.agent_id = agent_id
        self.background = background

        # 从 background 派生 identity（向后兼容 ContextBuilder）
        self.identity = {
            "id": background.get("id", agent_id),
            "name": background.get("name", agent_id),
            "daily_habits": background.get("daily_habits", ""),
            "core_motivation": background.get("core_motivation", ""),
            "secret": background.get("secret", ""),
            "speaking_style": background.get("speaking_style", ""),
            "visibility": tuple(background.get("visibility", ["basic"])),
        }

        self.state = NPCState()
        self.memory = MemoryManager(memory_base, agent_id)
        self.budget = budget
        self.visibility = list(self.identity.get("visibility", ("basic",)))
        self.dialogue_history: List[DialogueTurn] = []

        self.memory.seed_if_empty(background)

        # 工具系统（延迟注入，由 Orchestrator 初始化时设置）
        self.tool_registry: Optional[Any] = None
        self.tool_pipeline: Optional[Any] = None
        self.tool_executor: Optional[Any] = None

        # 活动状态
        self.activity_state = ActivityState()
        self.location: str = background.get("default_location", "home")
        self.activity_log: List[str] = []

    def get_visible_state(self, player_state) -> dict:
        return player_state.get_visible_state(self.visibility)

    def can_interact(self, current_time) -> bool:
        hour = current_time.hour
        if hour >= 22 or hour < 6:
            return False
        return True

    def on_hour_tick(self, game_time) -> None:
        self.state.hunger = max(0, self.state.hunger - 5)
        current_tool = self.activity_state.current_tool
        if current_tool not in ("rest", "sleep", "eat"):
            self.state.fatigue = min(100, self.state.fatigue + 2)
        if game_time.hour == 0:
            self.budget.reset()

    def get_available_tools(self, context: Dict[str, Any]) -> List:
        """通过策略管道过滤，返回当前可用工具列表。"""
        if not self.tool_registry or not self.tool_pipeline:
            return []
        all_tools = self.tool_registry.get_all()
        return self.tool_pipeline.filter(all_tools, context)

    def generate_tool_schemas(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        """为当前可用工具生成 function calling schemas。"""
        available = self.get_available_tools(context)
        return [tool.to_function_schema() for tool in available]

    async def run_tool_turn(
        self,
        context: Dict[str, Any],
        messages: List[Dict[str, str]],
    ) -> Dict[str, Any]:
        """执行一次带工具的 NPC turn。

        流程：过滤可用工具 → 生成 schema → 调用 LLM → 解析响应 → 执行工具 → 返回结果
        """
        import time as _time
        from server.llm.client import get_llm_client, parse_tool_calls

        schemas = self.generate_tool_schemas(context)
        available_names = [s["function"]["name"] for s in schemas]
        print(f"[ToolTurn] NPC={self.agent_id} | 可用工具: {available_names}")

        client = get_llm_client()

        tools_param = schemas if schemas else None
        _t0 = _time.time()
        response = await client.chat(messages, tools=tools_param)
        _latency = (_time.time() - _t0) * 1000

        # 记录到 LLM monitor
        try:
            from server.llm.request_logger import llm_logger
            usage = response.get("usage", {})
            llm_logger.log(
                npc_id=self.agent_id,
                model=client.model,
                request_messages=list(messages),
                response_raw=response,
                estimated_tokens=usage.get("total_tokens", 0),
                latency_ms=_latency,
                success=True,
            )
        except Exception:
            pass

        tool_calls = parse_tool_calls(response)

        if not tool_calls:
            text = response.get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"[ToolTurn] NPC={self.agent_id} | LLM 未调用工具，文本回复: {text[:60]}...")
            return {"tool_used": None, "tool_result": None, "text_reply": text}

        print(f"[ToolTurn] NPC={self.agent_id} | LLM 选择工具: {[c['name'] for c in tool_calls]}")

        results = self.tool_executor.execute_tool_calls(
            self.agent_id, tool_calls, context
        )

        first = results[0] if results else {}
        print(f"[ToolTurn] NPC={self.agent_id} | 执行结果: tool={first.get('name')} success={first.get('success')} | {first.get('message')}")
        return {
            "tool_used": first.get("name"),
            "tool_result": first,
            "text_reply": None,
        }
