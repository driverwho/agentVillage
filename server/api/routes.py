from fastapi import APIRouter, HTTPException
import server.core.orchestrator as orch_mod

router = APIRouter(prefix="/api")

FALLBACK_REPLIES: dict[str, str] = {
    "farmer": "得去田里干活了，改天再聊。",
    "bartender": "店里忙着呢，你先坐会儿。",
}


@router.post("/chat/{npc_id}")
async def chat_with_npc(npc_id: str, message: str, option: str | None = None):
    if npc_id not in orch_mod.orch.npcs:
        raise HTTPException(status_code=404, detail="NPC not found")

    npc = orch_mod.orch.npcs[npc_id]
    input_text = option if option else message

    # Token耗尽检查
    if npc.budget.status.value == "exhausted":
        templates = {
            "farmer": "得去田里干活了，改天再聊。",
            "bartender": "店里忙着呢，你先坐会儿。",
        }
        return {"reply": templates.get(npc_id, "我现在很忙，晚点再聊。"), "options": []}

    # 夜间检查
    if not npc.can_interact(orch_mod.orch.time_system.game_time):
        return {"reply": "（NPC正在休息，无法交互）", "options": []}

    # 组装上下文 + 调用LLM（如果API key可用）
    try:
        from server.llm.context_builder import ContextBuilder, BuildParams
        from server.llm.context_audit import ContextAudit
        from server.config import config as game_config

        # 从配置文件加载 ContextBuilder，warning 状态时缩减上限
        model_limit = game_config.LLM_CONTEXT_LIMIT
        if npc.budget.status.value == "warning":
            model_limit = int(model_limit * 0.7)

        builder = ContextBuilder.from_config(game_config)
        builder.model_limit = model_limit

        visible_state = npc.get_visible_state(orch_mod.orch.player_state)
        world_state = {
            "day": orch_mod.orch.time_system.game_time.day,
            "hour": orch_mod.orch.time_system.game_time.hour,
            "weather": "晴",
            "events": "今日无事",
        }

        # 转换dialogue_history格式
        history_dicts = []
        for turn in npc.dialogue_history[-10:]:
            role = "user" if turn.speaker == "player" else "assistant"
            history_dicts.append({"role": role, "content": turn.content})

        # 读取记忆文件
        memory_files = {
            "user.md": npc.memory._read("user.md"),
            "self.md": npc.memory._read("self.md"),
            "agent_mem.md": npc.memory._read("agent_mem.md"),
            "world.md": "",
        }

        params = BuildParams(
            identity=npc.identity,
            npc_state=npc.state,
            world_state=world_state,
            interlocutor={
                "name": "玩家",
                "summary": npc.memory.get_user_summary(),
                "visible_state": str(visible_state) if visible_state else "",
            },
            memory_files=memory_files,
            dialogue_history=history_dicts,
            current_input=input_text,
            background=npc.background if hasattr(npc, "background") else {},
        )

        result = builder.build(params)

        # 疲倦模式：跳过 LLM 调用
        if result.budget_status == "tired":
            import random
            return {
                "reply": random.choice(list(FALLBACK_REPLIES.values())),
                "options": ["点头示意", "默默走开"],
            }

        # 审计日志（异步写入，不阻塞）
        import asyncio as _asyncio
        try:
            lay_ers = {k: v for k, v in result.audit.items() if k.startswith("L")}
            entry = ContextAudit.format_entry(
                npc_id=npc_id,
                layers=lay_ers,
                total_tokens=result.audit.get("total_tokens", 0),
                model_limit=result.audit.get("model_limit", builder.model_limit),
                budget_status=result.budget_status,
            )
            _asyncio.create_task(_asyncio.to_thread(ContextAudit.write, npc_id, entry))
        except Exception:
            pass

        messages = result.messages

        options = []
        # 调用LLM（兼容无API key的情况）
        import time as _time
        _t0 = _time.time()
        llm_success = True
        llm_error = ""
        llm_model = "fallback"
        resp = None
        try:
            from server.llm.client import get_llm_client
            client = get_llm_client()
            llm_model = client.model
            print(f"[Chat] 调用 LLM — NPC: {npc_id}, 模型: {llm_model}, 消息数: {len(messages)}")
            resp = await client.chat_with_retry(messages)
            reply = resp["choices"][0]["message"]["content"]
            estimated_tokens = len(reply) // 2 + len(str(messages)) // 2
            npc.budget.consume(estimated_tokens)
            print(f"[Chat] LLM 成功 — NPC: {npc_id}, 耗时: {(_time.time() - _t0)*1000:.0f}ms, 预估token: {estimated_tokens}")
        except Exception as exc:
            llm_success = False
            llm_error = str(exc)
            import traceback
            print(f"[Chat] LLM 失败 — NPC: {npc_id}, 错误:\n{traceback.format_exc()}")
            reply = f"{npc.identity['name']}对你点点头。"
            options = ["询问近况", "闲聊一会儿", "有事想请你帮忙"]
            estimated_tokens = 0

        _latency = (_time.time() - _t0) * 1000
        try:
            from server.llm.request_logger import llm_logger
            llm_logger.log(
                npc_id=npc_id,
                model=llm_model,
                request_messages=list(messages),
                response_raw=resp if llm_success else None,
                estimated_tokens=estimated_tokens,
                latency_ms=_latency,
                success=llm_success,
                error=llm_error,
            )
        except Exception:
            pass

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


@router.post("/tool/farming")
async def use_farming_tool():
    from server.tools.farming import FarmingTool
    tool = FarmingTool()
    can_use, reason = tool.check_preconditions(orch_mod.orch.player_state)
    if not can_use:
        raise HTTPException(status_code=400, detail=reason)

    far_npc = orch_mod.orch.npcs.get("farmer")
    far_state = far_npc.state if far_npc else None
    result = tool.execute(orch_mod.orch.player_state, far_state)
    return result


@router.get("/player")
async def get_player():
    return orch_mod.orch.player_state.__dict__
