"""工具执行引擎。

接收 LLM 返回的 tool_calls，逐个查找工具并执行，收集结果。
结果可转为 tool role messages 回传给 LLM 做后续推理。
"""

import json
import logging
from typing import Any, Callable, Dict, List, Optional

from server.tools.registry import ToolRegistry
from server.models.event import GameEvent

logger = logging.getLogger(__name__)

TOOL_EVENT_TYPE = {
    "farm": "action", "brew": "action", "patrol": "action",
    "divine": "action", "paint": "action",
    "eat": "action", "sleep": "action", "rest": "action",
    "move": "movement",
    "gossip": "dialogue", "trade": "dialogue",
}


class ToolExecutor:
    def __init__(self, registry: ToolRegistry, max_calls_per_turn: int = 3,
                 on_event: Optional[Callable[[GameEvent], None]] = None):
        self.registry = registry
        self.max_calls_per_turn = max_calls_per_turn
        self.on_event = on_event

    def execute_tool_calls(
        self,
        actor_id: str,
        tool_calls: List[Dict[str, Any]],
        context: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """执行一组 tool_calls，返回结果列表。

        每个结果包含: call_id, name, success, message, state_changes
        """
        results = []
        for call in tool_calls[: self.max_calls_per_turn]:
            call_id = call.get("call_id", "")
            name = call.get("name", "")
            arguments = call.get("arguments", {})

            tool = self.registry.get(name)
            if tool is None:
                logger.warning("[ToolExec] 未知工具: %s (actor=%s)", name, actor_id)
                results.append({
                    "call_id": call_id,
                    "name": name,
                    "success": False,
                    "message": f"未知工具: {name}",
                    "state_changes": {},
                })
                continue

            try:
                print(f"[ToolExec] actor={actor_id} | 执行 {name}({arguments})")
                result = tool.execute(actor_id, arguments, context)
                print(f"[ToolExec] actor={actor_id} | {name} → success={result.success} | {result.message} | changes={result.state_changes}")
                results.append({
                    "call_id": call_id,
                    "name": name,
                    "success": result.success,
                    "message": result.message,
                    "state_changes": result.state_changes,
                })
                if result.success and self.on_event:
                    self._emit_event(name, actor_id, arguments, result, context)
            except Exception as e:
                logger.warning("[ToolExec] 工具 %s 执行失败: %s", name, e)
                print(f"[ToolExec] actor={actor_id} | {name} → 异常: {e}")
                results.append({
                    "call_id": call_id,
                    "name": name,
                    "success": False,
                    "message": f"执行失败: {e}",
                    "state_changes": {},
                })

        return results

    def _emit_event(self, tool_name, actor_id, arguments, result, context):
        game_time = context.get("game_time", {"day": 1, "hour": 0})
        location = context.get("location", "unknown")
        loc_reg = context.get("location_registry")

        witnesses = [actor_id]
        if loc_reg:
            colocated = loc_reg.get_npcs_at(location)
            if isinstance(colocated, set):
                witnesses = list(colocated)
            elif isinstance(colocated, list):
                witnesses = colocated

        timestamp = dict(game_time) if isinstance(game_time, dict) else game_time.to_dict()

        event = GameEvent(
            type=TOOL_EVENT_TYPE.get(tool_name, "action"),
            timestamp=timestamp,
            actor=actor_id,
            location=arguments.get("destination", location) if tool_name == "move" else location,
            content=result.message,
            witnesses=witnesses,
            visibility="location",
        )
        self.on_event(event)

    def build_result_messages(self, results: List[Dict[str, Any]]) -> List[Dict[str, str]]:
        """将执行结果转为 OpenAI tool role messages，供后续 LLM 调用。"""
        messages = []
        for r in results:
            content = json.dumps(
                {"success": r["success"], "message": r["message"], "state_changes": r["state_changes"]},
                ensure_ascii=False,
            )
            messages.append({
                "role": "tool",
                "tool_call_id": r["call_id"],
                "content": content,
            })
        return messages
