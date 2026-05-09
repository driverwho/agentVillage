import os
from dataclasses import dataclass, field
from typing import Dict


@dataclass
class GameConfig:
    # --- 游戏机制 ---
    INTERACTIONS_PER_HOUR: int = 3
    INTERACTION_COOLDOWN_MINUTES: int = 10
    NPC_STATE_DECAY_HUNGER: int = 5
    NPC_STATE_DECAY_FATIGUE: int = 5
    TOKEN_WARNING_THRESHOLD: float = 0.8
    TOKEN_HARD_LIMIT: float = 1.0
    LLM_MAX_CONCURRENT: int = 3
    INPUT_MAX_LENGTH: int = 500
    FARMING_FATIGUE_COST: int = 20
    FARMING_HUNGER_MIN: int = 20
    FARMING_FATIGUE_MAX: int = 80
    FARMER_JOY_AFFINITY: int = 80
    FARMER_JOY_CROP_TYPES: int = 2
    FARMER_JOY_FARM_COUNT: int = 5

    # --- 上下文管理 ---
    LLM_CONTEXT_LIMIT: int = 4096
    LLM_OUTPUT_RESERVE: int = 500
    CONTEXT_COMPRESS_THRESHOLD: int = 10
    CONTEXT_TIRED_THRESHOLD: int = 200
    CONTEXT_DECAY_RATE: float = 0.05

    # 每层配额比例（总和应为 1.0）
    CONTEXT_LAYER_QUOTAS: Dict[int, float] = field(default_factory=lambda: {
        0: 0.30, 1: 0.05, 2: 0.05, 3: 0.10, 4: 0.25, 5: 0.25,
    })

    # 注入关键词黑名单
    INJECTION_BLACKLIST: tuple = (
        "ignore previous", "ignore all previous",
        "system prompt", "system:",
    )

    def layer_quota(self, layer: int) -> int:
        """返回指定层的 token 配额上限"""
        ratio = self.CONTEXT_LAYER_QUOTAS.get(layer, 0)
        return int(self.LLM_CONTEXT_LIMIT * ratio)

    @classmethod
    def from_env(cls) -> "GameConfig":
        """从环境变量覆盖默认值"""
        return cls(
            LLM_CONTEXT_LIMIT=int(os.getenv("LLM_CONTEXT_LIMIT", "4096")),
            LLM_OUTPUT_RESERVE=int(os.getenv("LLM_OUTPUT_RESERVE", "500")),
        )

    @classmethod
    def from_yaml(cls, path: str = "config.yaml") -> "GameConfig":
        """从 YAML 配置文件加载"""
        import yaml

        cfg = cls()
        if not os.path.exists(path):
            return cfg

        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}

        # 映射 YAML key → dataclass field
        key_map = {
            # 游戏机制
            "interactions_per_hour": "INTERACTIONS_PER_HOUR",
            "interaction_cooldown_minutes": "INTERACTION_COOLDOWN_MINUTES",
            "npc_state_decay_hunger": "NPC_STATE_DECAY_HUNGER",
            "npc_state_decay_fatigue": "NPC_STATE_DECAY_FATIGUE",
            "token_warning_threshold": "TOKEN_WARNING_THRESHOLD",
            "token_hard_limit": "TOKEN_HARD_LIMIT",
            "llm_max_concurrent": "LLM_MAX_CONCURRENT",
            "input_max_length": "INPUT_MAX_LENGTH",
            "farming_fatigue_cost": "FARMING_FATIGUE_COST",
            "farming_hunger_min": "FARMING_HUNGER_MIN",
            "farming_fatigue_max": "FARMING_FATIGUE_MAX",
            "farmer_joy_affinity": "FARMER_JOY_AFFINITY",
            "farmer_joy_crop_types": "FARMER_JOY_CROP_TYPES",
            "farmer_joy_farm_count": "FARMER_JOY_FARM_COUNT",
            # 上下文管理
            "llm_context_limit": "LLM_CONTEXT_LIMIT",
            "llm_output_reserve": "LLM_OUTPUT_RESERVE",
            "context_compress_threshold": "CONTEXT_COMPRESS_THRESHOLD",
            "context_tired_threshold": "CONTEXT_TIRED_THRESHOLD",
            "context_decay_rate": "CONTEXT_DECAY_RATE",
        }

        section = data.get("context", {})
        for yaml_key, attr_name in key_map.items():
            if yaml_key in section:
                setattr(cfg, attr_name, section[yaml_key])

        # Layer quotas: dict[int, float]
        if "layer_quotas" in section:
            quotas = {}
            for k, v in section["layer_quotas"].items():
                quotas[int(k)] = float(v)
            cfg.CONTEXT_LAYER_QUOTAS = quotas

        # Injection blacklist
        if "injection_blacklist" in section:
            cfg.INJECTION_BLACKLIST = tuple(section["injection_blacklist"])

        # 也支持环境变量覆盖
        env_config = cls.from_env()
        if env_config.LLM_CONTEXT_LIMIT != 4096:
            cfg.LLM_CONTEXT_LIMIT = env_config.LLM_CONTEXT_LIMIT
        if env_config.LLM_OUTPUT_RESERVE != 500:
            cfg.LLM_OUTPUT_RESERVE = env_config.LLM_OUTPUT_RESERVE

        return cfg


config = GameConfig()
