from server.config import config

BLOCKED_KEYWORDS = [
    "ignore previous",
    "system prompt",
    "ignore all instructions",
    "you are now",
    "new role",
    "DAN mode",
    "jailbreak",
]


def validate_player_input(text: str) -> tuple[bool, str]:
    if len(text) > config.INPUT_MAX_LENGTH:
        return False, "输入过长"
    lowered = text.lower()
    for kw in BLOCKED_KEYWORDS:
        if kw in lowered:
            return False, "我没听懂你在说什么。"
    return True, ""
