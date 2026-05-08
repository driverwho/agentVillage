from dataclasses import dataclass


@dataclass
class GameTime:
    day: int = 1
    hour: int = 6
    minute: int = 0

    def tick(self, minutes: int = 60) -> None:
        self.minute += minutes
        while self.minute >= 60:
            self.minute -= 60
            self.hour += 1
        while self.hour >= 24:
            self.hour -= 24
            self.day += 1

    def to_dict(self) -> dict:
        return {"day": self.day, "hour": self.hour, "minute": self.minute}

    @classmethod
    def from_dict(cls, data: dict) -> "GameTime":
        return cls(day=data["day"], hour=data["hour"], minute=data["minute"])

    def __str__(self) -> str:
        return f"Day {self.day}, {self.hour:02d}:{self.minute:02d}"
