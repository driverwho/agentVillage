import os
import tempfile
from server.llm.context_audit import ContextAudit


class TestContextAudit:
    def test_format_audit_entry(self):
        layers = {
            "L0": {"tokens": 320, "truncated": False},
            "L1": {"tokens": 45, "truncated": False},
            "L2": {"tokens": 38, "truncated": False},
            "L3": {"tokens": 52, "truncated": False},
            "L4": {"tokens": 180, "truncated": False},
            "L5": {"tokens": 400, "truncated": False},
        }
        entry = ContextAudit.format_entry(
            "farmer", layers,
            total_tokens=1035, model_limit=4096, compressed=False
        )
        assert "farmer" in entry
        assert "1035 / 4096" in entry
        assert "L0" in entry
        assert all(f"{v['tokens']}" in entry for v in layers.values())

    def test_format_with_truncation(self):
        layers = {
            "L0": {"tokens": 320, "truncated": False},
            "L4": {"tokens": 800, "truncated": True},
            "L5": {"tokens": 100, "truncated": True},
        }
        entry = ContextAudit.format_entry(
            "test", layers,
            total_tokens=1220, model_limit=4096, compressed=False
        )
        assert "截断" in entry

    def test_format_with_compression(self):
        layers = {
            "L0": {"tokens": 100, "truncated": False},
            "L5": {"tokens": 300, "truncated": False},
        }
        entry = ContextAudit.format_entry(
            "test", layers,
            total_tokens=400, model_limit=4096, compressed=True
        )
        assert "压缩" in entry

    def test_format_tired_status(self):
        layers = {"L0": {"tokens": 100, "truncated": False}}
        entry = ContextAudit.format_entry(
            "test", layers,
            total_tokens=100, model_limit=4096, budget_status="tired"
        )
        assert "tired" in entry

    def test_log_path(self):
        path = ContextAudit.log_path("farmer")
        assert path.startswith("logs/context/farmer/")
        assert path.endswith(".md")

    def test_write_creates_file(self):
        entry = "=== 测试审计日志 ==="
        with tempfile.TemporaryDirectory() as tmpdir:
            # Monkey-patch 路径
            original_log_path = ContextAudit.log_path
            import datetime
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            ContextAudit.log_path = staticmethod(lambda npc_id: f"{tmpdir}/{npc_id}.md")
            try:
                ContextAudit.write("test_npc", entry)
                assert os.path.exists(f"{tmpdir}/test_npc.md")
                with open(f"{tmpdir}/test_npc.md", "r", encoding="utf-8") as f:
                    assert f.read() == entry
            finally:
                ContextAudit.log_path = original_log_path
