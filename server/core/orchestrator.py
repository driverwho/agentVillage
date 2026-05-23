from typing import Dict, Any
import asyncio
from server.core.time_system import TimeSystem
from server.core.message_bus import MessageBus
from server.core.state_store import JsonStore
from server.core.activity_manager import ActivityManager
from server.models.player_state import PlayerState
from server.agents.farmer import FarmerAgent
from server.agents.bartender import BartenderAgent
from server.llm.token_budget import TokenBudget

# 全局实例，由 main.py 初始化
orch: "Orchestrator | None" = None

AUTO_TICK_INTERVAL = 10  # 每 10 秒 = 1 游戏小时


class Orchestrator:
    def __init__(self, user_id: str = "default"):
        self.user_id = user_id
        self.time_system = TimeSystem()
        self.message_bus = MessageBus()
        self.store = JsonStore(base_path=f"data/users/{user_id}")
        self.npcs: Dict[str, Any] = {}
        self.player_state = PlayerState(name="玩家")
        self.activity_manager = ActivityManager()
        self._auto_tick_task: asyncio.Task | None = None
        self._init_npcs()
        self._init_event_system()
        self._init_location_registry()
        self._init_hooks()

    def _init_npcs(self) -> None:
        from server.core.background_manager import BackgroundManager

        agent_cls = {
            "farmer": FarmerAgent,
            "bartender": BartenderAgent,
        }
        memory_base = f"data/users/{self.user_id}/memory"
        for npc_id, cls in agent_cls.items():
            bg = BackgroundManager.get(npc_id)
            self.npcs[npc_id] = cls(
                background=bg,
                memory_base=memory_base,
                budget=TokenBudget(daily_limit=5000),
            )

        from server.tools.setup import init_tool_system
        init_tool_system(self.npcs)

    def _init_event_system(self) -> None:
        from server.core.event_engine import EventEngine, EventState, ActiveEvent, load_event_defs

        saved = self.store.load("event_state")
        if saved:
            state = EventState(
                active_events=[ActiveEvent(**e) for e in saved.get("active_events", [])],
                cooldowns=saved.get("cooldowns", {}),
            )
        else:
            state = EventState()
        event_defs = load_event_defs("server/data/events")
        self.event_engine = EventEngine(event_defs=event_defs, state=state)

    def _init_location_registry(self) -> None:
        from server.core.location_registry import LocationRegistry

        saved = self.store.load("locations")
        if saved:
            self.location_registry = LocationRegistry(initial=saved)
        else:
            merged: Dict[str, list] = {}
            for npc_id, npc in self.npcs.items():
                merged.setdefault(npc.location, []).append(npc_id)
            self.location_registry = LocationRegistry(initial=merged)

    def _init_hooks(self) -> None:
        from server.hooks import HookRegistry
        from server.hooks.interaction_hook import InteractionHook
        from server.core.interaction_runner import InteractionRunner
        from server.llm.context_builder import ContextBuilder
        from server.llm.client import get_llm_client
        from server.config import config as game_config

        self.hook_registry = HookRegistry()
        builder = ContextBuilder.from_config(game_config)
        runner = InteractionRunner(context_builder=builder, llm_client=get_llm_client())
        interaction_hook = InteractionHook(
            npc_registry=self.npcs,
            location_registry=self.location_registry,
            interaction_runner=runner,
        )
        self.hook_registry.register(interaction_hook)

    def advance_time(self, minutes: int = 60) -> None:
        if self.time_system.is_paused:
            self.time_system.is_paused = False
        is_hour = self.time_system.tick(minutes)
        if is_hour:
            self._on_hour_tick()
        self._auto_save()

    def _on_hour_tick(self) -> None:
        """每小时 tick 的核心逻辑。"""
        from server.api.ws import observe_manager, ws_manager

        game_time = self.time_system.game_time
        hour = game_time.hour

        def _broadcast(data: dict):
            try:
                asyncio.ensure_future(observe_manager.broadcast(data))
            except RuntimeError:
                pass

        def _broadcast_all(data: dict):
            """同时广播到 observe 和主 WS。"""
            _broadcast(data)
            try:
                asyncio.ensure_future(ws_manager.broadcast(data))
            except RuntimeError:
                pass

        # 步骤 0: 广播时间更新（到所有客户端）
        _broadcast_all({
            "type": "game_time_update",
            "day": game_time.day,
            "hour": game_time.hour,
            "minute": 0,
        })

        # 步骤 0.5: 事件引擎 tick
        prev_event_ids = [e.id for e in self.event_engine.state.active_events]
        self.event_engine.tick(game_time)
        curr_event_ids = [e.id for e in self.event_engine.state.active_events]
        if prev_event_ids != curr_event_ids:
            _broadcast_all({
                "type": "world_events_update",
                "events": [
                    {"id": e.id, "name": e.name, "description": e.description,
                     "started_hour": e.started_hour}
                    for e in self.event_engine.state.active_events
                ],
            })

        # 步骤 1: 更新所有 NPC 状态值
        for npc in self.npcs.values():
            npc.on_hour_tick(game_time)

        # 广播状态更新
        for npc_id, npc in self.npcs.items():
            _broadcast({
                "type": "npc_state_update",
                "npc_id": npc_id,
                "health": npc.state.health,
                "hunger": npc.state.hunger,
                "fatigue": npc.state.fatigue,
                "mood": npc.state.mood,
            })

        # 步骤 2: 检查事件中断
        for npc_id, npc in self.npcs.items():
            if npc.activity_state.status != "active":
                continue
            reason = self.activity_manager.check_interrupts(npc.activity_state, npc.state)
            if reason:
                tool = npc.activity_state.current_tool
                self.activity_manager.transition_to_idle(
                    npc.activity_state, f"因为{reason}中断了{tool}"
                )
                print(f"[AutoTick] {npc_id} 被中断: {reason}")
                npc.activity_log.append(f"{hour}:00 {tool} — 因为{reason}中断了{tool}")
                _broadcast({
                    "type": "npc_activity_change",
                    "npc_id": npc_id,
                    "status": npc.activity_state.status,
                    "current_tool": npc.activity_state.current_tool,
                    "end_day": npc.activity_state.end_day,
                    "end_hour": npc.activity_state.end_hour,
                    "idle_reason": npc.activity_state.idle_reason,
                    "location": npc.location,
                })

        # 步骤 3: 检查活动完成
        for npc_id, npc in self.npcs.items():
            if npc.activity_state.status != "active":
                continue
            if self.activity_manager.check_completion(npc.activity_state, game_time):
                tool = npc.activity_state.current_tool
                self.activity_manager.transition_to_idle(
                    npc.activity_state, f"完成了{tool}"
                )
                print(f"[AutoTick] {npc_id} 完成活动: {tool}")
                npc.activity_log.append(f"{hour}:00 {tool} — 完成了{tool}")
                _broadcast({
                    "type": "npc_activity_change",
                    "npc_id": npc_id,
                    "status": npc.activity_state.status,
                    "current_tool": npc.activity_state.current_tool,
                    "end_day": npc.activity_state.end_day,
                    "end_hour": npc.activity_state.end_hour,
                    "idle_reason": npc.activity_state.idle_reason,
                    "location": npc.location,
                })

        # 步骤 4: 检查决策点
        if self.activity_manager.is_decision_point(hour):
            for npc_id, npc in self.npcs.items():
                if npc.activity_state.status == "active":
                    tool = npc.activity_state.current_tool
                    self.activity_manager.transition_to_idle(
                        npc.activity_state, f"到了{hour}:00决策时间"
                    )
                    print(f"[AutoTick] {npc_id} 决策点中断: {hour}:00")
                    npc.activity_log.append(f"{hour}:00 {tool} — 到了决策时间")
                    _broadcast({
                        "type": "npc_activity_change",
                        "npc_id": npc_id,
                        "status": npc.activity_state.status,
                        "current_tool": npc.activity_state.current_tool,
                        "end_day": npc.activity_state.end_day,
                        "end_hour": npc.activity_state.end_hour,
                        "idle_reason": npc.activity_state.idle_reason,
                        "location": npc.location,
                    })

        # 步骤 5: 对所有 idle NPC 触发自主决策
        idle_npcs = [
            (npc_id, npc) for npc_id, npc in self.npcs.items()
            if npc.activity_state.status == "idle"
        ]
        if idle_npcs:
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self._run_autonomous_turns(idle_npcs))
            except RuntimeError:
                pass  # 无 event loop 时跳过（同步调用场景）

    async def _run_autonomous_turns(self, idle_npcs: list) -> None:
        """并发对所有 idle NPC 执行自主决策。"""
        game_time = self.time_system.game_time
        tasks = []

        for npc_id, npc in idle_npcs:
            if npc.budget.status.value == "exhausted":
                print(f"[AutoTick] {npc_id} token 耗尽，默认 rest")
                self.activity_manager.transition_to_active(
                    npc.activity_state, "rest", 2, game_time
                )
                continue

            tasks.append(self._single_autonomous_turn(npc_id, npc, game_time))

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def _single_autonomous_turn(self, npc_id, npc, game_time) -> None:
        """单个 NPC 的自主决策 turn。"""
        from server.tools.setup import build_policy_context, build_autonomous_context
        from server.llm.context_builder import ContextBuilder, BuildParams, ScenarioType
        from server.config import config as game_config
        from server.api.ws import observe_manager

        try:
            await observe_manager.broadcast({
                "type": "npc_llm_start",
                "npc_id": npc_id,
                "timestamp": f"Day{game_time.day} {game_time.hour}:00",
            })

            builder = ContextBuilder.from_config(game_config)
            world_state = {
                "day": game_time.day,
                "hour": game_time.hour,
                "weather": self.event_engine.get_current_weather(),
                "events": self.event_engine.get_world_events_text(),
            }
            autonomous_input = build_autonomous_context(npc, game_time)
            params = BuildParams(
                scenario=ScenarioType.AUTONOMOUS_DECISION,
                identity=npc.identity,
                npc_state=npc.state,
                world_state=world_state,
                interlocutor={},
                memory_files={
                    "agent_mem.md": npc.memory._read("agent_mem.md"),
                    "self.md": npc.memory._read("self.md"),
                },
                dialogue_history=[],
                current_input=autonomous_input,
                background=npc.background,
            )
            build_result = builder.build(params)
            messages = build_result.messages

            policy_ctx = build_policy_context(npc, game_time)
            policy_ctx["npc_states"] = {npc_id: npc.state}

            result = await npc.run_tool_turn(context=policy_ctx, messages=messages)

            tool_name = result.get("tool_used")
            if tool_name:
                tool = npc.tool_registry.get(tool_name)
                duration = tool.duration_hours if tool else 1
                if duration == -1:
                    duration = self.activity_manager.calculate_sleep_duration(game_time.hour)
                if tool_name == "sleep":
                    await _trigger_dream(npc, game_time, world_state.get("events", "今日无事"))
                self.activity_manager.transition_to_active(
                    npc.activity_state, tool_name, duration, game_time
                )
                if tool_name == "move" and result.get("tool_result"):
                    new_loc = result["tool_result"].get("state_changes", {}).get("location")
                    if new_loc:
                        old_loc = self.location_registry.get_location(npc_id)
                        self.location_registry.move(npc_id, old_loc, new_loc)
                        npc.location = new_loc
                        await self.hook_registry.fire("post_move", {
                            "actor_id": npc_id,
                            "location": new_loc,
                            "game_time": game_time,
                        })
            else:
                self.activity_manager.transition_to_active(
                    npc.activity_state, "_idle_wander", 1, game_time
                )

            print(f"[AutoTick] {npc_id} 决策完成: {npc.activity_state.current_tool} "
                  f"(到 Day{npc.activity_state.end_day} {npc.activity_state.end_hour}:00)")

            msg = ""
            if result.get("tool_result"):
                msg = result["tool_result"].get("message", "")
            elif result.get("text_reply"):
                msg = result["text_reply"][:50]

            await observe_manager.broadcast({
                "type": "npc_llm_done",
                "npc_id": npc_id,
                "tool_used": tool_name or "_idle_wander",
                "message": msg,
                "tokens": 0,
                "timestamp": f"Day{game_time.day} {game_time.hour}:00",
            })
            await observe_manager.broadcast({
                "type": "npc_activity_change",
                "npc_id": npc_id,
                "status": npc.activity_state.status,
                "current_tool": npc.activity_state.current_tool,
                "end_day": npc.activity_state.end_day,
                "end_hour": npc.activity_state.end_hour,
                "idle_reason": npc.activity_state.idle_reason,
                "location": npc.location,
            })

        except Exception as e:
            print(f"[AutoTick] {npc_id} 自主决策失败: {e}")
            self.activity_manager.transition_to_active(
                npc.activity_state, "rest", 2, game_time
            )

    def _auto_save(self) -> None:
        self.store.save("world_state", {
            "game_time": self.time_system.game_time.to_dict(),
            "is_paused": self.time_system.is_paused,
        })
        self.store.save("player_state", self.player_state.__dict__)
        self.store.save("locations", self.location_registry.to_dict())
        self.store.save("event_state", {
            "active_events": [
                {"id": e.id, "name": e.name, "description": e.description,
                 "started_day": e.started_day, "started_hour": e.started_hour,
                 "expires_day": e.expires_day, "expires_hour": e.expires_hour}
                for e in self.event_engine.state.active_events
            ],
            "cooldowns": self.event_engine.state.cooldowns,
        })

    async def _auto_tick_loop(self) -> None:
        while True:
            await asyncio.sleep(AUTO_TICK_INTERVAL)
            if not self.time_system.is_paused:
                self.advance_time(60)

    def start_auto_tick(self) -> None:
        if self._auto_tick_task is None:
            self._auto_tick_task = asyncio.create_task(self._auto_tick_loop())

    def stop_auto_tick(self) -> None:
        if self._auto_tick_task:
            self._auto_tick_task.cancel()
            self._auto_tick_task = None

    def get_world_state(self) -> dict:
        return {
            "game_time": self.time_system.game_time.to_dict(),
            "is_paused": self.time_system.is_paused,
            "npcs": {
                nid: {
                    "state": {
                        "health": n.state.health,
                        "hunger": n.state.hunger,
                        "fatigue": n.state.fatigue,
                        "mood": n.state.mood,
                    },
                    "activity": {
                        "status": n.activity_state.status,
                        "current_tool": n.activity_state.current_tool,
                        "location": n.location,
                    },
                }
                for nid, n in self.npcs.items()
            },
        }


def _build_dream_prompt(npc_name: str, activity_log: list, today_events: str) -> str:
    """构建 Dream 总结 prompt。"""
    activity_text = "\n".join(activity_log) if activity_log else "（今天没做什么特别的事）"

    social_entries = [e for e in activity_log if "gossip" in e or "trade" in e]
    social_text = "\n".join(social_entries) if social_entries else "今天没有与人交流"

    events_text = today_events if today_events and today_events != "今日无事" else "今日平静无事"

    return (
        f"你是{npc_name}。现在你准备入睡，回顾今天发生的事情。\n\n"
        f"【今日活动记录】\n{activity_text}\n\n"
        f"【今日世界事件】\n{events_text}\n\n"
        f"【今日社交互动】\n{social_text}\n\n"
        f"请用第一人称写一段简短的日终回顾（3-5句话），包含：\n"
        f"1. 今天主要做了什么\n"
        f"2. 如果有特殊事件发生，你对此的感想\n"
        f"3. 如果有社交互动，你对那个人的印象变化\n\n"
        f"注意：用你自己的语气和性格来写，不要列清单。"
    )


async def _trigger_dream(npc, game_time, today_events: str = "今日无事") -> None:
    """NPC 入睡时触发 dream：LLM 总结当天活动。"""
    if not npc.activity_log:
        return

    from server.llm.client import get_llm_client

    prompt = _build_dream_prompt(npc.identity["name"], npc.activity_log, today_events)
    client = get_llm_client()

    try:
        response = await client.chat(
            [{"role": "user", "content": prompt}],
            model=None,
        )
        summary = response.get("choices", [{}])[0].get("message", {}).get("content", "")
        if summary:
            npc.memory.write_daily_summary(game_time.day, summary.strip())
            print(f"[Dream] {npc.agent_id} Day{game_time.day} 总结已写入: {summary[:50]}...")
    except Exception as e:
        print(f"[Dream] {npc.agent_id} 总结失败: {e}")

    npc.activity_log.clear()
