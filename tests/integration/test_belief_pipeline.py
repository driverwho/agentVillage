import pytest
import tempfile
from server.models.event import GameEvent
from server.models.belief import Belief
from server.models.game_time import GameTime
from server.core.event_log import EventLog
from server.core.belief_store import BeliefStore
from server.core.witness_engine import WitnessEngine
from server.core.belief_propagator import BeliefPropagator


class TestBeliefPipelineIntegration:
    def setup_method(self):
        self.tmpdir = tempfile.mkdtemp()
        self.event_log = EventLog(base_path=f"{self.tmpdir}/events")
        self.belief_stores = {
            "farmer": BeliefStore(npc_id="farmer", base_path=f"{self.tmpdir}/beliefs"),
            "bartender": BeliefStore(npc_id="bartender", base_path=f"{self.tmpdir}/beliefs"),
        }
        self.witness_engine = WitnessEngine(belief_stores=self.belief_stores)
        self.propagator = BeliefPropagator(belief_stores=self.belief_stores)

    def test_full_cycle_action_to_belief(self):
        """完整循环：工具执行 → 事件 → 目击 → 信念。"""
        event = GameEvent(
            type="action", timestamp={"day": 1, "hour": 10},
            actor="farmer", location="field",
            content="乔治在田地里发现了一颗奇怪的种子",
            witnesses=["farmer"],
            visibility="location",
        )
        self.event_log.append(event)
        self.witness_engine.process_event(event)

        beliefs = self.belief_stores["farmer"].get_active(current_day=1)
        assert len(beliefs) == 1
        assert "奇怪的种子" in beliefs[0].content
        assert beliefs[0].confidence == "high"

        assert len(self.belief_stores["bartender"].get_active(current_day=1)) == 0

    def test_full_cycle_gossip_propagation(self):
        """完整循环：farmer 目击 → 对话传播给 bartender。"""
        event = GameEvent(
            type="action", timestamp={"day": 1, "hour": 10},
            actor="farmer", location="field",
            content="一个陌生商人鬼鬼祟祟地进了森林",
            witnesses=["farmer"],
            visibility="location",
        )
        self.event_log.append(event)
        self.witness_engine.process_event(event)

        self.propagator.propagate_from_dialogue(
            speaker_id="farmer",
            listener_id="bartender",
            summary="乔治说他看到陌生商人进了森林",
            game_time={"day": 1, "hour": 14},
        )

        bartender_beliefs = self.belief_stores["bartender"].get_active(current_day=1)
        assert len(bartender_beliefs) == 1
        assert bartender_beliefs[0].confidence == "medium"
        assert bartender_beliefs[0].source == "told_by:farmer"

        farmer_beliefs = self.belief_stores["farmer"].get_active(current_day=1)
        assert len(farmer_beliefs) == 2

    def test_public_event_reaches_all(self):
        """公共事件所有 NPC 都知道。"""
        event = GameEvent(
            type="world", timestamp={"day": 2, "hour": 6},
            actor="world", location="village",
            content="村口来了一位旅行商人",
            witnesses=[],
            visibility="public",
        )
        self.event_log.append(event)
        self.witness_engine.process_event(event)

        for store in self.belief_stores.values():
            beliefs = store.get_active(current_day=2)
            assert any("旅行商人" in b.content for b in beliefs)

    def test_belief_retrieval_for_context(self):
        """从 BeliefStore 获取 context 注入用的信念子集。"""
        self.belief_stores["farmer"].add(Belief(
            content="亲眼看到商人", source="witnessed",
            confidence="high", acquired_at={"day": 3, "hour": 10},
            about=["world"],
        ))
        self.belief_stores["farmer"].add(Belief(
            content="听说商人有问题", source="told_by:bartender",
            confidence="medium", acquired_at={"day": 3, "hour": 14},
            about=["world"],
        ))
        self.belief_stores["farmer"].add(Belief(
            content="很久以前的小道消息", source="overheard",
            confidence="low", acquired_at={"day": 1, "hour": 8},
            about=["world"],
        ))

        context_beliefs = self.belief_stores["farmer"].get_for_context(current_day=5)
        assert len(context_beliefs) == 2
        assert context_beliefs[0].confidence == "high"

    def test_event_log_persistence(self):
        """事件持久化并可查询。"""
        for i in range(5):
            self.event_log.append(GameEvent(
                type="action", timestamp={"day": 1, "hour": 8 + i},
                actor="farmer", location="field",
                content=f"活动{i}", witnesses=["farmer"],
                visibility="location",
            ))
        log2 = EventLog(base_path=f"{self.tmpdir}/events")
        day1 = log2.query(day=1)
        assert len(day1) == 5

    def test_reasoning_in_full_pipeline(self):
        """reasoning 字段贯穿整个管道。"""
        event = GameEvent(
            type="action", timestamp={"day": 2, "hour": 9},
            actor="farmer", location="market",
            content="乔治去了市场",
            witnesses=["farmer"],
            visibility="location",
            reasoning="想确认商人的事",
        )
        self.event_log.append(event)
        self.witness_engine.process_event(event)

        farmer_beliefs = self.belief_stores["farmer"].get_active(current_day=2)
        contents = [b.content for b in farmer_beliefs]
        assert "乔治去了市场" in contents
        assert "想确认商人的事" in contents

    def test_information_asymmetry(self):
        """信息不对称：只有在场者知道发生了什么。"""
        # farmer 在 field 做了事
        event1 = GameEvent(
            type="action", timestamp={"day": 1, "hour": 10},
            actor="farmer", location="field",
            content="乔治挖到了金币",
            witnesses=["farmer"],
            visibility="location",
        )
        # bartender 在 tavern 做了事
        event2 = GameEvent(
            type="action", timestamp={"day": 1, "hour": 10},
            actor="bartender", location="tavern",
            content="盖斯偷偷藏了一封信",
            witnesses=["bartender"],
            visibility="location",
        )
        self.witness_engine.process_event(event1)
        self.witness_engine.process_event(event2)

        # 各自只知道自己的事
        farmer_beliefs = self.belief_stores["farmer"].get_active(current_day=1)
        bartender_beliefs = self.belief_stores["bartender"].get_active(current_day=1)

        farmer_contents = [b.content for b in farmer_beliefs]
        bartender_contents = [b.content for b in bartender_beliefs]

        assert "乔治挖到了金币" in farmer_contents
        assert "盖斯偷偷藏了一封信" not in farmer_contents
        assert "盖斯偷偷藏了一封信" in bartender_contents
        assert "乔治挖到了金币" not in bartender_contents
