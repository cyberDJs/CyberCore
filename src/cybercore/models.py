from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CheckState(StrEnum):
    OK = "ok"
    WARN = "warn"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class CheckResult:
    name: str
    state: CheckState
    detail: str

    @property
    def successful(self) -> bool:
        return self.state is not CheckState.ERROR
