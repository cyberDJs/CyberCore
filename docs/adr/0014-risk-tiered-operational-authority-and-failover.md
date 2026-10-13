# ADR-0014: Risk-tiered operational authority and failover

- **Status:** Proposed — not approved or implemented
- **Date:** 2026-10-14
- **Scope:** CyberCore, CyberHIVE, VOODOO, Kato, Ruku
- **Change type:** Architectural governance proposal; no production or provider mutation

## Goal and existing authority boundaries

Routine maintenance should not require Jan to act as a human confirmation button. Ruku may make bounded executive decisions and delegate within an *already approved* policy; Kira/Aion propose, CyberCore verifies operational state, VOODOO applies a mandatory independent security veto, and Kato executes and journals effects.

This proposal does **not** grant production write permissions. Existing [governance](../governance.md) and [authority boundary](../operations/self-deployment-authority-boundary-v0.md) continue to apply: production operations, authority changes and canonical merges require the currently applicable explicit approvals. No autonomous production restart is authorized by this ADR alone.

## Risk tiers (proposed)

| Tier | Examples | Execution rule |
| --- | --- | --- |
| **GREEN / standard** | Restart of an approved redundant stateless service; non-destructive recovery under a tested runbook | Autonomous **only after** specific runbook, target allowlist, tested recovery, monitoring, operational limits, and delegation have been formally approved; VOODOO must allow |
| **AMBER / elevated** | Single-instance maintenance; stateful restart; routing changes with bounded blast radius | Additional independent impact and recoverability review; Ruku decision with VOODOO allow **only when existing policy explicitly permits it**; otherwise Jan's approval |
| **RED / exceptional** | Destructive or irreversible action; database data/schema mutations; missing rollback; uncertain target state; unbounded outage; policy exception, secrets/identity/network trust changes | Jan's explicit authorization plus all applicable independent security and project gates; no autonomous execution |

**Risk classification is based on actual blast radius and recoverability, not the operation name.** An ordinary-looking restart can be RED if it risks material downtime or unrecoverable state.

GREEN eligibility requires **all** of:
1. Versioned approved runbook for the exact action/target; defined time window, concurrency and availability budget.
2. Fresh inventory, dependency graph and health evidence; redundant capacity and impact bounded by policy.
3. Tested recovery/compensation procedure with operator-visible evidence. Restart cannot literally be undone; recovery must restore a verified service state.
4. Idempotency key, durable operation journal and safe effect-reconciliation path.
5. Explicit VOODOO allow bound to the operation, actor, target and policy version.
6. Measurable postflight success criteria, abort timeout and audit trail.
7. No existing stricter governance restriction.

Uncertain evidence, unavailable VOODOO, a security denial, untested recovery, exhausted availability budget, expired delegated authority or unavailable observations => **STOP and escalate**, never silent downgrade of controls.

## Responsibilities

- **Kira/Aion:** propose actions and supporting evidence, without implicit production authority.
- **Ruku:** accountable executive decision-maker within established boundaries; may grant scoped, revocable, expiring leases.
- **CyberCore:** audits actual target/provider state, verifies policy, coordinates failover, prevents duplicate actions.
- **VOODOO:** independent mandatory security gate; fail closed.
- **Kato:** authorized executor; persists operation progress; never blindly retries after connection loss.
- **Jan Kočí:** authorizes exceptions, out-of-policy/RED actions, and all changes currently requiring human approval.
- **Eimy:** consultation/review for material governance changes where project rules require it.

No agent can self-award new permissions, impersonate the independent veto, or substitute a conversational agreement for formal policy approval.

## Execution and lost-contact recovery

Use durable state machine:
`PROPOSED -> CLASSIFIED -> PREFLIGHTED -> AUTHORIZED -> EXECUTING -> VERIFYING -> SUCCEEDED`
with `UNKNOWN`, `STOPPED` and `RECOVERING` branches.

Every action uses `operation_id` plus `idempotency_key`. Kato durably records target, plan, authority/policy version, intended state and checkpoint before each effect. On loss of connection it reports the last checkpoint after recovery. CyberCore reads persisted evidence and independently inspects provider state; an `UNKNOWN` action must be **reconciled before any replay**.

If Ruku drops out, CyberCore may take over **only pre-authorized GREEN** cases with a valid bounded authority lease; everything else stops or escalates. Failover requires exclusive leader fencing, lease expiry/revocation and verified handover. When Ruku returns, reconcile operations before taking control back. Never allow concurrent leaders to act on the same target.

Delegation records must specify: delegated principal, allowed actions and targets, policy/runbook hash, expiry, concurrency, maximum downtime budget, audit identity and revocation/fencing token. No generic delegation or inherited RED authority.

## Security, rollback and observability

- VOODOO denial/unavailability is a hard stop.
- Enforce immutable or tamper-evident event/decision logging with actor attribution.
- Test failure injection before activation: partial restart, Kato disconnect, split brain, lost Ruku, stale inventory, VOODOO denial, failed rollback and unknown provider state.
- Require measurable postflight checks, recovery time and data-loss budgets (RTO/RPO) for each target.
- For stateful systems distinguish traffic restoration, service recovery and **data restore**; snapshot existence does not establish recoverability.
- Escalate unconfirmed outcomes and recovery failures to Jan rather than silently repeating the operation.

## Open decisions — must resolve before implementation

1. Exact per-service GREEN allowlists and approved runbooks, maintenance/error budget, health thresholds, dependency freshness TTL.
2. AMBER categories, delegation scopes and who may authorize them in conflict with existing explicit-approval requirements.
3. Durable journal, distributed lease/fencing mechanism and failover timeouts.
4. Verified restore/rollback evidence, outage tolerance and escalation channel.
5. Approval workflow for amending current production-operation and authority-change restrictions.

## Rollout and acceptance criteria

Start with simulation/no-op + state-machine tests, then isolated staging tests after staging authorization, then policy/governance review. **Do not enable production automation or change existing gates without separate explicit approval.**

Acceptance evidence: no duplicate restart after lost ACK; deny on stale inventory/security veto; no split brain after leader handback; RED cannot execute without explicit operator authorization; audit traces contain every decision; verified recovery for each approved target.

## Failover scenario verification

The normative fault-injection and acceptance matrix for F01–F10 and T01–T10 is documented in [Failover scenarios v0](../operations/failover-scenarios-v0.md). It is a design/test specification only; passing results are not claimed and current production approval gates remain in force.

## Rollback

This change is documentation-only. Close the draft PR to reject the proposal; any future runtime deployment requires a separate reviewed rollback plan.