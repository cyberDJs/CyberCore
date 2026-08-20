from __future__ import annotations

from typing import Literal, NotRequired, TypedDict

Scalar = str | int | float | bool | None
Authority = Literal["CANONICAL", "EVIDENCE", "WORKING"]
SOTStatus = Literal["CURRENT", "DRIFT", "CONFLICT", "UNKNOWN"]
RemediationDisposition = Literal["NONE", "EXISTING", "PROPOSE"]
Recommendation = Literal[
    "NO_ACTION",
    "OBSERVE_EXISTING_REMEDIATION",
    "PROPOSE_REMEDIATION",
    "ESCALATE_AUTHORITY_CONFLICT",
    "REQUEST_MORE_EVIDENCE",
]


class SourceSnapshot(TypedDict):
    """Normalized read-only facts observed from one source."""

    source_id: str
    authority: Authority
    facts: dict[str, Scalar]


class Remediation(TypedDict):
    """Known remediation that may already cover detected drift."""

    id: str
    state: Literal["OPEN", "CLOSED"]
    target_keys: list[str]


class Finding(TypedDict):
    kind: Literal["DRIFT", "CONFLICT", "UNKNOWN"]
    key: str
    sources: list[str]
    expected: NotRequired[Scalar]
    observed: NotRequired[Scalar]


class ReconciliationState(TypedDict):
    sources: list[SourceSnapshot]
    remediations: list[Remediation]
    canonical_facts: NotRequired[dict[str, Scalar]]
    findings: NotRequired[list[Finding]]
    status: NotRequired[SOTStatus]
    remediation_disposition: NotRequired[RemediationDisposition]
    remediation_ids: NotRequired[list[str]]
    recommendation: NotRequired[Recommendation]
