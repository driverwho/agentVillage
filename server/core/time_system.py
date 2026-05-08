from server.models.game_time import GameTime


class TimeSystem:
    def __init__(self):
        self.game_time = GameTime(day=1, hour=6, minute=0)
        self.is_paused = True

    def tick(self, minutes: int = 60) -> bool:
        if self.is_paused:
            return False
        old_hour = self.game_time.hour
        self.game_time.tick(minutes)
        if self.game_time.hour != old_hour:
            return True
        return False

    def toggle_pause(self) -> None:
        self.is_paused = not self.is_paused
