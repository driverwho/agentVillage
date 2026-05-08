from typing import List, Dict
from server.models.npc_state import NPCState


class ContextBuilder:
    @staticmethod
    def build_npc_context(
        identity: dict,
        npc_state: NPCState,
        world_events: str,
        user_summary: str,
        visible_player_state: dict,
        dialogue_history: List[dict],
        budget_status: str = "normal",
    ) -> List[Dict[str, str]]:
        descriptions = npc_state.describe()
        state_text = (
            f"你现在很{descriptions['health']}。"
            f"{descriptions['hunger']}。"
            f"{descriptions['fatigue']}。"
        )

        player_text = f"玩家当前状态：{visible_player_state}"

        context = (
            f"【世界事件】{world_events}\n"
            f"【玩家印象】{user_summary}\n"
            f"【玩家状态】{player_text}\n"
        )

        system_prompt = f"""你是{identity['name']}。{identity['daily_habits']}
{identity['core_motivation']}
{identity['speaking_style']}
注意：{identity['secret']}（这是你内心的秘密，不要直接告诉别人，除非极度信任）

你的当前状态：{state_text}

世界背景：{context}

你正在与玩家对话。请用第一人称回复，每次回复同时生成2-3个后续选项（放在[OPTIONS]标签后，每行一个选项）。"""

        if budget_status == "warning":
            system_prompt += "\n你现在有些疲惫，请简短回复。"

        messages = [{"role": "system", "content": system_prompt}]
        for turn in dialogue_history[-5:]:
            messages.append({"role": turn.get("role", "user"), "content": turn["content"]})
        return messages
