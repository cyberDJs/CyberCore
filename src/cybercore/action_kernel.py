"""Feature-gated, local-only Action Kernel reference slice.

No network I/O, remote execution, generic shell, or persistent audit writer.
The authenticated caller identity is injected by the trusted application.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
import json
from typing import Callable, Mapping


@dataclass(frozen=True)
class TaskRequest:
    task_id: str
    correlation_id: str
    capability: str
    target_id: str
    arguments: Mapping[str, object]
    expires_at: datetime


@dataclass(frozen=True)
class ExecutionReceipt:
    task_id: str
    correlation_id: str
    status: str
    reason: str
    actor: str
    capability: str
    target_id: str
    evidence_sha256: str | None = None


class ActionKernel:
    """Minimal deterministic dispatcher; explicitly NOT the production authority."""

    def __init__(
        self,
        *,
        targets: Mapping[str, Mapping[str, str]],
        allowed_actors: frozenset[str],
        enabled: bool = False,
        max_input_bytes: int = 2048,
        evidence_sink: Callable[[ExecutionReceipt], None] | None = None,
    ) -> None:
        self._targets = dict(targets)
        self._actors = allowed_actors
        self._enabled = enabled
        self._max_bytes = max_input_bytes
        self._sink = evidence_sink
        self._used: set[str] = set()

    def execute(self, request: TaskRequest, *, trusted_actor: str) -> ExecutionReceipt:
        def receipt(status: str, reason: str, evidence_hash: str | None = None) -> ExecutionReceipt:
            return ExecutionReceipt(
                request.task_id,
                request.correlation_id,
                status,
                reason,
                trusted_actor,
                request.capability,
                request.target_id,
                evidence_hash,
            )

        if not self._enabled:
            return receipt("DENIED", "FEATURE_DISABLED")
        if not trusted_actor or trusted_actor not in self._actors:
            return receipt("DENIED", "ACTOR_DENIED")
        if not request.task_id or not request.correlation_id:
            return receipt("DENIED", "INVALID_ID")
        if request.expires_at.tzinfo is None or request.expires_at <= datetime.now(timezone.utc):
            return receipt("DENIED", "EXPIRED")
        if request.task_id in self._used:
            return receipt("DENIED", "DUPLICATE")
        if request.capability != "diagnostics.synthetic_status.v1":
            return receipt("DENIED", "CAPABILITY_DENIED")
        if request.target_id not in self._targets:
            return receipt("DENIED", "TARGET_DENIED")
        try:
            encoded = json.dumps(request.arguments, allow_nan=False).encode("utf-8")
        except (TypeError, ValueError, OverflowError):
            return receipt("DENIED", "INVALID_ARGUMENTS")
        if len(encoded) > self._max_bytes:
            return receipt("DENIED", "OVERSIZED")
        if request.arguments:
            return receipt("DENIED", "ARGUMENTS_DENIED")
        if self._sink is None:
            return receipt("DENIED", "AUDIT_UNAVAILABLE")

        # Static inventory only: never contact the hostname or execute a command.
        status = self._targets[request.target_id].get("synthetic_status", "unknown")
        if status not in {"ok", "offline", "unknown"}:
            return receipt("DENIED", "INVALID_INVENTORY")
        evidence = {"target_id": request.target_id, "synthetic_status": status}
        digest = sha256(json.dumps(evidence, sort_keys=True).encode("utf-8")).hexdigest()
        result = receipt("EXECUTED", "SYNTHETIC_ONLY", digest)
        try:
            self._sink(result)
        except Exception:
            return receipt("FAILED", "AUDIT_FAILED")
        self._used.add(request.task_id)
        return result
