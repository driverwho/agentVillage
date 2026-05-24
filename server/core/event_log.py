from __future__ import annotations
import json
import os
from typing import Dict, List, Optional
from server.models.event import GameEvent


class EventLog:
    """结构化事件持久化。

    按天分文件存储：{base_path}/events_day{N}.json
    """

    def __init__(self, base_path: str = "data/users/default/events"):
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)
        self._cache: Dict[int, List[GameEvent]] = {}

    def _day_file(self, day: int) -> str:
        return os.path.join(self.base_path, f"events_day{day}.json")

    def _load_day(self, day: int) -> List[GameEvent]:
        if day in self._cache:
            return self._cache[day]
        path = self._day_file(day)
        if not os.path.exists(path):
            self._cache[day] = []
            return self._cache[day]
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        events = [GameEvent.from_dict(d) for d in data]
        self._cache[day] = events
        return events

    def _save_day(self, day: int) -> None:
        events = self._cache.get(day, [])
        path = self._day_file(day)
        with open(path, "w", encoding="utf-8") as f:
            json.dump([e.to_dict() for e in events], f, ensure_ascii=False, indent=2)

    def append(self, event: GameEvent) -> None:
        day = event.timestamp.get("day", 1)
        events = self._load_day(day)
        events.append(event)
        self._save_day(day)

    def get_by_id(self, event_id: str) -> Optional[GameEvent]:
        for day_events in self._cache.values():
            for e in day_events:
                if e.id == event_id:
                    return e
        for filename in sorted(os.listdir(self.base_path)):
            if not filename.startswith("events_day"):
                continue
            day_num = int(filename.replace("events_day", "").replace(".json", ""))
            if day_num in self._cache:
                continue
            events = self._load_day(day_num)
            for e in events:
                if e.id == event_id:
                    return e
        return None

    def query(
        self,
        day: Optional[int] = None,
        actor: Optional[str] = None,
        location: Optional[str] = None,
        witness: Optional[str] = None,
    ) -> List[GameEvent]:
        if day is not None:
            candidates = self._load_day(day)
        else:
            candidates = []
            for filename in sorted(os.listdir(self.base_path)):
                if not filename.startswith("events_day"):
                    continue
                day_num = int(filename.replace("events_day", "").replace(".json", ""))
                candidates.extend(self._load_day(day_num))

        results = candidates
        if actor is not None:
            results = [e for e in results if e.actor == actor]
        if location is not None:
            results = [e for e in results if e.location == location]
        if witness is not None:
            results = [e for e in results if witness in e.witnesses]
        return results

    def get_recent(self, limit: int = 10) -> List[GameEvent]:
        all_events: List[GameEvent] = []
        filenames = sorted(os.listdir(self.base_path), reverse=True)
        for filename in filenames:
            if not filename.startswith("events_day"):
                continue
            day_num = int(filename.replace("events_day", "").replace(".json", ""))
            day_events = self._load_day(day_num)
            all_events.extend(reversed(day_events))
            if len(all_events) >= limit:
                break
        return all_events[:limit]
