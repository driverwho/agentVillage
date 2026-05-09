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
