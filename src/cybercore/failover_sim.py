"""Offline, deterministic CyberCore failover fault-injection simulator.

No imports or adapters to real transports, providers, credentials or executors.
A production target is deliberately unrepresentable in this module.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


class SimulatedCrash(RuntimeError):
    """Controlled process loss at an effect boundary."""


class UnsafeEffect(RuntimeError):
    """The fake provider refused an unsafe effect."""


class AuditUnavailable(RuntimeError):
    """A durable local journal update was not possible."""


@dataclass
class Clock:
    now: int = 1_800_000_000

    def advance(self, seconds: int) -> None:
        self.now += seconds


@dataclass(frozen=True)
class Capability:
    capability_id: str
    holder: str
    target: str
    action: str
    policy_hash: str
    expires: int


@dataclass(frozen=True)
class Lease:
    lease_id: str
    holder: str
    target: str
    epoch: int
    expires: int


@dataclass(frozen=True)
class Verdict:
    decision: Literal["ALLOW", "DENY", "UNKNOWN"]
    target: str
    action: str
    policy_hash: str
    expires: int
    valid: bool = True


@dataclass(frozen=True)
class Request:
    operation_id: str
    actor: str = "Ruku"
    target: str = "service_a"
    action: str = "restart"
    tier: str = "GREEN"
    policy_hash: str = "policy-v1"
    inventory_fresh: bool = True
    restore_verified: bool = True
    production: bool = False
    human_approval: str | None = None
    correlation_id: str = "trace-001"


class Journal:
    """SQLite WAL; operation rows and append-only events commit atomically."""

    def __init__(self, path: str | Path) -> None:
        self.conn = sqlite3.connect(str(path))
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=FULL")
        self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS operations (
              operation_id TEXT PRIMARY KEY, actor TEXT NOT NULL,
              target TEXT NOT NULL, action TEXT NOT NULL, tier TEXT NOT NULL,
              policy_hash TEXT NOT NULL, correlation_id TEXT NOT NULL,
              idempotency_key TEXT NOT NULL, state TEXT NOT NULL,
              before_generation INTEGER NOT NULL, changed INTEGER NOT NULL DEFAULT 0,
              provider_op TEXT, lease_epoch INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS events (
              seq INTEGER PRIMARY KEY AUTOINCREMENT, operation_id TEXT NOT NULL,
              timestamp INTEGER NOT NULL, record TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS leases (
              target TEXT PRIMARY KEY, holder TEXT NOT NULL,
              lease_id TEXT NOT NULL, epoch INTEGER NOT NULL,
              expires INTEGER NOT NULL
            );
            """
        )
        self.fail_writes = False

    def _writable(self) -> None:
        if self.fail_writes:
            raise AuditUnavailable("injected journal-write failure")

    def begin(self, req: Request, generation: int, now: int) -> None:
        self._writable()
        try:
            with self.conn:
                self.conn.execute(
                    """INSERT INTO operations
                    (operation_id, actor, target, action, tier, policy_hash,
                     correlation_id, idempotency_key, state, before_generation)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'PREPARED', ?)""",
                    (
                        req.operation_id,
                        req.actor,
                        req.target,
                        req.action,
                        req.tier,
                        req.policy_hash,
                        req.correlation_id,
                        req.operation_id,
                        generation,
                    ),
                )
                self._event(
                    req.operation_id,
                    now,
                    {
                        "state": "PREPARED",
                        "actor": req.actor,
                        "target": req.target,
                        "policy_hash": req.policy_hash,
                        "correlation_id": req.correlation_id,
                    },
                )
        except sqlite3.Error as exc:
            raise AuditUnavailable("journal prepare failed") from exc

    def _event(self, operation_id: str, now: int, data: dict[str, object]) -> None:
        self.conn.execute(
            "INSERT INTO events(operation_id, timestamp, record) VALUES(?, ?, ?)",
            (operation_id, now, json.dumps(data, sort_keys=True, separators=(",", ":"))),
        )

    def transition(
        self,
        operation_id: str,
        now: int,
        state: str,
        *,
        capability_id: str = "",
        lease_id: str = "",
        lease_epoch: int = 0,
        verdict: str = "",
        provider_op: str | None = None,
        changed: bool | None = None,
        reason: str = "",
    ) -> None:
        self._writable()
        row = self.get(operation_id)
        if row is None:
            raise AuditUnavailable("missing persisted operation")
        event: dict[str, object] = {
            "state": state,
            "actor": row["actor"],
            "target": row["target"],
            "policy_hash": row["policy_hash"],
            "correlation_id": row["correlation_id"],
            "capability_id": capability_id,
            "lease_id": lease_id,
            "lease_epoch": lease_epoch,
            "voodoo": verdict,
            "reason": reason,
        }
        try:
            with self.conn:
                self.conn.execute(
                    """UPDATE operations SET state=?, changed=COALESCE(?, changed),
                    provider_op=COALESCE(?, provider_op),
                    lease_epoch=CASE WHEN ? > 0 THEN ? ELSE lease_epoch END
                    WHERE operation_id=?""",
                    (
                        state,
                        None if changed is None else int(changed),
                        provider_op,
                        lease_epoch,
                        lease_epoch,
                        operation_id,
                    ),
                )
                self._event(operation_id, now, event)
        except sqlite3.Error as exc:
            raise AuditUnavailable("journal transition failed") from exc

    def get(self, operation_id: str) -> sqlite3.Row | None:
        return self.conn.execute(
            "SELECT * FROM operations WHERE operation_id=?", (operation_id,)
        ).fetchone()

    def events(self, operation_id: str) -> list[dict[str, object]]:
        return [
            dict(seq=row["seq"], timestamp=row["timestamp"], **json.loads(row["record"]))
            for row in self.conn.execute(
                "SELECT seq, timestamp, record FROM events WHERE operation_id=? ORDER BY seq",
                (operation_id,),
            )
        ]

    def acquire(
        self, target: str, holder: str, now: int, *, takeover: bool = False, ttl: int = 60
    ) -> Lease:
        self._writable()
        try:
            with self.conn:
                current = self.conn.execute(
                    "SELECT * FROM leases WHERE target=?", (target,)
                ).fetchone()
                if current is not None and current["expires"] > now and not takeover:
                    raise UnsafeEffect("active lease prevents competing controller")
                epoch = 1 if current is None else current["epoch"] + 1
                lease = Lease(f"lease-{epoch}-{holder}", holder, target, epoch, now + ttl)
                self.conn.execute(
                    """INSERT INTO leases VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(target) DO UPDATE SET holder=excluded.holder,
                    lease_id=excluded.lease_id,epoch=excluded.epoch,expires=excluded.expires""",
                    (target, holder, lease.lease_id, epoch, lease.expires),
                )
                return lease
        except sqlite3.Error as exc:
            raise AuditUnavailable("lease acquisition failed") from exc

    def in_flight(self, target: str, excluding: str) -> bool:
        row = self.conn.execute(
            """SELECT 1 FROM operations WHERE target=? AND operation_id != ?
            AND state IN ('PREPARED', 'EXECUTING', 'VERIFYING', 'UNKNOWN', 'RECOVERING')
            LIMIT 1""",
            (target, excluding),
        ).fetchone()
        return row is not None

    def current_lease(self, target: str) -> Lease | None:
        row = self.conn.execute("SELECT * FROM leases WHERE target=?", (target,)).fetchone()
        return (
            Lease(row["lease_id"], row["holder"], target, row["epoch"], row["expires"])
            if row
            else None
        )

    def close(self) -> None:
        self.conn.close()


class FakeProvider:
    """Inert in-memory provider with enforced fencing and idempotency."""

    def __init__(
        self,
        *,
        targets: tuple[str, ...] = ("service_a", "service_b"),
        fencing: bool = True,
        idempotency: bool = True,
    ) -> None:
        if any(not re.fullmatch(r"[a-z][a-z0-9_]*", name) for name in targets):
            raise ValueError("fake targets must be local symbolic names")
        self.targets = frozenset(targets)
        self.health = dict.fromkeys(targets, True)
        self.generation = dict.fromkeys(targets, 0)
        self.epochs = dict.fromkeys(targets, 0)
        self.fencing = fencing
        self.idempotency = idempotency
        self.effects: list[tuple[str, str, int, str]] = []
        self.receipts: dict[str, tuple[str, str, int, str]] = {}
        self.fail_restart = False
        self.fail_restore = False
        self.readable = True

    def validate_target(self, target: str) -> bool:
        return bool(re.fullmatch(r"[a-z][a-z0-9_]*", target) and target in self.targets)

    def fence(self, target: str, epoch: int) -> None:
        if not self.fencing:
            raise UnsafeEffect("fake adapter has no enforced fencing")
        if epoch < self.epochs[target]:
            raise UnsafeEffect("stale fencing epoch")
        self.epochs[target] = epoch

    def observe(self, target: str, key: str) -> tuple[bool, int, tuple[str, str, int, str] | None]:
        if not self.readable:
            raise UnsafeEffect("fake provider observation unavailable")
        return self.health[target], self.generation[target], self.receipts.get(key)

    def mutate(self, target: str, action: str, epoch: int, key: str) -> str:
        if not self.validate_target(target) or action not in {"restart", "restore"}:
            raise UnsafeEffect("non-fake target or unsupported effect")
        if not self.fencing or epoch != self.epochs[target]:
            raise UnsafeEffect("effect-boundary fencing rejected")
        if self.idempotency and key in self.receipts:
            return self.receipts[key][3]
        self.generation[target] += 1
        self.health[target] = not (self.fail_restart if action == "restart" else self.fail_restore)
        op_id = f"fake-effect-{len(self.effects) + 1}"
        receipt = (target, action, epoch, op_id)
        self.effects.append(receipt)
        if self.idempotency:
            self.receipts[key] = receipt
        return op_id


class Simulator:
    """Security-first coordinator; deliberately accepts *only* FakeProvider."""

    def __init__(
        self, journal: Journal, provider: FakeProvider, clock: Clock | None = None
    ) -> None:
        if type(provider) is not FakeProvider:
            raise TypeError("only the exact inert FakeProvider class is accepted")
        self.journal = journal
        self.provider = provider
        self.clock = clock or Clock()
        self.capabilities: dict[tuple[str, str, str], Capability] = {}
        self.verdicts: dict[tuple[str, str], Verdict] = {}
        self.human_approvals: set[str] = set()
        self.alerts: list[str] = []

    def grant(
        self,
        holder: str,
        target: str,
        action: str,
        *,
        policy_hash: str = "policy-v1",
        ttl: int = 60,
    ) -> Capability:
        if not self.provider.validate_target(target):
            raise UnsafeEffect("invalid fake target")
        cap = Capability(
            f"grant-{holder}-{target}-{action}",
            holder,
            target,
            action,
            policy_hash,
            self.clock.now + ttl,
        )
        self.capabilities[holder, target, action] = cap
        return cap

    def lease(
        self, holder: str, target: str = "service_a", *, takeover: bool = False, ttl: int = 60
    ) -> Lease:
        if not self.provider.validate_target(target) or not self.provider.fencing:
            raise UnsafeEffect("fencing unavailable")
        lease = self.journal.acquire(target, holder, self.clock.now, takeover=takeover, ttl=ttl)
        self.provider.fence(target, lease.epoch)
        return lease

    def allow(
        self,
        target: str = "service_a",
        action: str = "restart",
        *,
        decision: Literal["ALLOW", "DENY", "UNKNOWN"] = "ALLOW",
        policy_hash: str = "policy-v1",
        ttl: int = 60,
        valid: bool = True,
    ) -> Verdict:
        verdict = Verdict(decision, target, action, policy_hash, self.clock.now + ttl, valid)
        self.verdicts[target, action] = verdict
        return verdict

    def gates(self, req: Request) -> tuple[bool, str, str, str, int, str]:
        if req.production:
            return False, "production forbidden", "", "", 0, ""
        if not self.provider.validate_target(req.target):
            return False, "target not a local fake", "", "", 0, ""
        if req.action not in {"restart", "restore"}:
            return False, "invalid action", "", "", 0, ""
        if not req.inventory_fresh or not req.restore_verified:
            return False, "stale inventory or untested restore", "", "", 0, ""
        if req.tier not in {"GREEN", "AMBER", "RED"}:
            return False, "unrecognized risk tier", "", "", 0, ""
        if self.journal.in_flight(req.target, req.operation_id):
            return False, "unreconciled prior operation on target", "", "", 0, ""
        if req.tier in {"AMBER", "RED"} and (
            req.human_approval != "Jan Kočí" or req.operation_id not in self.human_approvals
        ):
            return False, "explicit scoped Jan approval missing", "", "", 0, ""
        cap = self.capabilities.get((req.actor, req.target, req.action))
        if cap is None or cap.expires <= self.clock.now or cap.policy_hash != req.policy_hash:
            return False, "capability missing, expired or wrong policy", "", "", 0, ""
        lease = self.journal.current_lease(req.target)
        if (
            lease is None
            or lease.holder != req.actor
            or lease.expires <= self.clock.now
            or not self.provider.fencing
            or lease.epoch != self.provider.epochs[req.target]
        ):
            return False, "exclusive fenced lease missing or stale", cap.capability_id, "", 0, ""
        v = self.verdicts.get((req.target, req.action))
        if (
            v is None
            or v.decision != "ALLOW"
            or not v.valid
            or v.expires <= self.clock.now
            or v.policy_hash != req.policy_hash
        ):
            return (
                False,
                "VOODOO veto/timeout/corrupt verdict",
                cap.capability_id,
                lease.lease_id,
                lease.epoch,
                v.decision if v else "UNKNOWN",
            )
        return True, "", cap.capability_id, lease.lease_id, lease.epoch, "ALLOW"

    def _transition(
        self,
        req: Request,
        state: str,
        *,
        reason: str = "",
        provider_op: str | None = None,
        changed: bool | None = None,
    ) -> None:
        _ok, _why, cap_id, lease_id, epoch, verdict = self.gates(req)
        self.journal.transition(
            req.operation_id,
            self.clock.now,
            state,
            capability_id=cap_id,
            lease_id=lease_id,
            lease_epoch=epoch,
            verdict=verdict,
            provider_op=provider_op,
            changed=changed,
            reason=reason,
        )
        if state in {"STOPPED", "UNKNOWN", "RECOVERY_FAILED", "RECOVERY_BLOCKED"}:
            self.alerts.append(f"{req.operation_id}:{state}:{reason}")

    def run(self, req: Request, *, crash: str | None = None) -> str:
        if self.journal.get(req.operation_id) is not None:
            raise UnsafeEffect("duplicate operation ID; reconcile instead")
        # Invalid symbolic targets are recorded as a refusal, never passed to a provider.
        generation = (
            self.provider.generation[req.target] if self.provider.validate_target(req.target) else 0
        )
        self.journal.begin(req, generation, self.clock.now)
        ok, reason, *_ = self.gates(req)
        if not ok:
            self._transition(req, "STOPPED", reason=reason)
            return "STOPPED"
        if crash == "before_effect":
            raise SimulatedCrash("Kato stopped after durable PREPARED")
        self._transition(req, "EXECUTING")  # durable before provider effect
        if crash == "during_effect":
            raise SimulatedCrash("Kato lost after EXECUTING checkpoint")
        # The preflight verdict is not a lasting authorization: sample all gates
        # again immediately before the fake effect boundary.
        ok, reason, *_ = self.gates(req)
        if not ok:
            self._transition(req, "STOPPED", reason=reason)
            return "STOPPED"
        lease = self.journal.current_lease(req.target)
        if lease is None:
            self._transition(req, "UNKNOWN", reason="lost lease")
            return "UNKNOWN"
        try:
            receipt = self.provider.mutate(req.target, req.action, lease.epoch, req.operation_id)
        except UnsafeEffect as exc:
            self._transition(req, "STOPPED", reason=str(exc))
            return "STOPPED"
        if crash == "after_effect":
            raise SimulatedCrash("Kato stopped after effect before acknowledgement")
        self._transition(req, "VERIFYING", provider_op=receipt, changed=True)
        try:
            health, _, _ = self.provider.observe(req.target, req.operation_id)
        except UnsafeEffect as exc:
            self._transition(req, "UNKNOWN", reason=f"post-effect observation failed: {exc}")
            return "UNKNOWN"
        if health:
            self._transition(req, "SUCCEEDED")
            return "SUCCEEDED"
        self._transition(req, "UNKNOWN", reason="health failed after effect")
        return "UNKNOWN"

    def reconcile(self, req: Request, *, retry: bool = False) -> str:
        row = self.journal.get(req.operation_id)
        if row is None:
            raise UnsafeEffect("nothing to reconcile")
        if row["state"] in {"STOPPED", "SUCCEEDED", "RECOVERY_FAILED", "RECOVERY_BLOCKED"}:
            return str(row["state"])
        if any(
            row[field] != getattr(req, field)
            for field in ("actor", "target", "action", "tier", "policy_hash", "correlation_id")
        ):
            raise UnsafeEffect("reconciliation request conflicts with durable intent")
        try:
            healthy, _generation, receipt = self.provider.observe(req.target, req.operation_id)
        except UnsafeEffect as exc:
            self._transition(req, "UNKNOWN", reason=str(exc))
            return "UNKNOWN"
        if receipt:
            self._transition(req, "VERIFYING", provider_op=receipt[3], changed=True)
            if healthy:
                self._transition(req, "SUCCEEDED")
                return "SUCCEEDED"
            self._transition(req, "UNKNOWN", reason="observed unhealthy service")
            return "UNKNOWN"
        # No receipt is NOT proof that a write did not happen.
        if not retry or not self.provider.idempotency or not self.provider.fencing:
            self._transition(req, "UNKNOWN", reason="effect not provably absent")
            return "UNKNOWN"
        ok, reason, *_ = self.gates(req)
        if not ok:
            self._transition(req, "STOPPED", reason=reason)
            return "STOPPED"
        self._transition(req, "EXECUTING", reason="safe idempotent re-dispatch")
        # A durable checkpoint does not preserve authorization; fail closed on
        # revocation, expiry, or takeover before any replayed effect.
        ok, reason, *_ = self.gates(req)
        if not ok:
            self._transition(req, "STOPPED", reason=reason)
            return "STOPPED"
        lease = self.journal.current_lease(req.target)
        if lease is None:
            self._transition(req, "UNKNOWN", reason="lease vanished")
            return "UNKNOWN"
        receipt_id = self.provider.mutate(req.target, req.action, lease.epoch, req.operation_id)
        self._transition(req, "VERIFYING", provider_op=receipt_id, changed=True)
        try:
            healthy, _, _ = self.provider.observe(req.target, req.operation_id)
        except UnsafeEffect as exc:
            self._transition(req, "UNKNOWN", reason=f"post-retry observation failed: {exc}")
            return "UNKNOWN"
        state = "SUCCEEDED" if healthy else "UNKNOWN"
        self._transition(
            req, state, reason="provider health verified" if healthy else "effect unhealthy"
        )
        return state

    def compensate(self, req: Request) -> str:
        row = self.journal.get(req.operation_id)
        if row is None or row["state"] not in {"UNKNOWN", "RECOVERING"}:
            raise UnsafeEffect("compensation requires an unresolved operation")
        if any(
            row[field] != getattr(req, field)
            for field in ("actor", "target", "action", "tier", "policy_hash", "correlation_id")
        ):
            raise UnsafeEffect("compensation request conflicts with durable intent")
        restore_req = Request(
            req.operation_id,
            req.actor,
            req.target,
            "restore",
            req.tier,
            req.policy_hash,
            req.inventory_fresh,
            req.restore_verified,
            req.production,
            req.human_approval,
            req.correlation_id,
        )
        ok, reason, *_ = self.gates(restore_req)
        if not ok:
            self._transition(restore_req, "RECOVERY_BLOCKED", reason=reason)
            return "RECOVERY_BLOCKED"
        self._transition(restore_req, "RECOVERING", reason="approved distinct restore effect")
        # VOODOO and scoped restore authority must still be valid at the
        # compensation effect boundary, not just before journaling.
        ok, reason, *_ = self.gates(restore_req)
        if not ok:
            self._transition(restore_req, "RECOVERY_BLOCKED", reason=reason)
            return "RECOVERY_BLOCKED"
        lease = self.journal.current_lease(req.target)
        if lease is None:
            self._transition(restore_req, "RECOVERY_BLOCKED", reason="lease missing")
            return "RECOVERY_BLOCKED"
        try:
            provider_op = self.provider.mutate(
                req.target, "restore", lease.epoch, f"{req.operation_id}:restore"
            )
        except UnsafeEffect as exc:
            self._transition(restore_req, "RECOVERY_FAILED", reason=str(exc))
            return "RECOVERY_FAILED"
        self._transition(restore_req, "VERIFYING", provider_op=provider_op, changed=True)
        try:
            healthy, _, _ = self.provider.observe(req.target, f"{req.operation_id}:restore")
        except UnsafeEffect as exc:
            self._transition(
                restore_req, "UNKNOWN", reason=f"post-restore observation failed: {exc}"
            )
            return "UNKNOWN"
        state = "SUCCEEDED" if healthy else "RECOVERY_FAILED"
        self._transition(
            restore_req,
            state,
            reason="restored health verified" if healthy else "compensation health check failed",
        )
        return state


def main() -> int:
    parser = argparse.ArgumentParser(description="Inert CyberCore failover simulator (offline)")
    parser.add_argument(
        "--scenario", choices=("before", "after", "veto", "healthy"), default="healthy"
    )
    parser.add_argument("--db", default=":memory:", help="local SQLite journal, default in-memory")
    args = parser.parse_args()
    journal = Journal(args.db)
    sim = Simulator(journal, FakeProvider())
    sim.grant("Ruku", "service_a", "restart")
    sim.lease("Ruku")
    sim.allow()
    request = Request("local-demo")
    try:
        if args.scenario == "veto":
            sim.allow(decision="DENY")
        state = sim.run(
            request, crash={"before": "before_effect", "after": "after_effect"}.get(args.scenario)
        )
    except SimulatedCrash:
        state = sim.reconcile(request)
    print(
        json.dumps(
            {
                "scenario": args.scenario,
                "state": state,
                "writes": len(sim.provider.effects),
                "events": journal.events(request.operation_id),
            },
            sort_keys=True,
        )
    )
    journal.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
