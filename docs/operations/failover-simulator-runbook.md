# WB-FAILOVER-001 — Offline failover simulator

Implementation for [issue #115](https://github.com/cyberDJs/CyberCore/issues/115), informed by the **proposed** [ADR-0014 / PR #114](https://github.com/cyberDJs/CyberCore/pull/114).

**Not a production executor.** The implementation has no network clients, SSH, cloud integrations, DNS lookups or access to real provider credentials. Only the exact in-memory `FakeProvider` type is accepted. Targets are allowlisted symbolic identifiers. It introduces no new authority and does not relax the existing explicit approval boundary.

## Local execution

From repository root, using Python 3.11+ and the existing development dependencies:

```bash
python -m pip install -e '.[dev]'
python -m pytest -q tests/test_failover_sim.py
python -m cybercore.failover_sim --scenario healthy
python -m cybercore.failover_sim --scenario before
python -m cybercore.failover_sim --scenario after
python -m cybercore.failover_sim --scenario veto
```

Use `--db /tmp/local-failover.sqlite3` to inspect persistent SQLite/WAL event records. The default is `:memory:`. CLI output is deterministic JSON containing state, fake-write count and ordered trace; never place real endpoint, credentials or production inventory in CLI options or public logs.

## Design guarantees and limits

- SQLite `PREPARED`/`EXECUTING` checkpoints occur before fake effects; each event includes logical time, decision state, actor/target, capability ID, controller lease/epoch, policy hash, VOODOO verdict, correlation ID and reason.
- Authorization capability, exclusive controller lease, fake effect-boundary fencing, fresh security verdict and scope are independently checked. An unresolved operation on the same target blocks **new** effects pending read-only reconciliation.
- A lost ACK is **not** proof of no effect. Reconciliation checks provider receipts; a missing receipt blocks automatic replay unless this fake provider explicitly enforces effect-key deduplication and fencing. No real exactly-once guarantee is claimed.
- Compensation is a *separate gated fake write*. An unhealthy result becomes `RECOVERY_BLOCKED` on denied or unavailable authorization and `RECOVERY_FAILED` if an allowed fake restore fails. Neither state is reported as success.
- `FakeProvider` state is in memory; after a real OS restart of the simulator process, it is **not** restored. Tests emulate a recoverable fake provider continuing to exist across a CyberCore process restart. This harness cannot certify durability of an external provider.
- Human approval is simulated by an operation ID scoped approval event. This does **not** implement production authentication or human identity proof.

## Failure injection and acceptance

Named tests `F01`–`F10` and `T01`–`T10` cover Kato crash before/after effect, lost ACK, Ruku outage and handback, invalid target, VOODOO veto/timeout/corruption, unhealthy restart and compensation, split brain, stale inventory, RED gate, orphan state, capability/lease expiry, crash persistence and journal failure. Additional regression tests cover conflicting intent and unreconciled-operation barriers.

For release gates, review the **exact PR commit**: run project-wide CI tests, Ruff, Pyright and CodeQL; perform independent security review. Do not merge or deploy the proposed ADR or simulator without required approvals. Delete the simulator files to roll back; no active executor or deployment files are modified.
