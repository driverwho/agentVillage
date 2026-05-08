from fastapi import APIRouter, HTTPException
from server.core.orchestrator import orch

router = APIRouter(prefix="/api")


@router.post("/chat/{npc_id}")
async def chat_with_npc(npc_id: str, message: str, option: str | None = None):
    if npc_id not in orch.npcs:
        raise HTTPException(status_code=404, detail="NPC not found")

    npc = orch.npcs[npc_id]
    input_text = option if option else message

    # Token耗尽检查
    if npc.budget.status.value == "exhausted":
        templates = {
            "farmer": "得去田里干活了，改天再聊。",
            "bartender": "店里忙着呢，你先坐会儿。",
        }
        return {"reply": templates.get(npc_id, "我现在很忙，晚点再聊。"), "options": []}

    # 夜间检查
    if not npc.can_interact(orch.time_system.game_time):
        return {"reply": "（NPC正在休息，无法交互）", "options": []}

    # 组装上下文 + 调用LLM（如果API key可用）
    try:
        from server.llm.context_builder import ContextBuilder
        visible_state = npc.get_visible_state(orch.player_state)
        world_events = "今日无事"
        user_summary = npc.memory.get_user_summary()

        # 转换dialogue_history格式
        history_dicts = []
        for turn in npc.dialogue_history[-5:]:
            role = "user" if turn.speaker == "player" else "assistant"
            history_dicts.append({"role": role, "content": turn.content})

        messages = ContextBuilder.build_npc_context(
            identity=npc.identity,
            npc_state=npc.state,
            world_events=world_events,
            user_summary=user_summary,
            visible_player_state=visible_state,
            dialogue_history=history_dicts,
            budget_status=npc.budget.status.value,
        )

        # 追加当前玩家输入
        messages.append({"role": "user", "content": input_text})

        options = []
        # 调用LLM（兼容无API key的情况）
        try:
            from server.llm.client import LLMClient
            client = LLMClient()
            resp = await client.chat_with_retry(messages)
            reply = resp["choices"][0]["message"]["content"]
            # 估算token（简单按字符数/2估算）
            estimated_tokens = len(reply) // 2 + len(str(messages)) // 2
            npc.budget.consume(estimated_tokens)
        except Exception:
            # LLM不可用时使用简单回复
            reply = f"{npc.identity['name']}对你点点头。"
            options = ["询问近况", "闲聊一会儿", "有事想请你帮忙"]

        # 记录对话
        from server.models.messages import DialogueTurn
        npc.dialogue_history.append(DialogueTurn(speaker="player", content=input_text))
        npc.dialogue_history.append(DialogueTurn(speaker=npc_id, content=reply))
        npc.memory.add_dialogue(DialogueTurn(speaker="player", content=input_text))

        # 解析选项（LLM回复中的[OPTIONS]指令覆盖默认选项）
        if "[OPTIONS]" in reply:
            parts = reply.split("[OPTIONS]")
            reply = parts[0].strip()
            options = [opt.strip() for opt in parts[1].strip().split("\n") if opt.strip()]

        return {"reply": reply, "options": options}

    except Exception as e:
        return {"reply": f"（出错了: {str(e)}）", "options": []}


@router.get("/player")
async def get_player():
    return orch.player_state.__dict__
