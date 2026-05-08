from dataclasses import dataclass
from enum import Enum

class BudgetStatus(Enum):
    NORMAL = "normal"
    WARNING = "warning"
    EXHAUSTED = "exhausted"

@dataclass
class TokenBudget:
    daily_limit: int = 5000
    used: int = 0
    warning_threshold: float = 0.8

    def consume(self, tokens: int) -> bool:
        if self.status == BudgetStatus.EXHAUSTED:
            return False
        self.used += tokens
        return True

    @property
    def status(self) -> BudgetStatus:
        ratio = self.used / self.daily_limit
        if ratio >= 1.0:
            return BudgetStatus.EXHAUSTED
        if ratio >= self.warning_threshold:
            return BudgetStatus.WARNING
        return BudgetStatus.NORMAL

    def reset(self) -> None:
        self.used = 0
