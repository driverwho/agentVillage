"""NPC 活动状态管理。

管理 NPC 的 IDLE/ACTIVE 状态转换、活动完成检查、事件中断检查。
"""

from dataclasses import dataclass
from typing import Literal

from server.models.game_time import GameTime
from server.models.npc_state import NPCState

DECISION_POINTS = [6, 12, 18, 20]

INTERRUPT_CONDITIONS = [
    ("hunger", lambda s: s.hunger < 20, "饥饿难耐"),
    ("fatigue", lambda s: s.fatigue > 90, "极度疲惫"),
    ("health", lambda s: s.health < 20, "身体虚弱"),
]

MIN_SLEEP_HOURS = 6
WAKE_HOUR = 6


@dataclass
class ActivityState:
    status: Literal["idle", "active"] = "idle"
    current_tool: str | None = None
    end_hour: int | None = None
    end_day: int | None = None
    idle_reason: str | None = None


class ActivityManager:
    """管理 NPC 活动状态转换。"""

    def check_completion(self, activity: ActivityState, game_time: GameTime) -> bool:
        """检查当前活动是否已完成（时间到达）。"""
        if activity.status != "active":
            return False
        if activity.end_day is None or activity.end_hour is None:
            return False
        current_abs = game_time.day * 24 + game_time.hour
        end_abs = activity.end_day * 24 + activity.end_hour
        return current_abs >= end_abs

    def check_interrupts(self, activity: ActivityState, npc_state: NPCState) -> str | None:
        """检查是否有中断条件触发。返回中断原因字符串，无中断返回 None。"""
        if activity.status != "active":
            return None
        for _name, condition, reason in INTERRUPT_CONDITIONS:
            if condition(npc_state):
                return reason
        return None

    def is_decision_point(self, hour: int) -> bool:
        """当前小时是否为决策点。"""
        return hour in DECISION_POINTS

    def transition_to_idle(self, activity: ActivityState, reason: str) -> None:
        """将活动状态转为 idle。"""
        activity.status = "idle"
        activity.idle_reason = reason
        activity.current_tool = None
        activity.end_hour = None
        activity.end_day = None

    def transition_to_active(
        self, activity: ActivityState, tool_name: str, duration_hours: int, game_time: GameTime
    ) -> None:
        """将活动状态转为 active，计算结束时间。"""
        end_abs_hour = game_time.hour + duration_hours
        end_day = game_time.day + end_abs_hour // 24
        end_hour = end_abs_hour % 24
        activity.status = "active"
        activity.current_tool = tool_name
        activity.end_day = end_day
        activity.end_hour = end_hour
        activity.idle_reason = None

    def calculate_sleep_duration(self, current_hour: int) -> int:
        """计算从当前小时到次日 WAKE_HOUR 的睡眠时长，最少 MIN_SLEEP_HOURS。"""
        hours_until_wake = (WAKE_HOUR - current_hour) % 24
        if hours_until_wake == 0:
            hours_until_wake = 24
        return max(MIN_SLEEP_HOURS, hours_until_wake)
