from __future__ import annotations
from collections import defaultdict
from typing import Dict, List, Set


class LocationRegistry:
    def __init__(self, initial: Dict[str, List[str]] | None = None):
        self._map: Dict[str, Set[str]] = defaultdict(set)
        if initial:
            for loc, npcs in initial.items():
                self._map[loc] = set(npcs)

    def move(self, npc_id: str, from_loc: str | None, to_loc: str) -> None:
        if from_loc:
            self._map[from_loc].discard(npc_id)
        self._map[to_loc].add(npc_id)

    def get_npcs_at(self, location: str) -> Set[str]:
        return self._map[location].copy()

    def get_location(self, npc_id: str) -> str | None:
        for loc, npcs in self._map.items():
            if npc_id in npcs:
                return loc
        return None

    def to_dict(self) -> Dict[str, List[str]]:
        return {loc: sorted(npcs) for loc, npcs in self._map.items() if npcs}
