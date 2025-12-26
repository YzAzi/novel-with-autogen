from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


@dataclass
class AgentResult:
    data: Dict[str, Any]
    logs: List[Dict[str, Any]]


class LLMNotAvailable(RuntimeError):
    pass

