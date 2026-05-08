from dataclasses import dataclass
from typing import Optional, List


@dataclass
class DialogueTurn:
    speaker: str
    content: str
    timestamp: Optional[str] = None
    options: Optional[List[str]] = None
