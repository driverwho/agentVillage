import os
from dataclasses import dataclass, field
from typing import List, Dict, Union


@dataclass
class ContextConfig:
    model_limit: int = 4096
    output_reserve: int = 500
    compress_threshold: int = 10
    tired_threshold: int = 200
    decay_rate: float = 0.05

    @classmethod
    def from_env(cls) -> "ContextConfig":
        return cls(
            model_limit=int(os.getenv("LLM_CONTEXT_LIMIT", "4096")),
            output_reserve=int(os.getenv("LLM_OUTPUT_RESERVE", "500")),
        )

    def quota(self, layer: int) -> int:
        ratios = {0: 0.30, 1: 0.05, 2: 0.05, 3: 0.10, 4: 0.25, 5: 0.25}
        return int(self.model_limit * ratios.get(layer, 0))


@dataclass
class BuildParams:
    identity: dict
    npc_state: any
    world_state: dict
    interlocutor: dict
    memory_files: dict
    dialogue_history: List[dict]
    current_input: str


@dataclass
class LayerResult:
    content: Union[str, List[dict]]
    tokens: int
    truncated: bool = False
    errors: List[str] = field(default_factory=list)


@dataclass
class BuildResult:
    messages: List[dict]
    audit: dict
    budget_status: str = "normal"
