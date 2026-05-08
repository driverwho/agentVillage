from dataclasses import dataclass


@dataclass
class GameConfig:
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


config = GameConfig()
