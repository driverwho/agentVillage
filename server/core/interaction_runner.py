from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple
from server.models.game_time import GameTime
from server.llm.context_builder import ContextBuilder, BuildParams, ScenarioType


@dataclass
class ConversationResult:
    participants: Tuple[str, str]
    location: str
    dialogue: List[Dict[str, str]]
    summary: str
    game_time: GameTime


class InteractionRunner:
    def __init__(self, context_builder: ContextBuilder, llm_client):
        self.context_builder = context_builder
        self.llm_client = llm_client

    async def run_conversation(self, initiator, target,
                               location: str, game_time: GameTime) -> ConversationResult:
        from server.core.activity_manager import ActivityManager

        activity_mgr = ActivityManager()
        activity_mgr.transition_to_active(initiator.activity_state, "socializing", 1, game_time)
        activity_mgr.transition_to_active(target.activity_state, "socializing", 1, game_time)

        dialogue: List[Dict[str, str]] = []
        speakers = [initiator, target, initiator, target]

        summary = ""
        for i, speaker in enumerate(speakers):
            listener = target if speaker is initiator else initiator
            is_last_turn = (i == 3)
            prompt = self._build_interaction_prompt(speaker, listener, dialogue, i, is_last_turn)

            rel = speaker.background.get("relationships", {}).get(
                listener.id if hasattr(listener, 'id') else listener.agent_id, {}
            )
            if not isinstance(rel, dict):
                rel = {}

            speaker_id = speaker.id if hasattr(speaker, 'id') else speaker.agent_id
            params = BuildParams(
                scenario=ScenarioType.NPC_INTERACTION,
                identity=speaker.identity,
                npc_state=speaker.state,
                world_state={"day": game_time.day, "hour": game_time.hour, "weather": "晴"},
                interlocutor={
                    "id": listener.id if hasattr(listener, 'id') else listener.agent_id,
                    "name": listener.identity.get("name", "某人"),
                    "summary": rel.get("shared_history", ""),
                },
                memory_files={
                    "agent_mem.md": speaker.memory._read("agent_mem.md"),
                },
                dialogue_history=[
                    {"role": "assistant" if d["speaker"] == speaker_id else "user",
                     "content": d["content"]}
                    for d in dialogue
                ],
                current_input=prompt,
                background=speaker.background,
            )
            build_result = self.context_builder.build(params)
            response = await self.llm_client.chat(build_result.messages)
            content = response.get("choices", [{}])[0].get("message", {}).get("content", "...")

            if is_last_turn and "[总结]" in content:
                parts = content.split("[总结]", 1)
                dialogue.append({"speaker": speaker_id, "content": parts[0].strip()})
                summary = parts[1].strip()
            else:
                dialogue.append({"speaker": speaker_id, "content": content.strip()})

        if not summary:
            init_name = initiator.identity.get("name", "某人")
            target_name = target.identity.get("name", "某人")
            summary = f"{init_name}和{target_name}聊了几句。"

        self._write_results(initiator, target, dialogue, summary, game_time, location)

        return ConversationResult(
            participants=(
                initiator.id if hasattr(initiator, 'id') else initiator.agent_id,
                target.id if hasattr(target, 'id') else target.agent_id,
            ),
            location=location,
            dialogue=dialogue,
            summary=summary,
            game_time=game_time,
        )

    def _build_interaction_prompt(self, speaker, listener, dialogue, turn_index, is_last) -> str:
        listener_name = listener.identity.get("name", "某人")
        if turn_index == 0:
            base = f"你在当前地点遇到了{listener_name}。请自然地打个招呼或开启一段对话。只说一两句话。"
        elif turn_index % 2 == 0:
            base = f"继续和{listener_name}的对话。只说一两句话。"
        else:
            speaker_name = speaker.identity.get("name", "你")
            base = f"{speaker_name}，{listener_name}对你说了话，请自然地回应。只说一两句话。"

        if is_last:
            base += "\n\n在你的回复最后，用 [总结] 标记开头写一句话总结这次对话的要点。"
        return base

    def _write_results(self, initiator, target, dialogue, summary, game_time, location) -> None:
        from server.tools.setup import LOCATION_NAMES
        location_cn = LOCATION_NAMES.get(location, location)

        for npc in [initiator, target]:
            other = target if npc is initiator else initiator
            other_name = other.identity.get("name", "某人")
            entry = f"{game_time.hour}:00 socializing — 在{location_cn}与{other_name}交谈：{summary}"
            npc.activity_log.append(entry)
            if not hasattr(npc, "recent_social"):
                npc.recent_social = []
            npc.recent_social.append({
                "day": game_time.day,
                "hour": game_time.hour,
                "partner": other_name,
                "summary": summary,
            })
