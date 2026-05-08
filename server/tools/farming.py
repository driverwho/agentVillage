from server.tools.base_tool import Tool
from server.config import config


class FarmingTool(Tool):
    name = "farming"

    def check_preconditions(self, player_state, npc_state=None) -> tuple[bool, str]:
        if player_state.fatigue >= config.FARMING_FATIGUE_MAX:
            return False, "你太累了，无法耕作。"
        if player_state.hunger <= config.FARMING_HUNGER_MIN:
            return False, "你太饿了，先吃点东西吧。"
        return True, ""

    def execute(self, player_state, npc_state=None) -> dict:
        player_state.fatigue += config.FARMING_FATIGUE_COST
        player_state.farm_count += 1
        if npc_state:
            player_state.relationships["farmer"] = (
                player_state.relationships.get("farmer", 0) + 5
            )
        return {
            "success": True,
            "message": "你辛勤地耕作了一小时，土地变得更加肥沃。",
            "player_state_changes": {
                "fatigue": player_state.fatigue,
                "farm_count": player_state.farm_count,
            },
        }
