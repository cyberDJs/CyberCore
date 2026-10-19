"""Feature-gated, local-only Action Kernel reference slice.

No network I/O, remote execution, generic shell, or persistent audit writer.
The authenticated caller identity is injected by the trusted application.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from hashlib import sha256
from threading import Lock
from typing import Callable, Literal, Mapping


ACTION_KERNEL_SCHEMA_VERSION = "action-kernel/v1"
NEXUS_ACTION_CONTRACT = "action/v1"
NEXUS_CAPABILITY_CONTRACT = "capability/v1"
NEXUS_PROVENANCE_CONTRACT = "provenance/v1"

# Compatibility targets only. Internal dataclasses are not Nexus wire objects unless
# explicitly serialized into the Nexus shape.
PolicyDecision = Literal["ALLOW", "DENY"]
CapabilityMode = Literal["read"]
AuditStage = Literal["request", "policy", "execution", "evidence"]


@dataclass(frozen=True)
class Provenance:
    """Nexus-compatible provenance subset for the local Action Kernel slice."""

    source: str
    adapter: str
    source_instance: str
    observed_at: datetime
    confidence: str = "verified"
    collector_run: str | None = None
    contract: str = NEXUS_PROVENANCE_CONTRACT

    def as_nexus(self) -> dict[str, object]:
        payload: dict[str, object] = {
            "contract": self.contract,
            "source": self.source,
            "adapter": self.adapter,
            "sourceInstance": self.source_instance,
            "observedAt": self.observed_at.isoformat(),
            "confidence": self.confidence,
        }
        if self.collector_run is not None:
            payload["collectorRun"] = self.collector_run
        return payload


@dataclass(frozen=True)
class TaskRequest:
    task_id: str
    correlation_id: str
    actor: str
    capability: str
    target_id: str
    arguments: Mapping[str, object]
    requested_at: datetime
    expires_at: datetime
    provenance: Provenance
    schema_version: str = ACTION_KERNEL_SCHEMA_VERSION
    nexus_contract_family: str = NEXUS_ACTION_CONTRACT


@dataclass(frozen=True)
class CapabilityDescriptor:
    name: str
    version: str
    mode: CapabilityMode
    allowed_targets: frozenset[str]
    arguments_allowed: bool = False
    schema_version: str = ACTION_KERNEL_SCHEMA_VERSION
    nexus_contract_family: str = NEXUS_CAPABILITY_CONTRACT


@dataclass(frozen=True)
class PolicyVerdict:
    task_id: str
    correlation_id: str
    decision: PolicyDecision
    reason: str
    actor: str
    capability: str
    target_id: str
    evaluated_at: datetime
    provenance: Provenance
    schema_version: str = ACTION_KERNEL_SCHEMA_VERSION


@dataclass(frozen=True)
class EvidenceMetadata:
    sha256: str
    byte_count: int
    media_type: str = "application/json"
    redacted: bool = True
    schema_version: str = ACTION_KERNEL_SCHEMA_VERSION


@dataclass(frozen=True)
class ExecutionReceipt:
    task_id: str
    correlation_id: str
    status: str
    reason: str
    actor: str
    capability: str
    target_id: str
    policy: PolicyVerdict
    completed_at: datetime
    provenance: Provenance
    evidence: EvidenceMetadata | None = None
    schema_version: str = ACTION_KERNEL_SCHEMA_VERSION
    nexus_contract_family: str = NEXUS_ACTION_CONTRACT

    @property
    def evidence_sha256(self) -> str | None:
        return None if self.evidence is None else self.evidence.sha256


@dataclass(frozen=True)
class AuditEvent:
    stage: AuditStage
    task_id: str
    correlation_id: str
    actor: str
    capability: str
    target_id: str
    outcome: str
    reason: str
    occurred_at: datetime
    provenance: Provenance
    evidence_sha256: str | None = None
    schema_version: str = ACTION_KERNEL_SCHEMA_VERSION


class ActionKernel:
    """Minimal deterministic dispatcher; explicitly NOT the production authority."""

    def __init__(
        self,
        *,
        targets: Mapping[str, Mapping[str, str]],
        allowed_actors: frozenset[str],
        capabilities: Mapping[str, CapabilityDescriptor] | None = None,
        enabled: bool = False,
        max_input_bytes: int = 2048,
        max_evidence_bytes: int = 2048,
        evidence_sink: Callable[[AuditEvent], None] | None = None,
        source_instance: str = "cybercore-local",
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._targets = {target_id: dict(values) for target_id, values in targets.items()}
        self._actors = allowed_actors
        self._enabled = enabled
        self._max_bytes = max_input_bytes
        self._max_evidence_bytes = max_evidence_bytes
        self._sink = evidence_sink
        self._source_instance = source_instance
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self._used: set[str] = set()
        self._task_id_lock = Lock()

        default = CapabilityDescriptor(
            name="diagnostics.synthetic_status.v1",
            version="1",
            mode="read",
            allowed_targets=frozenset(self._targets),
        )
        self._capabilities = dict({default.name: default} if capabilities is None else capabilities)

    def execute(self, request: TaskRequest, *, trusted_actor: str) -> ExecutionReceipt:
        if self._sink is None:
            verdict = self._verdict(request, trusted_actor, "DENY", "AUDIT_UNAVAILABLE")
            return self._receipt(request, trusted_actor, verdict, "DENIED", verdict.reason)

        if not self._audit(
            request,
            trusted_actor,
            stage="request",
            outcome="OBSERVED",
            reason="REQUEST_RECEIVED",
        ):
            verdict = self._verdict(request, trusted_actor, "DENY", "AUDIT_FAILED")
            return self._receipt(request, trusted_actor, verdict, "FAILED", "AUDIT_FAILED")

        verdict = self._evaluate_policy(request, trusted_actor)
        if not self._audit(
            request,
            trusted_actor,
            stage="policy",
            outcome=verdict.decision,
            reason=verdict.reason,
        ):
            return self._receipt(request, trusted_actor, verdict, "FAILED", "AUDIT_FAILED")

        if verdict.decision != "ALLOW":
            return self._receipt(request, trusted_actor, verdict, "DENIED", verdict.reason)

        # Time-of-check is not authority to execute later: revalidate immediately
        # before the local dispatch boundary, after the policy audit callback.
        if request.expires_at <= self._now():
            expired_verdict = self._verdict(request, trusted_actor, "DENY", "EXPIRED")
            if not self._audit(
                request,
                trusted_actor,
                stage="execution",
                outcome="DENIED",
                reason="EXPIRED",
            ):
                return self._receipt(
                    request,
                    trusted_actor,
                    expired_verdict,
                    "FAILED",
                    "AUDIT_FAILED",
                )
            return self._receipt(
                request,
                trusted_actor,
                expired_verdict,
                "DENIED",
                "EXPIRED",
            )

        if not self._reserve_task_id(request.task_id):
            duplicate_verdict = self._verdict(request, trusted_actor, "DENY", "DUPLICATE")
            if not self._audit(
                request,
                trusted_actor,
                stage="execution",
                outcome="DENIED",
                reason="DUPLICATE",
            ):
                return self._receipt(
                    request,
                    trusted_actor,
                    duplicate_verdict,
                    "FAILED",
                    "AUDIT_FAILED",
                )
            return self._receipt(
                request,
                trusted_actor,
                duplicate_verdict,
                "DENIED",
                "DUPLICATE",
            )

        # The reservation is intentionally never released after dispatch starts.
        # If execution or audit becomes uncertain, replay with the same task_id
        # fails closed instead of risking a duplicate effect/evidence record.
        # Static inventory only: never contact the hostname or execute a command.
        status = self._targets[request.target_id]["synthetic_status"]
        evidence_payload = {
            "target_id": request.target_id,
            "synthetic_status": status,
        }
        encoded_evidence = json.dumps(
            evidence_payload,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        if len(encoded_evidence) > self._max_evidence_bytes:
            return self._receipt(request, trusted_actor, verdict, "FAILED", "EVIDENCE_OVERSIZED")

        evidence = EvidenceMetadata(
            sha256=sha256(encoded_evidence).hexdigest(),
            byte_count=len(encoded_evidence),
        )
        result = self._receipt(
            request,
            trusted_actor,
            verdict,
            "EXECUTED",
            "SYNTHETIC_ONLY",
            evidence=evidence,
        )

        if not self._audit(
            request,
            trusted_actor,
            stage="execution",
            outcome="COMPLETED",
            reason=result.reason,
        ):
            return self._receipt(request, trusted_actor, verdict, "FAILED", "AUDIT_FAILED")

        if not self._audit(
            request,
            trusted_actor,
            stage="evidence",
            outcome="RECORDED",
            reason="EVIDENCE_HASHED",
            evidence_sha256=evidence.sha256,
        ):
            return self._receipt(request, trusted_actor, verdict, "FAILED", "AUDIT_FAILED")

        return result

    def _evaluate_policy(self, request: TaskRequest, trusted_actor: str) -> PolicyVerdict:
        def deny(reason: str) -> PolicyVerdict:
            return self._verdict(request, trusted_actor, "DENY", reason)

        if not self._enabled:
            return deny("FEATURE_DISABLED")
        if not trusted_actor or trusted_actor not in self._actors:
            return deny("ACTOR_DENIED")
        if not request.actor or request.actor != trusted_actor:
            return deny("ACTOR_MISMATCH")
        if request.schema_version != ACTION_KERNEL_SCHEMA_VERSION:
            return deny("SCHEMA_DENIED")
        if request.nexus_contract_family != NEXUS_ACTION_CONTRACT:
            return deny("CONTRACT_DENIED")
        if not self._valid_provenance(request.provenance):
            return deny("PROVENANCE_INVALID")
        if not request.task_id or not request.correlation_id:
            return deny("INVALID_ID")
        if request.requested_at.tzinfo is None or request.expires_at.tzinfo is None:
            return deny("INVALID_TIME")
        if request.expires_at <= request.requested_at:
            return deny("INVALID_TIME")
        if request.expires_at <= self._now():
            return deny("EXPIRED")
        if self._task_id_is_reserved(request.task_id):
            return deny("DUPLICATE")

        descriptor = self._capabilities.get(request.capability)
        if descriptor is None:
            return deny("CAPABILITY_DENIED")
        if (
            descriptor.schema_version != ACTION_KERNEL_SCHEMA_VERSION
            or descriptor.nexus_contract_family != NEXUS_CAPABILITY_CONTRACT
            or descriptor.name != request.capability
            or descriptor.mode != "read"
        ):
            return deny("CAPABILITY_DESCRIPTOR_INVALID")
        if request.target_id not in descriptor.allowed_targets:
            return deny("TARGET_DENIED")
        if request.target_id not in self._targets:
            return deny("TARGET_DENIED")

        try:
            encoded = json.dumps(
                request.arguments,
                allow_nan=False,
                sort_keys=True,
                separators=(",", ":"),
            ).encode("utf-8")
        except (TypeError, ValueError, OverflowError):
            return deny("INVALID_ARGUMENTS")
        if len(encoded) > self._max_bytes:
            return deny("OVERSIZED")
        if request.arguments and not descriptor.arguments_allowed:
            return deny("ARGUMENTS_DENIED")

        inventory = self._targets[request.target_id]
        if "synthetic_status" not in inventory:
            return deny("INVALID_INVENTORY")
        status = inventory["synthetic_status"]
        if status not in {"ok", "offline", "unknown"}:
            return deny("INVALID_INVENTORY")
        return self._verdict(request, trusted_actor, "ALLOW", "READ_ONLY_ALLOWED")

    def _verdict(
        self,
        request: TaskRequest,
        trusted_actor: str,
        decision: PolicyDecision,
        reason: str,
    ) -> PolicyVerdict:
        now = self._now()
        return PolicyVerdict(
            task_id=request.task_id,
            correlation_id=request.correlation_id,
            decision=decision,
            reason=reason,
            actor=trusted_actor,
            capability=request.capability,
            target_id=request.target_id,
            evaluated_at=now,
            provenance=self._kernel_provenance(now),
        )

    def _receipt(
        self,
        request: TaskRequest,
        trusted_actor: str,
        verdict: PolicyVerdict,
        status: str,
        reason: str,
        *,
        evidence: EvidenceMetadata | None = None,
    ) -> ExecutionReceipt:
        now = self._now()
        return ExecutionReceipt(
            task_id=request.task_id,
            correlation_id=request.correlation_id,
            status=status,
            reason=reason,
            actor=trusted_actor,
            capability=request.capability,
            target_id=request.target_id,
            policy=verdict,
            completed_at=now,
            provenance=self._kernel_provenance(now),
            evidence=evidence,
        )

    def _audit(
        self,
        request: TaskRequest,
        trusted_actor: str,
        *,
        stage: AuditStage,
        outcome: str,
        reason: str,
        evidence_sha256: str | None = None,
    ) -> bool:
        if self._sink is None:
            return False
        now = self._now()
        event = AuditEvent(
            stage=stage,
            task_id=request.task_id,
            correlation_id=request.correlation_id,
            actor=trusted_actor,
            capability=request.capability,
            target_id=request.target_id,
            outcome=outcome,
            reason=reason,
            occurred_at=now,
            provenance=self._kernel_provenance(now),
            evidence_sha256=evidence_sha256,
        )
        try:
            self._sink(event)
        except Exception:
            return False
        return True

    def _now(self) -> datetime:
        return self._clock()

    def _task_id_is_reserved(self, task_id: str) -> bool:
        with self._task_id_lock:
            return task_id in self._used

    def _reserve_task_id(self, task_id: str) -> bool:
        with self._task_id_lock:
            if task_id in self._used:
                return False
            self._used.add(task_id)
            return True

    def _kernel_provenance(self, observed_at: datetime) -> Provenance:
        return Provenance(
            source="cybercore",
            adapter="action-kernel",
            source_instance=self._source_instance,
            observed_at=observed_at,
            confidence="verified",
        )

    @staticmethod
    def _valid_provenance(provenance: Provenance) -> bool:
        return (
            provenance.contract == NEXUS_PROVENANCE_CONTRACT
            and bool(provenance.source)
            and bool(provenance.adapter)
            and bool(provenance.source_instance)
            and provenance.observed_at.tzinfo is not None
            and provenance.confidence in {"verified", "supported", "inferred", "unknown"}
        )
