from dataclasses import dataclass
from typing import Dict


@dataclass
class NPCState:
    health: int = 100
    hunger: int = 100
    fatigue: int = 0
    mood: int = 50

    def describe(self) -> Dict[str, str]:
        return {
            "health": self._describe_value(self.health, [
                (0, 20, "你感觉身体极度虚弱"),
                (21, 40, "你身体有些不适"),
                (41, 60, "你身体状况一般"),
                (61, 80, "你感觉身体不错"),
                (81, 100, "你感觉精力充沛，非常健康"),
            ]),
            "hunger": self._describe_value(self.hunger, [
                (0, 20, "你饿得头晕眼花"),
                (21, 40, "你的肚子在咕咕叫"),
                (41, 60, "你不太饿也不太饱"),
                (61, 80, "你吃得还算饱"),
                (81, 100, "你吃得很饱很满足"),
            ]),
            "fatigue": self._describe_value(self.fatigue, [
                (0, 20, "你精神抖擞"),
                (21, 40, "你精神还不错"),
                (41, 60, "你有些累了"),
                (61, 80, "你感到很疲倦"),
                (81, 100, "你疲惫到几乎无法站立"),
            ]),
            "mood": self._describe_value(self.mood, [
                (0, 20, "你的心情非常低落"),
                (21, 40, "你心情不太好"),
                (41, 60, "你心情一般"),
                (61, 80, "你心情不错"),
                (81, 100, "你心情非常愉快"),
            ]),
        }

    def _describe_value(self, value: int, ranges) -> str:
        for lo, hi, desc in ranges:
            if lo <= value <= hi:
                return desc
        return ranges[0][2] if value < ranges[0][0] else ranges[-1][2]
