from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
from typing import Any, Iterable

from cybercore.discovery import DiscoveryFinding
from cybercore.evidence import EvidenceAssessment
from cybercore.policy import PolicyDecision
from cybercore.risk import RiskAssessment


@dataclass(frozen=True, slots=True)
class PlannedAction:
    id: str
    subject_ref: str
    priority: int
    risk: str
    action: str
    approval: str
   