from server.config import config


class EndingChecker:
    @staticmethod
    def check_farmer_joy(player_state) -> bool:
        affinity = player_state.relationships.get("farmer", 0)
        crops = len(set(player_state.crops_harvested))
        return (
            affinity >= config.FARMER_JOY_AFFINITY
            and crops >= config.FARMER_JOY_CROP_TYPES
            and player_state.farm_count >= config.FARMER_JOY_FARM_COUNT
        )

    @classmethod
    def check_all(cls, player_state) -> str | None:
        if cls.check_farmer_joy(player_state):
            return "farmer_joy"
        if player_state.health <= 0:
            return "death"
        return None
