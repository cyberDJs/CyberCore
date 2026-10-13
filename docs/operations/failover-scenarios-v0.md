# CyberCore failover scenarios v0 — testable decision matrix

- **Status:** Proposed / design-level closure; **not implemented or production-authorized**
- **Date:** 2026-10-14
- **Parent decision:** [ADR-0014](../adr/0014-risk-tiered-operational-authority-and-failover.md)
- **Applies to:** Ruku (executive), CyberCore (orchestration and independent state audit), VOODOO (security veto), Kato (executor), Kira/Aion (proposers)
- **Existing restriction:** [Current authority boundary](self-deployment-authority-boundary-v0.md) still requires Jan Kočí's explicit authorization for *any* production operation and other listed actions. This specification cannot activate autonomous restarts.

## Five operational rules

1. **No double execution:** `operation_id` identifies the intent; `idempotency_key` and a per-target fencing token prevent duplicate side effects. If actual effect is unknown, **reconcile before retrying**. If external providers cannot enforce fencing, fail closed instead of claiming split-brain safety.
2. **No unilateral security bypass:** VOODOO must give a fresh, attributable `ALLOW` for the authorized scope and decision policy. `DENY`, `UNKNOWN` or timeout blocks new effects. An already executing operation may only complete a strictly pre-authorized bounded safe recovery step whose policy explicitly covers gate loss; never broaden the authority.
3. **No power without a lease:** Ruku delegates only an allowlisted operation/target, expiry, max concurrency, operational budget, policy hash, revocation path and fencing epoch. CyberCore's failover has no authority outside that lease.
4. **Recover, don't assume rollback:** Restart cannot be undone. A rollback means restoring verified workload, traffic and application state with tested recovery runbook; database restores additionally need verified data-integrity and RPO evidence.
5. **Unknown means safe stop:** Stop *new* mutations, preserve journal/evidence and alert operator. Monitoring may continue read-only.

## Scenario-to-decision matrix

| ID | Injected fault / trigger | Required autonomous behavior | Result / escalation |
| --- | --- | --- | --- |
| **F01** | Kato disconnects **before** effect | Persisted `PREPARED` intent; CyberCore independently queries provider and journals observation; attempt only if evidence definitively proves no effect, old authorization remains valid and idempotency/fencing are effective | Verified no effect may resume under lease; else `UNKNOWN` and operator alert. No blind retry |
| **F02** | Kato disconnects **after** effect, before acknowledgement | Compare durable journal, target generation and live service state; reconcile to `VERIFYING` and measure postflight | `SUCCEEDED` if proven healthy; otherwise bounded `RECOVERING` or `UNKNOWN`. Exactly one side effect |
| **F03** | Ruku becomes unavailable | Existing controller lease expires / fenced; CyberCore acquires next exclusive epoch and verifies still-valid **pre-authorized GREEN** scope plus VOODOO allow | GREEN in policy only; AMBER/RED or any missing gate goes to Jan. No unapproved new authority |
| **F04** | Ruku returns while CyberCore controls an operation | Read active operations, stop issuing conflicting commands, revoke/fence old controller, take new epoch in one controlled handback | One active writer per target, no duplicate operation, handback record retained |
| **F05** | VOODOO denies or times out | Fail closed on initiating new effects; record exact decision and stale/failed gate; do not infer allow from previous successful checks | `STOPPED` with security escalation; only pre-authorized bounded in-flight safe recovery may proceed |
| **F06** | Restart starts but health checks fail | Stop further rollout; compare service state with expected; execute tested, pre-authorized compensation within recovery budget; verify state and error budget | `SUCCEEDED` only after verified restored health; otherwise `RECOVERY_FAILED` + page Jan |
| **F07** | Inventory outdated, target ambiguity, unknown previous effect, or restore untested | Classify as RED/blocked, capture evidence and request human review; no guesswork from a green-looking command | Zero mutating calls; Jan's explicit per-operation approval required for any eventual exception |
| **F08** | Network partition, two contenders for leadership, or CyberCore unreachable | Exclusive monotonic fencing tokens *enforced at effect boundary*, journal recheck; Kato rejects stale epochs; without enforceable fencing stop new effects | Never two active writers; if cannot establish exclusivity, `STOPPED` + alert |
| **F09** | RED operation requested with agent-only approval | Validate policy before issuing execution envelope; VOODOO cannot replace Jan's required authorization | Request explicitly scoped Jan approval; zero production writes until approved |
| **F10** | CyberCore recovers and observes orphaned in-flight operation | Rehydrate durable journal, correlate provider-operation IDs and current target health, perform read-only reconciliation before accepting new commands | Resume `VERIFYING` or bounded recovery only with valid authority; otherwise quarantine scope and escalate |

**AMBER rule:** Ruku can authorize AMBER only if a *separate approved delegation and existing governance* both explicitly permit that exact operation. For the current CyberCore production boundary, AMBER and GREEN alike still require Jan's operator approval.

## Evidence contract

Each operation record must contain at minimum:

- `operation_id`, `idempotency_key`, correlation/trace ID;
- requested/observed target identities and provider's operation ID where supported;
- desired state, read-before/write-after evidence, inventory version and freshness;
- tier, runbook ID+revision, policy version/hash, approver and VOODOO verdict;
- authority lease ID, epoch/fencing token, valid-until, actor identities;
- WAL checkpoint written **before** each side effect, result and monotonic event sequence;
- health checks, abort/verification deadlines, downtime/RTO/RPO budgets;
- executed recovery steps, final outcome, immutable/tamper-evident receipt.

Do not include credentials, tokens or private topology in the public repository; only sanitized evidence, identifiers and schema examples.

## State machine and stop invariants

```text
PROPOSED -> CLASSIFIED -> PREFLIGHTED -> AUTHORIZED -> PREPARED
 PREPARED -> EXECUTING -> VERIFYING -> SUCCEEDED
     |           |            |
     +-----------+------------+-----> UNKNOWN
                               \-----> RECOVERING -> VERIFYING
                    ANY unsafe gate --> STOPPED / ESCALATED
```

- `PREPARED` is durable before invocation; no transient memory-only intent.
- `UNKNOWN` may only become `VERIFYING`, `STOPPED` or a fresh, independently justified `PREPARED` with reconciled provider state; never blindly jump back to `EXECUTING`.
- After a lease epoch change, the old writer must be unable to mutate the target, not merely instructed to stop.
- A timeout is not proof that an action did not execute.
- If the journal or reconciliation source is unavailable, no additional mutating operation may start.

## Acceptance tests (must all pass before any production consideration)

| Test | Fault injection | Assertion |
| --- | --- | --- |
| T01 | Kill Kato before write, then after write but before ACK | Provider sees **0 or 1** justified executions, never an unverified second write |
| T02 | Drop Ruku; attempt GREEN and RED under preloaded bounded lease | GREEN only with all gates and exclusive lease; RED performs **0 writes** |
| T03 | Partition leader network; race old/new epochs | Old epoch rejected at execution boundary; at most one writer |
| T04 | Return Ruku during recovery | No overlap of controllers, all outstanding operations reconciled |
| T05 | VOODOO DENY, timeout and corrupted verdict | No new side effects; denial is attributed and logged |
| T06 | Stale inventory and missing restore evidence | Both block autonomy; no unapproved operation |
| T07 | Induce post-restart health failure | Verified bounded recovery or explicit `RECOVERY_FAILED` alert; no fictional rollback |
| T08 | Crash and restore CyberCore while Kato resumes | Durable event sequence, unambiguous reconciliation and no replay |
| T09 | Replay expired lease / wrong target / outdated policy hash | All rejected with audit receipt |
| T10 | Audit log write unavailable | New effect fails closed; partial incident is recoverable/readable from last durable state |

## Exit criteria and remaining work

**Scenario design can be considered reviewed/closed** once stakeholders agree to F01–F10, invariants and tests. That does **not** mean runtime code exists, tests ran or live production failover is safe.

Pending before implementation: per-service allowlists, real inventory/health thresholds, availability budget, verified restore drills, WAL storage, enforced fencing, operational alert channel, independent VOODOO integration and formal modification to current approval restrictions. Implement under a separate work block/PR, test in an isolated simulator and authorized staging, then request the correct human approvals before production deployment.

No live configuration, production operation, approval gate or repository `main` branch is changed by this proposal.
