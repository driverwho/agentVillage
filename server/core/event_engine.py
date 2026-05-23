from __future__ import annotations
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List
from server.models.game_time import GameTime


@dataclass
class EventDef:
    id: str
    name: str
    category: str
    probability: float
    duration_hours: int
    conditions: Dict[str, Any]
    description: str


@dataclass
class ActiveEvent:
    id: str
    name: str
    description: str
    started_day: int
    started_hour: int
    expires_day: int
    expires_hour: int


@dataclass
class EventState:
    active_events: List[ActiveEvent] = field(default_factory=list)
    cooldowns: Dict[str, int] = field(default_factory=dict)


_WEATHER_IDS = {"heavy_rain", "fog", "scorching_heat", "strong_wind"}


class EventEngine:
    def __init__(self, event_defs: List[EventDef], state: EventState):
        self.event_defs = event_defs
        self.state = state

    def tick(self, game_time: GameTime) -> List[ActiveEvent]:
        self._expire_events(game_time)
        self._try_generate(game_time)
        return list(self.state.active_events)

    def _expire_events(self, game_time: GameTime) -> None:
        self.state.active_events = [
            e for e in self.state.active_events
            if not self._is_expired(e, game_time)
        ]

    def _is_expired(self, event: ActiveEvent, game_time: GameTime) -> bool:
        if game_time.day > event.expires_day:
            return True
        if game_time.day == event.expires_day and game_time.hour >= event.expires_hour:
            return True
        return False

    def _try_generate(self, game_time: GameTime) -> None:
        active_ids = {e.id for e in self.state.active_events}
        for event_def in self.event_defs:
            if event_def.id in active_ids:
                continue
            if not self._check_conditions(event_def, game_time):
                continue
            if random.random() < event_def.probability:
                self._activate(event_def, game_time)
                active_ids.add(event_def.id)

    def _check_conditions(self, event_def: EventDef, game_time: GameTime) -> bool:
        cond = event_def.conditions
        if game_time.day < cond.get("min_day", 1):
            return False
        if event_def.id in self.state.cooldowns:
            if game_time.day < self.state.cooldowns[event_def.id]:
                return False
        hour_range = cond.get("hour_range")
        if hour_range and not (hour_range[0] <= game_time.hour < hour_range[1]):
            return False
        max_active = cond.get("max_active_events", 3)
        if len(self.state.active_events) >= max_active:
            return False
        required = cond.get("required_event")
        if required:
            active_ids = {e.id for e in self.state.active_events}
            if required not in active_ids:
                return False
        return True

    def _activate(self, event_def: EventDef, game_time: GameTime) -> None:
        expires_hour = game_time.hour + event_def.duration_hours
        expires_day = game_time.day
        while expires_hour >= 24:
            expires_hour -= 24
            expires_day += 1
        active = ActiveEvent(
            id=event_def.id, name=event_def.name, description=event_def.description,
            started_day=game_time.day, started_hour=game_time.hour,
            expires_day=expires_day, expires_hour=expires_hour,
        )
        self.state.active_events.append(active)
        cooldown_days = event_def.conditions.get("cooldown_days", 0)
        if cooldown_days:
            self.state.cooldowns[event_def.id] = game_time.day + cooldown_days

    def get_current_weather(self) -> str:
        for event in self.state.active_events:
            if event.id in _WEATHER_IDS:
                return event.name
        return "晴"

    def get_world_events_text(self) -> str:
        non_weather = [e for e in self.state.active_events if e.id not in _WEATHER_IDS]
        if not non_weather:
            return "今日无事"
        return "；".join(e.description for e in non_weather)


def load_event_defs(events_dir: str) -> List[EventDef]:
    """从指定目录加载所有事件 YAML 定义。"""
    import yaml
    from pathlib import Path

    defs = []
    events_path = Path(events_dir)
    if not events_path.exists():
        return defs
    for yaml_file in events_path.glob("*.yaml"):
        with open(yaml_file, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        category = data.get("category", "unknown")
        for item in data.get("events", []):
            defs.append(EventDef(
                id=item["id"],
                name=item["name"],
                category=category,
                probability=item["probability"],
                duration_hours=item["duration_hours"],
                conditions=item.get("conditions", {}),
                description=item["description"],
            ))
    return defs
