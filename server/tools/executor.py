"""工具执行引擎。

接收 LLM 返回的 tool_calls，逐个查找工具并执行，收集结果。
结果可转为 tool role messages 回传给 LLM 做后续推理。
"""

import json
import logging
from typing import Any, Dict, List

from server.tools.registry import ToolRegistry

logger = logging.getLogger(__name__)


class ToolExecutor:
    def __init__(self, registry: ToolRegistry, max_calls_per_turn: int = 3):
        self.registry = registry
        self.max_calls_per_turn = max_calls_per_turn

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
                results.append({
                    "call_id": call_id,
                    "name": name,
                    "success": False,
                    "message": f"未知工具: {name}",
                    "state_changes": {},
                })
                continue

            try:
                result = tool.execute(actor_id, arguments, context)
                results.append({
                    "call_id": call_id,
                    "name": name,
                    "success": result.success,
                    "message": result.message,
                    "state_changes": result.state_changes,
                })
            except Exception as e:
                logger.warning("工具 %s 执行失败: %s", name, e)
                results.append({
                    "call_id": call_id,
                    "name": name,
                    "success": False,
                    "message": f"执行失败: {e}",
                    "state_changes": {},
                })

        return results

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
