"""Pure, fail-closed evaluation of externally verified exact-head CI observations.

No GitHub I/O, authentication, review authority or merge permission is provided.
The trusted adapter must bind each observation to the provider's actual commit.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable


DEFAULT_REQUIRED_CHECKS = frozenset(
    {
        "CI / quality",
        "CI / package",
        "CI / tests (python 3.11)",
        "CI / tests (python 3.12)",
        "CI / tests (python 3.13)",
        "CI / tests (python 3.14)",
        "CodeQL",
        "Action Kernel real CyberHIVE contract",
    }
)


@dataclass(frozen=True)
class CheckObservation:
    name: str
    commit_sha: str
    status: str
    conclusion: str | None


@dataclass(frozen=True)
class GateVerdict:
    passed: bool
    reason: str
    missing: tuple[str, ...] = ()


def evaluate_ci_evidence(
    expected_sha: str,
    observations: Iterable[CheckObservation],
    *,
    required_checks: frozenset[str] = DEFAULT_REQUIRED_CHECKS,
) -> GateVerdict:
    """Evaluate a snapshot, never authorize merges or bypass branch protection."""
    if re.fullmatch(r"[0-9a-f]{40}", expected_sha) is None:
        return GateVerdict(False, "INVALID_EXPECTED_SHA")
    if not required_checks or any(not name.strip() for name in required_checks):
        return GateVerdict(False, "INVALID_REQUIRED_CHECKS")

    seen: dict[str, CheckObservation] = {}
    for item in observations:
        if item.name not in required_checks:
            continue
        if item.name in seen:
            return GateVerdict(False, "DUPLICATE_REQUIRED_CHECK")
        if item.commit_sha != expected_sha:
            return GateVerdict(False, "STALE_OR_FOREIGN_SHA")
        seen[item.name] = item

    missing = tuple(sorted(required_checks - seen.keys()))
    if missing:
        return GateVerdict(False, "MISSING_REQUIRED_CHECKS", missing)
    if any(item.status != "completed" for item in seen.values()):
        return GateVerdict(False, "INCOMPLETE_REQUIRED_CHECK")
    if any(item.conclusion != "success" for item in seen.values()):
        return GateVerdict(False, "FAILED_REQUIRED_CHECK")
    return GateVerdict(True, "EVIDENCE_CHECKS_PASSED")
