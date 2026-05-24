from __future__ import annotations
import uuid
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class GameEvent:
    type: str
    timestamp: Dict[str, int]
    actor: str
    location: str
    content: str
    witnesses: List[str]
    visibility: str
    reasoning: Optional[str] = None
    id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "id": self.id,
            "type": self.type,
            "timestamp": self.timestamp,
            "actor": self.actor,
            "location": self.location,
            "content": self.content,
            "witnesses": self.witnesses,
            "visibility": self.visibility,
        }
        if self.reasoning is not None:
            d["reasoning"] = self.reasoning
        return d

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> GameEvent:
        return cls(
            id=data["id"],
            type=data["type"],
            timestamp=data["timestamp"],
            actor=data["actor"],
            location=data["location"],
            content=data["content"],
            witnesses=data["witnesses"],
            visibility=data["visibility"],
            reasoning=data.get("reasoning"),
        )
