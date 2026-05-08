from server.llm.context_builder import ContextBuilder
from server.models.npc_state import NPCState


def test_build_npc_context():
    identity = {
        "name": "农夫王大爷",
        "daily_habits": "日出而作",
        "core_motivation": "守住三亩地",
        "speaking_style": "说话慢条斯理",
        "secret": "年轻时是拳师",
    }
    state = NPCState(health=80, hunger=30, fatigue=60)
    ctx = ContextBuilder.build_npc_context(
        identity=identity,
        npc_state=state,
        world_events="今日无事",
        user_summary="一个陌生人",
        visible_player_state={"basic": {"health": 100}},
        dialogue_history=[],
    )
    assert ctx[0]["role"] == "system"
    assert "农夫王大爷" in ctx[0]["content"]
    assert "肚子在咕咕叫" in ctx[0]["content"]


def test_build_npc_context_warning():
    identity = {"name": "测试", "daily_habits": "", "core_motivation": "", "speaking_style": "", "secret": ""}
    state = NPCState()
    ctx = ContextBuilder.build_npc_context(
        identity=identity, npc_state=state,
        world_events="", user_summary="",
        visible_player_state={}, dialogue_history=[],
        budget_status="warning",
    )
    assert "简短回复" in ctx[0]["content"]
