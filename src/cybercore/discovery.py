from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from typing import Any, Callable, Iterable

from cybercore.registry import Registry, RegistryRecord


@dataclass(frozen=True, slots=True)
class DiscoveryFinding:
    id: str
    detector: str
    severity: str
    subject_ref: str | None
    summary: str
    evidence: tuple[str, ...]
    proposed_action