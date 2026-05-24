from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List

CONFIDENCE_LEVELS = ("high", "medium", "low")
DECAY_DAYS = {"low": 3, "medium": 7, "high": None}


@dataclass
class Belief:
    content: str
    source: str
    confidence: str
    acquired_at: Dict[str, int]
    about: List[str]
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def is_expired(self, current_day: int) -> bool:
        decay = DECAY_DAYS.get(self.confidence)
        if decay is None:
            return False
        age = current_day - self.acquired_at.get("day", current_day)
        return age > decay

    def propagate(self, teller_id: str, new_content: str) -> Belief:
        idx = CONFIDENCE_LEVELS.index(self.confidence)
        new_confidence = CONFIDENCE_LEVELS[min(idx + 1, len(CONFIDENCE_LEVELS) - 1)]
        return Belief(
            content=new_content,
            source=f"told_by:{teller_id}",
            confidence=new_confidence,
            acquired_at=dict(self.acquired_at),
            about=list(self.about),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "source": self.source,
            "confidence": self.confidence,
            "acquired_at": self.acquired_at,
            "about": self.about,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> Belief:
        return cls(
            id=data["id"],
            content=data["content"],
            source=data["source"],
            confidence=data["confidence"],
            acquired_at=data["acquired_at"],
            about=data["about"],
        )
