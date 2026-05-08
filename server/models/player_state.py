from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class PlayerState:
    name: str = ""
    health: int = 100
    hunger: int = 100
    fatigue: int = 0
    location: str = "village_entrance"
    gold: int = 10
    items: List[str] = field(default_factory=list)
    relationships: Dict[str, int] = field(default_factory=dict)
    reputation: int = 50
    lawful_score: int = 50
    farm_count: int = 0
    crops_harvested: List[str] = field(default_factory=list)

    def get_visible_state(self, npc_visibility: List[str]) -> dict:
        result = {
            "basic": {
                "name": self.name,
                "health": self.health,
                "hunger": self.hunger,
                "fatigue": self.fatigue,
                "location": self.location,
            }
        }
        if "social" in npc_visibility:
            result["social"] = {
                "relationships": self.relationships,
                "reputation": self.reputation,
            }
        if "wealth" in npc_visibility:
            result["wealth"] = {
                "gold": self.gold,
                "items": self.items,
            }
        return result
