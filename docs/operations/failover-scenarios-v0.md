# CyberCore failover scenarios v0 — testable decision matrix

- **Status:** Proposed / design-level closure; **not implemented or production-authorized**
- **Date:** 2026-10-14
- **Parent decision:** [ADR-0014](../adr/0014-risk-tiered-operational-authority-and-failover.md)
- **Applies to:** Ruku (executive), CyberCore (orchestration and independent state audit), VOODOO (security veto), Kato (executor), Kira/Aion (proposers)
- **Existing restriction:** [Current authority boundary](self-deployment-authority-boundary-v0.md) still requires Jan Kočí's explicit authorization for *any* production operation and other listed actions. This specification cannot activate autonomous restarts.

## Five operational rules

1. **No blind duplicate execution:** `operation_id` identifies intent and enables correlation; it does **not** make side effects idempotent. A provider-supported atomic idempotency key or equivalent enforceable effect-boundary deduplication is required for automatic replay. An ambiguous outcome must first be reconciled against the real target; if that is impossible, halt and escalate instead of promising exactly-once execution. Fencing must also be enforced at the effect boundary.
2. **No unilateral security bypass:** VOODOO must give a fresh, attributable `ALLOW` for the authorized scope and decision policy. `DENY`, `UNKNOWN` or timeout blocks new effects. An already executing operation may only complete a strictly pre-authorized bounded safe recovery step whose policy explicitly covers gate loss; never broaden the authority.
3. **Authorization is not leadership:** Ruku may delegate a constrained **capability grant** specifying actions/targets, expiry, budget, policy hash and revocation. Separately, a controller must acquire an **exclusive short-lived leadership/execution lease** with fencing epoch enforced at the effect boundary. A capability alone cannot execute; a leadership lease alone grants no operational permission. CyberCore failover requires both, plus VOODOO allow and any existing human gate.
4. **Recover, don't assume rollback:** Restart cannot be undone. A rollback means restoring verified workload, traffic and application state with tested recovery runbook; database restores additionally need verified data-integrity and RPO evidence.
5. **Unknown means safe stop:** Stop *new* mutations, preserve journal/evidence and alert operator. Monitoring may continue read-only.

## Scenario-to-decision matrix

| ID | Injected fault / trigger | Required autonomous behavior | Result / escalation |
| --- | --- | --- | --- |
| **F01** | Kato disconnects **before** effect | Persisted `PREPARED` intent; CyberCore independently queries provider and journals observation; resume only when absence of prior effect is demonstrable, the capability grant is still valid, a current controller lease is held and provider-side idempotency/fencing is enforceable | Otherwise `UNKNOWN` and operator alert. A missing ACK is never proof of non-execution |
| **F02** | Kato disconnects **after** effect, before acknowledgement | Compare durable journal, provider operation ID (if any), target generation and live service state; reconcile to `VERIFYING` and measure postflight, without dispatching a second write | `SUCCEEDED` if the effect and healthy state are proven; otherwise bounded, separately authorized `RECOVERING` or `UNKNOWN`. No exactly-once guarantee without effect-boundary support |
| **F03** | Ruku becomes unavailable | Fence/expire Ruku's controller lease; CyberCore acquires a new exclusive epoch **separate from** checking its valid delegated GREEN capability grant; independently rechecks VOODOO allow | GREEN in policy only if both grants, fencing and any human gates are satisfied; otherwise stop and escalate to Jan |
| **F04** | Ruku returns while CyberCore controls an operation | Read active operations, stop issuing conflicting commands, fence CyberCore's controller epoch at the executor, then acquire a new Ruku epoch and reconcile in-flight effects | Only the new epoch can dispatch; where exclusivity cannot be enforced, freeze autonomous writes and escalate |
| **F05** | VOODOO denies or times out | Fail closed on initiating new effects; record exact decision and stale/failed gate; do not infer allow from previous successful checks | `STOPPED` with security escalation; only pre-authorized bounded in-flight safe recovery may proceed |
| **F06** | Restart starts but health checks fail | Stop further rollout; compare service state with expected; execute tested, pre-authorized compensation within recovery budget; verify state and error budget | `SUCCEEDED` only after verified restored health; otherwise `RECOVERY_FAILED` + page Jan |
| **F07** | Inventory outdated, target ambiguity, unknown previous effect, or restore untested | Classify as RED/blocked, capture evidence and request human review; no guesswork from a green-looking command | Zero mutating calls; Jan's explicit per-operation approval required for any eventual exception |
| **F08** | Network partition, two contenders for leadership, or CyberCore unreachable | Separate capability-grant check from exclusive monotonic fencing tokens *enforced at execution/effect boundary*; journal recheck; Kato rejects stale epochs; without proven fencing stop new effects | At most one accepted active epoch at a time **where enforcement is verified**; otherwise `STOPPED` + alert, with no autonomous failover |
| **F09** | RED operation requested with agent-only approval | Validate policy before issuing execution envelope; VOODOO cannot replace Jan's required authorization | Request explicitly scoped Jan approval; zero production writes until approved |
| **F10** | CyberCore recovers and observes orphaned in-flight operation | Rehydrate durable journal, correlate provider-operation IDs and current target health, perform read-only reconciliation before accepting new commands | Resume `VERIFYING` or bounded recovery only with valid authority; otherwise quarantine scope and escalate |

**AMBER rule:** Ruku can authorize AMBER only if a *separate approved delegation and existing governance* both explicitly permit that exact operation. For the current CyberCore production boundary, AMBER and GREEN alike still require Jan's operator approval.

## Evidence contract

Each operation record must contain at minimum:

- `operation_id`, `idempotency_key`, correlation/trace ID;
- requested/observed target identities and provider's operation ID where supported;
- desired state, read-before/write-after evidence, inventory version and freshness;
- tier, runbook ID+revision, policy version/hash, approver and VOODOO verdict;
- distinct capability-grant ID/scope/expiry and exclusive controller-lease ID/epoch/expiry/fencing-enforcement proof, actor identities;
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
- `UNKNOWN` may only become `VERIFYING`, `STOPPED` or a fresh, independently justified `PREPARED` after provider-state reconciliation. Retry requires verified effect-boundary idempotency and current, independent authorization plus controller lease; never blindly jump back to `EXECUTING`.
- After a controller-lease epoch change, the old writer must be unable to mutate the target, not merely instructed to stop. An authorization capability cannot serve as a fencing mechanism.
- A timeout is not proof that an action did not execute.
- If the journal or reconciliation source is unavailable, no additional mutating operation may start.

## Acceptance tests (must all pass before any production consideration)

| Test | Fault injection | Assertion |
| --- | --- | --- |
| T01 | Kill Kato before write, then after write but before ACK | With proven provider idempotency, duplicate dispatch is deduplicated at the effect boundary; without it, ambiguous outcomes result in **zero autonomous retry attempts** and operator escalation |
| T02 | Drop Ruku; attempt GREEN and RED with a valid capability grant but no controller lease, then vice versa | Neither case executes without **both** valid grants; with both and VOODOO allow, only pre-authorized GREEN may proceed; RED performs **0 writes** |
| T03 | Partition leader network; race old/new controller epochs | Old epoch rejected at effect boundary in verified-fencing adapter; adapter lacking fencing refuses autonomous failover |
| T04 | Return Ruku during recovery | Fenced handback blocks stale executor writes; all outstanding operations reconciled before new writes |
| T05 | VOODOO DENY, timeout and corrupted verdict | No new side effects; denial is attributed and logged |
| T06 | Stale inventory and missing restore evidence | Both block autonomy; no unapproved operation |
| T07 | Induce post-restart health failure | Verified bounded recovery or explicit `RECOVERY_FAILED` alert; no fictional rollback |
| T08 | Crash and restore CyberCore while Kato resumes | Durable event sequence, unambiguous reconciliation and no replay |
| T09 | Replay expired capability grant, expired controller lease, wrong target or outdated policy hash | Each individually rejected with audit receipt; a valid controller lease does not compensate for missing capability, and vice versa |
| T10 | Audit log write unavailable | New effect fails closed; partial incident is recoverable/readable from last durable state |

## Exit criteria and remaining work

**Scenario design can be considered reviewed/closed** once stakeholders agree to F01–F10, invariants and tests. That does **not** mean runtime code exists, tests ran or live production failover is safe.

Pending before implementation: per-service allowlists, real inventory/health thresholds, availability budget, verified restore drills, WAL storage, enforced fencing, operational alert channel, independent VOODOO integration and formal modification to current approval restrictions. Implement under a separate work block/PR, test in an isolated simulator and authorized staging, then request the correct human approvals before production deployment.

No live configuration, production operation, approval gate or repository `main` branch is changed by this proposal. **Scope limitation:** no claim of exactly-once execution or partition-safe takeover is valid until every relevant executor/provider demonstrably enforces the respective idempotency and fencing contract.
