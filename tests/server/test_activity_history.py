import pytest
from server.agents.base_agent import NPCAgent
from server.llm.token_budget import TokenBudget


class TestActivityLog:
    def test_npc_has_activity_log(self):
        agent = NPCAgent(
            agent_id="farmer",
            background={"name": "农夫", "id": "farmer"},
            memory_base="data/users/test_history/memory",
            budget=TokenBudget(daily_limit=5000),
        )
        assert hasattr(agent, "activity_log")
        assert agent.activity_log == []

    def test_activity_log_append(self):
        agent = NPCAgent(
            agent_id="farmer",
            background={"name": "农夫", "id": "farmer"},
            memory_base="data/users/test_history/memory",
            budget=TokenBudget(daily_limit=5000),
        )
        agent.activity_log.append("8:00 farm — 辛勤耕作了一阵")
        agent.activity_log.append("12:00 eat — 吃了一顿饭")
        assert len(agent.activity_log) == 2
        assert "farm" in agent.activity_log[0]


class TestDailySummary:
    @pytest.fixture
    def memory(self, tmp_path):
        from server.memory.memory_manager import MemoryManager
        return MemoryManager(str(tmp_path), "farmer")

    def test_write_and_read_daily_summary(self, memory):
        memory.write_daily_summary(1, "今天在田里干了一天活。")
        result = memory.read_daily_summary(1)
        assert "田里干了一天活" in result

    def test_read_nonexistent_summary_returns_empty(self, memory):
        result = memory.read_daily_summary(99)
        assert result == ""

    def test_read_recent_summaries(self, memory):
        memory.write_daily_summary(1, "Day1 内容")
        memory.write_daily_summary(2, "Day2 内容")
        memory.write_daily_summary(3, "Day3 内容")
        result = memory.read_recent_summaries(current_day=3, count=2)
        assert "Day2 内容" in result
        assert "Day1 内容" in result
        assert "Day3" not in result


class TestAutonomousContextHistory:
    def test_context_includes_today_log(self):
        from server.tools.setup import build_autonomous_context
        from server.core.time_system import GameTime

        agent = NPCAgent(
            agent_id="farmer",
            background={"name": "农夫", "id": "farmer", "default_location": "field"},
            memory_base="data/users/test_history/memory",
            budget=TokenBudget(daily_limit=5000),
        )
        agent.activity_log = ["8:00 farm — 辛勤耕作了一阵", "12:00 eat — 吃了一顿饭"]

        game_time = GameTime(day=1, hour=14)
        result = build_autonomous_context(agent, game_time)
        assert "【今日已完成】" in result
        assert "farm" in result
        assert "eat" in result

    def test_context_includes_recent_summaries(self, tmp_path):
        from server.tools.setup import build_autonomous_context
        from server.core.time_system import GameTime

        agent = NPCAgent(
            agent_id="farmer",
            background={"name": "农夫", "id": "farmer", "default_location": "field"},
            memory_base=str(tmp_path),
            budget=TokenBudget(daily_limit=5000),
        )
        agent.memory.write_daily_summary(1, "在田里劳作了大半天")
        agent.memory.write_daily_summary(2, "去了市场买种子")
        agent.activity_log = []

        game_time = GameTime(day=3, hour=8)
        result = build_autonomous_context(agent, game_time)
        assert "【近日回顾】" in result
        assert "田里劳作" in result
        assert "市场买种子" in result

    def test_context_empty_log_shows_hint(self):
        from server.tools.setup import build_autonomous_context
        from server.core.time_system import GameTime

        agent = NPCAgent(
            agent_id="farmer",
            background={"name": "农夫", "id": "farmer", "default_location": "field"},
            memory_base="data/users/test_history/memory",
            budget=TokenBudget(daily_limit=5000),
        )
        agent.activity_log = []

        game_time = GameTime(day=1, hour=6)
        result = build_autonomous_context(agent, game_time)
        assert "刚开始新的一天" in result


class TestDreamMechanism:
    def test_dream_prompt_construction(self):
        from server.core.orchestrator import _build_dream_prompt

        activity_log = ["8:00 farm — 辛勤耕作了一阵", "12:00 eat — 吃了一顿饭", "14:00 gossip — 向bartender说了八卦"]
        npc_name = "农夫·乔治"
        today_events = "流浪商人到访"

        prompt = _build_dream_prompt(npc_name, activity_log, today_events)
        assert "农夫·乔治" in prompt
        assert "farm" in prompt
        assert "eat" in prompt
        assert "流浪商人到访" in prompt
        assert "bartender" in prompt
        assert "第一人称" in prompt

    def test_dream_extracts_social_interactions(self):
        from server.core.orchestrator import _build_dream_prompt

        activity_log = ["8:00 farm — 干活", "10:00 gossip — 向bartender说了八卦", "14:00 trade — 与beggar交易"]
        prompt = _build_dream_prompt("测试NPC", activity_log, "无")
        assert "bartender" in prompt or "beggar" in prompt

    def test_dream_no_social(self):
        from server.core.orchestrator import _build_dream_prompt

        activity_log = ["8:00 farm — 干活", "12:00 eat — 吃饭"]
        prompt = _build_dream_prompt("测试NPC", activity_log, "今日无事")
        assert "没有与人交流" in prompt
