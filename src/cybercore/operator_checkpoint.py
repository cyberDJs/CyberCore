"""Pure checkpoint/deduplication adapter for already-validated operator updates.

This module never fetches provider data, authorizes actions, stores checkpoints,
or sends messages. The caller must supply trustworthy, sanitized evidence and
persist the returned fingerprint only after successful delivery.
"""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import re

from cybercore.operator_reporting import OperatorUpdate, format_operator_update

_DIGEST = re.compile(r"[0-9a-f]{64}", re.ASCII)


@dataclass(frozen=True)
class CheckpointDecision:
    report: str | None
    fingerprint: str | None
    reason: str


def checkpoint_operator_update(
    update: OperatorUpdate, *, last_delivered_fingerprint: str | None = None
) -> CheckpointDecision:
    """Decide whether to deliver a material report without making side effects.

    This fingerprint is a content identity, NOT a provenance/security attestation.
    A caller must check source authenticity, redact inputs, and retain the previous
    successfully delivered fingerprint in a separately governed store.
    """
    if last_delivered_fingerprint is not None and (
        type(last_delivered_fingerprint) is not str
        or _DIGEST.fullmatch(last_delivered_fingerprint) is None
    ):
        raise ValueError("INVALID_CHECKPOINT")
    report = format_operator_update(update)
    if report is None:
        return CheckpointDecision(None, None, "NON_MATERIAL")
    fingerprint = sha256(report.encode("utf-8")).hexdigest()
    if fingerprint == last_delivered_fingerprint:
        return CheckpointDecision(None, fingerprint, "UNCHANGED")
    return CheckpointDecision(report, fingerprint, "MATERIAL_CHANGE")
