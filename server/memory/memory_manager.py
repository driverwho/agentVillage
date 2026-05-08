import os
from typing import List
from server.models.messages import DialogueTurn


class MemoryManager:
    def __init__(self, base_path: str, npc_id: str):
        self.dir = os.path.join(base_path, npc_id)
        os.makedirs(self.dir, exist_ok=True)
        os.makedirs(os.path.join(self.dir, "daily_summary"), exist_ok=True)
        for f in ["user.md", "agent_mem.md", "self.md"]:
            p = os.path.join(self.dir, f)
            if not os.path.exists(p):
                open(p, "w", encoding="utf-8").close()

    def _read(self, filename: str) -> str:
        p = os.path.join(self.dir, filename)
        if not os.path.exists(p):
            return ""
        with open(p, "r", encoding="utf-8") as f:
            return f.read()

    def _write(self, filename: str, content: str) -> None:
        p = os.path.join(self.dir, filename)
        with open(p, "w", encoding="utf-8") as f:
            f.write(content)

    def append_user_memory(self, text: str) -> None:
        current = self._read("user.md")
        self._write("user.md", current + "\n" + text)

    def get_user_summary(self) -> str:
        return self._read("user.md")[:500]  # 取前500字符作为摘要

    def add_dialogue(self, turn: DialogueTurn) -> None:
        current = self._read("user.md")
        self._write("user.md", current + f"\n[{turn.speaker}]: {turn.content}")
