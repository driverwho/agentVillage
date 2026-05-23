import json
from fastapi import APIRouter, HTTPException, WebSocket
from fastapi.responses import StreamingResponse
import server.core.orchestrator as orch_mod
from server.api.ws import observe_manager

router = APIRouter(prefix="/api")

FALLBACK_REPLIES: dict[str, str] = {
    "farmer": "得去田里干活了，改天再聊。",
    "bartender": "店里忙着呢，你先坐会儿。",
}


def _build_messages(npc, input_text: str) -> tuple[list, object, str, int]:
    """组装 LLM 请求消息，返回 (messages, builder, budget_status, estimated_reply_tokens)"""
    from server.llm.context_builder import ContextBuilder, BuildParams, ScenarioType
    from server.config import config as game_config

    model_limit = game_config.LLM_CONTEXT_LIMIT
    if npc.budget.status.value == "warning":
        model_limit = int(model_limit * 0.7)

    builder = ContextBuilder.from_config(game_config)
    builder.model_limit = model_limit

    visible_state = npc.get_visible_state(orch_mod.orch.player_state)
    world_state = {
        "day": orch_mod.orch.time_system.game_time.day,
        "hour": orch_mod.orch.time_system.game_time.hour,
        "weather": orch_mod.orch.event_engine.get_current_weather(),
        "events": orch_mod.orch.event_engine.get_world_events_text(),
    }

    history_dicts = []
    for turn in npc.dialogue_history[-10:]:
        role = "user" if turn.speaker == "player" else "assistant"
        history_dicts.append({"role": role, "content": turn.content})

    memory_files = {
        "agent_mem.md": npc.memory._read("agent_mem.md"),
        "world.md": "",
    }

    params = BuildParams(
        scenario=ScenarioType.PLAYER_DIALOGUE,
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
    return result.messages, builder, result.budget_status, result.audit.get("total_tokens", 0)


def _write_audit(npc_id: str, builder, budget_status: str):
    """异步写入审计日志（fire-and-forget）"""
    import asyncio as _asyncio
    try:
        from server.llm.context_audit import ContextAudit
        # 使用最近的 build 参数生成空审计（简化版）
        entry = ContextAudit.format_entry(
            npc_id=npc_id,
            layers={},
            total_tokens=0,
            model_limit=builder.model_limit,
            budget_status=budget_status,
        )
        _asyncio.create_task(_asyncio.to_thread(ContextAudit.write, npc_id, entry))
    except Exception:
        pass


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

    try:
        messages, builder, budget_status, _audit_tokens = _build_messages(npc, input_text)

        if budget_status == "tired":
            import random
            return {
                "reply": random.choice(list(FALLBACK_REPLIES.values())),
                "options": ["点头示意", "默默走开"],
            }

        _write_audit(npc_id, builder, budget_status)

        options = []
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


@router.post("/chat/{npc_id}/stream")
async def chat_with_npc_stream(npc_id: str, message: str, option: str | None = None):
    """SSE 流式聊天端点"""
    if npc_id not in orch_mod.orch.npcs:
        raise HTTPException(status_code=404, detail="NPC not found")

    npc = orch_mod.orch.npcs[npc_id]
    input_text = option if option else message

    if npc.budget.status.value == "exhausted":
        return {"reply": FALLBACK_REPLIES.get(npc_id, "我现在很忙，晚点再聊。"), "options": []}

    if not npc.can_interact(orch_mod.orch.time_system.game_time):
        return {"reply": "（NPC正在休息，无法交互）", "options": []}

    try:
        messages, builder, budget_status, _audit_tokens = _build_messages(npc, input_text)

        if budget_status == "tired":
            import random
            return {
                "reply": random.choice(list(FALLBACK_REPLIES.values())),
                "options": ["点头示意", "默默走开"],
            }

        _write_audit(npc_id, builder, budget_status)

        from server.llm.client import get_llm_client
        llm_client = get_llm_client()

        async def sse_generator():
            full_reply = ""
            try:
                print(f"[Chat] 流式调用 LLM — NPC: {npc_id}, 模型: {llm_client.model}, 消息数: {len(messages)}")
                async for chunk in llm_client.chat_stream(messages):
                    full_reply += chunk
                    yield f"data: {json.dumps({'delta': chunk})}\n\n"
                yield f"data: {json.dumps({'done': True})}\n\n"
                print(f"[Chat] 流式完成 — NPC: {npc_id}, 回复长度: {len(full_reply)}")

                estimated_tokens = len(full_reply) // 2
                npc.budget.consume(estimated_tokens)

                # 记录对话
                from server.models.messages import DialogueTurn
                npc.dialogue_history.append(DialogueTurn(speaker="player", content=input_text))
                npc.dialogue_history.append(DialogueTurn(speaker=npc_id, content=full_reply))
                npc.memory.add_dialogue(DialogueTurn(speaker="player", content=input_text))

                # 解析选项
                options = []
                if "[OPTIONS]" in full_reply:
                    parts = full_reply.split("[OPTIONS]")
                    options = [opt.strip() for opt in parts[1].strip().split("\n") if opt.strip()]
                yield f"data: {json.dumps({'options': options})}\n\n"

            except Exception as exc:
                import traceback
                print(f"[Chat] 流式失败 — NPC: {npc_id}, 错误:\n{traceback.format_exc()}")
                yield f"data: {json.dumps({'error': str(exc)})}\n\n"

        return StreamingResponse(
            sse_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
        )

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


@router.post("/npc/{npc_id}/turn")
async def npc_autonomous_turn(npc_id: str):
    """触发一次 NPC 自主决策 turn（工具系统）。

    NPC 根据当前状态 + 可用工具，由 LLM 决定行为。
    """
    if npc_id not in orch_mod.orch.npcs:
        raise HTTPException(status_code=404, detail="NPC not found")

    npc = orch_mod.orch.npcs[npc_id]

    if not hasattr(npc, "tool_registry") or npc.tool_registry is None:
        raise HTTPException(status_code=500, detail="工具系统未初始化")

    from server.tools.setup import build_policy_context
    from server.llm.context_builder import ContextBuilder, BuildParams, ScenarioType

    game_time = orch_mod.orch.time_system.game_time
    policy_ctx = build_policy_context(npc, game_time)

    from server.config import config as game_config
    builder = ContextBuilder.from_config(game_config)
    world_state = {
        "day": game_time.day,
        "hour": game_time.hour,
        "weather": "晴",
        "events": "今日无事",
    }
    params = BuildParams(
        scenario=ScenarioType.AUTONOMOUS_DECISION,
        identity=npc.identity,
        npc_state=npc.state,
        world_state=world_state,
        interlocutor={},
        memory_files={"agent_mem.md": npc.memory._read("agent_mem.md")},
        dialogue_history=[],
        current_input="现在轮到你行动了。根据当前状态和时间，选择一个合适的行为。",
        background=npc.background,
    )
    build_result = builder.build(params)
    messages = build_result.messages

    policy_ctx["npc_states"] = {npc_id: npc.state}
    try:
        result = await npc.run_tool_turn(context=policy_ctx, messages=messages)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Turn 执行失败: {e}")

    if result.get("tool_used"):
        usage = getattr(npc, "_daily_usage", {})
        tool_name = result["tool_used"]
        usage[tool_name] = usage.get(tool_name, 0) + 1
        npc._daily_usage = usage

    return {
        "npc_id": npc_id,
        "tool_used": result.get("tool_used"),
        "tool_result": result.get("tool_result"),
        "text_reply": result.get("text_reply"),
        "state_after": {
            "health": npc.state.health,
            "hunger": npc.state.hunger,
            "fatigue": npc.state.fatigue,
            "mood": npc.state.mood,
        },
    }


@router.get("/npcs/status")
def get_npcs_status():
    """返回所有 NPC 的当前快照（供观察页面使用）。"""
    game_time = orch_mod.orch.time_system.game_time
    npcs_data = {}
    for npc_id, npc in orch_mod.orch.npcs.items():
        npcs_data[npc_id] = {
            "name": npc.identity.get("name", npc_id),
            "location": npc.location,
            "activity": {
                "status": npc.activity_state.status,
                "current_tool": npc.activity_state.current_tool,
                "end_day": npc.activity_state.end_day,
                "end_hour": npc.activity_state.end_hour,
                "idle_reason": npc.activity_state.idle_reason,
            },
            "state": {
                "health": npc.state.health,
                "hunger": npc.state.hunger,
                "fatigue": npc.state.fatigue,
                "mood": npc.state.mood,
            },
            "llm_status": "idle",
            "history": [],
        }
    return {
        "npcs": npcs_data,
        "game_time": game_time.to_dict(),
        "world_events": [
            {"id": e.id, "name": e.name, "description": e.description,
             "started_hour": e.started_hour}
            for e in orch_mod.orch.event_engine.state.active_events
        ],
    }


@router.websocket("/ws/observe")
async def ws_observe(websocket: WebSocket):
    await observe_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except Exception:
        observe_manager.disconnect(websocket)
