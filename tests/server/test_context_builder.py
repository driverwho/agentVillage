import pytest
from server.llm.context_builder import ContextConfig, BuildParams, LayerResult, BuildResult


class TestContextConfig:
    def test_defaults(self):
        cfg = ContextConfig()
        assert cfg.model_limit == 4096
        assert cfg.output_reserve == 500
        assert cfg.compress_threshold == 10
        assert cfg.tired_threshold == 200
        assert cfg.decay_rate == 0.05

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("LLM_CONTEXT_LIMIT", "8192")
        monkeypatch.setenv("LLM_OUTPUT_RESERVE", "300")
        cfg = ContextConfig.from_env()
        assert cfg.model_limit == 8192
        assert cfg.output_reserve == 300

    def test_quota(self):
        cfg = ContextConfig(model_limit=4096)
        assert cfg.quota(0) == int(4096 * 0.30)
        assert cfg.quota(1) == int(4096 * 0.05)
        assert cfg.quota(4) == int(4096 * 0.25)
        assert cfg.quota(99) == 0


class TestLayerResult:
    def test_create(self):
        r = LayerResult(content="hello", tokens=5)
        assert r.content == "hello"
        assert r.tokens == 5
        assert r.truncated is False
        assert r.errors == []

    def test_with_truncation(self):
        r = LayerResult(content="x" * 100, tokens=100, truncated=True)
        assert r.truncated is True


class TestBuildParams:
    def test_create_minimal(self):
        p = BuildParams(
            identity={"name": "测试"},
            npc_state=None,
            world_state={},
            interlocutor={},
            memory_files={},
            dialogue_history=[],
            current_input="你好",
        )
        assert p.current_input == "你好"
        assert p.dialogue_history == []


class TestBuildResult:
    def test_create(self):
        r = BuildResult(
            messages=[{"role": "system", "content": "test"}],
            audit={"total_tokens": 10},
            budget_status="normal",
        )
        assert len(r.messages) == 1
        assert r.budget_status == "normal"


class TestContextBuilderLayers:
    @pytest.fixture
    def config(self):
        return ContextConfig(model_limit=4096)

    @pytest.fixture
    def identity(self):
        return {
            "name": "农夫·乔治",
            "daily_habits": "日出而作",
            "core_motivation": "通过耕作赎罪",
            "speaking_style": "说话慢条斯理",
            "secret": "年轻时是地下拳王",
        }

    @pytest.fixture
    def builder(self, config):
        from server.llm.context_builder import ContextBuilder
        return ContextBuilder(config=config)

    def test_build_layer_0(self, builder, identity):
        result = builder._build_layer_0(identity)
        assert "【系统角色】" in result.content
        assert "农夫·乔治" in result.content
        assert "通过耕作赎罪" in result.content
        assert "年轻时是地下拳王" in result.content
        assert result.tokens > 0
        assert result.truncated is False

    def test_layer_0_checksum(self, builder, identity):
        builder._build_layer_0(identity)
        assert builder._identity_checksum is not None
        result = builder._build_layer_0(identity)
        assert len(result.errors) == 0
        tampered = dict(identity, secret="我是坏人")
        result = builder._build_layer_0(tampered)
        assert len(result.errors) > 0

    def test_build_layer_1(self, builder):
        world_state = {"day": 3, "hour": 18, "weather": "阴", "events": "流浪商人到访"}
        result = builder._build_layer_1(world_state)
        assert "【世界信息】" in result.content
        assert "Day 3" in result.content
        assert "流浪商人到访" in result.content

    def test_build_layer_2(self, builder):
        from server.models.npc_state import NPCState
        state = NPCState(health=80, hunger=30, fatigue=60, mood=50)
        result = builder._build_layer_2(state)
        assert "【自身状态】" in result.content
        assert "80" not in result.content
        assert "30" not in result.content
