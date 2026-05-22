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
        return self._read("user.md")[:500]

    # ---- memory seeding ----

    def seed_if_empty(self, background: dict) -> bool:
        """首次进入时用 yaml 背景种子记忆文件。

        幂等：如果 self.md 非空则不覆盖。返回 True 表示已种子。
        """
        if self._read("self.md").strip():
            return False

        name = background.get("name", "")
        habits = background.get("daily_habits", "")
        motivation = background.get("core_motivation", "")
        secret = background.get("secret", "")
        speaking = background.get("speaking_style", "")
        biography = background.get("biography", "")
        quirks = background.get("quirks", [])

        # self.md: 叙事传记
        quirks_text = "\n".join(f"- {q}" for q in quirks) if quirks else ""
        parts = [
            f"# {name} 的自我认知",
            "",
            f"## 日常习惯",
            habits,
            "",
            f"## 核心动机",
            motivation,
            "",
            f"## 说话风格",
            speaking,
        ]
        if quirks_text:
            parts.extend(["", "## 性格癖好", quirks_text])
        parts.extend([
            "",
            f"## 内心秘密",
            secret,
            "（这是你心底最深处的秘密，不会轻易告诉任何人）",
            "",
            f"## 身世",
            biography,
        ])
        self._write("self.md", "\n".join(parts))

        # user.md: 玩家印象模板
        self._write("user.md", (
            "# 关于玩家的印象\n\n"
            "## 第一次见面\n（尚未见面）\n\n"
            "## 信任等级\n0（陌生人）\n\n"
            "## 对话记录\n\n"
        ))

        # agent_mem.md: 对其他 NPC 的关系
        relationships = background.get("relationships", {})
        if relationships:
            rel_lines = ["# 与其他村民的关系\n"]
            for other_id, rel in relationships.items():
                rel_lines.append(f"## {other_id}")
                if isinstance(rel, dict):
                    rel_lines.append(f"态度：{rel.get('attitude', '暂无')}")
                    rel_lines.append(f"信任等级：{rel.get('trust_level', 0)}/10")
                    history = rel.get("shared_history", "")
                    if history:
                        rel_lines.append(f"共同经历：{history}")
                    nature = rel.get("nature", "")
                    if nature:
                        rel_lines.append(f"关系性质：{nature}")
                rel_lines.append("")
            self._write("agent_mem.md", "\n".join(rel_lines))
        else:
            self._write("agent_mem.md", "# 与其他村民的关系\n\n（暂无）\n")

        return True

    def add_dialogue(self, turn: DialogueTurn) -> None:
        current = self._read("user.md")
        self._write("user.md", current + f"\n[{turn.speaker}]: {turn.content}")
