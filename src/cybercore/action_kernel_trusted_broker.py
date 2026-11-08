"""Trusted in-process composition, never accepting caller-supplied policy receipts.

This is an opt-in local dry-run entry point, not an authentication service.
Transport authentication and durable audit remain external prerequisites.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from cybercore.action_kernel import ActionKernel, TaskRequest
from cybercore.action_kernel_hive_bridge import (
    HiveDryRunReceipt,
    ReplayGuard,
    run_local_hive_dry_run,
)


@dataclass(frozen=True)
class BrokerResult:
    """Structured result for the trusted local application."""

    status: str
    reason: str
    hive: HiveDryRunReceipt | None = None


class TrustedLocalHiveBroker:
    """Compose kernel evaluation and Hive dry-run without external receipt input.

    Only trusted application code may instantiate this class or supply actor
    identity, registry, replay store and audit sink. Do not expose it as an
    unauthenticated API or let a model choose its dependencies.
    """

    def __init__(
        self,
        *,
        kernel: ActionKernel,
        registry: Any,
        replay_guard: ReplayGuard,
    ) -> None:
        self._kernel = kernel
        self._registry = registry
        self._replay_guard = replay_guard

    def execute(self, task: TaskRequest, *, authenticated_actor: str) -> BrokerResult:
        if not authenticated_actor or task.actor != authenticated_actor:
            return BrokerResult("DENIED", "ACTOR_MISMATCH")

        receipt = self._kernel.execute(task, trusted_actor=authenticated_actor)
        if receipt.status != "EXECUTED" or receipt.policy.decision != "ALLOW":
            return BrokerResult(receipt.status, receipt.reason)

        # The receipt is generated inside this trusted call, never supplied
        # by the caller. An unresolved/failed Hive dispatch is not success.
        hive_receipt = run_local_hive_dry_run(
            task,
            trusted_actor=authenticated_actor,
            kernel_receipt=receipt,
            registry=self._registry,
            replay_guard=self._replay_guard,
        )
        return BrokerResult("DRY_RUN", "HIVE_DRY_RUN_ONLY", hive=hive_receipt)
