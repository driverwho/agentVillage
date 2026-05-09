import os
from datetime import datetime


class ContextAudit:
    @staticmethod
    def format_entry(
        npc_id: str,
        layers: dict,
        total_tokens: int,
        model_limit: int,
        compressed: bool = False,
        budget_status: str = "normal",
    ) -> str:
        lines = [f"NPC: {npc_id}", ""]
        layer_labels = {
            "L0": "System Prompt",
            "L1": "World Injection",
            "L2": "Self State",
            "L3": "Interlocutor Context",
            "L4": "Memory Retrieval",
            "L5": "Active Dialogue",
        }

        for layer_id in ["L0", "L1", "L2", "L3", "L4", "L5"]:
            if layer_id in layers:
                info = layers[layer_id]
                label = layer_labels.get(layer_id, layer_id)
                status = " [截断]" if info.get("truncated") else ""
                lines.append(f"=== {layer_id}: {label} ({info['tokens']} tokens){status} ===")

        lines.append("=== 统计 ===")
        ratio = int(total_tokens / model_limit * 100) if model_limit else 0
        lines.append(f"总Token: {total_tokens} / {model_limit} ({ratio}%)")
        trunc_layers = [k for k, v in layers.items() if v.get("truncated")]
        lines.append(f"截断触发: {'是 (' + ', '.join(trunc_layers) + ')' if trunc_layers else '否'}")
        lines.append(f"压缩触发: {'是' if compressed else '否'}")
        lines.append(f"预算状态: {budget_status}")

        return "\n".join(lines)

    @staticmethod
    def log_path(npc_id: str) -> str:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        dir_path = f"logs/context/{npc_id}"
        os.makedirs(dir_path, exist_ok=True)
        return f"{dir_path}/{timestamp}.md"

    @staticmethod
    def write(npc_id: str, entry: str) -> None:
        path = ContextAudit.log_path(npc_id)
        with open(path, "w", encoding="utf-8") as f:
            f.write(entry)
