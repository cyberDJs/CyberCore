# ADR Identifier Reconciliation — 2026-08-19

Status: CANDIDATE / POST-MERGE CORRECTION
Scope: documentation, governance identifiers, and source-of-truth state only

## Trigger

After PR #39, PR #40, and PR #41 landed, canonical `main` contained two different architecture decisions using the identifier `ADR-0005`:

- accepted `ADR-0005 — LangGraph as Optional Orchestration Runtime`, introduced by PR #40;
- proposed `ADR-0005 — Self-Deployment Staging Boundary`, introduced by PR #39.

The duplicate identifier makes references ambiguous and violates the purpose of an ADR sequence even though the decision contents themselves do not conflict.

## Resolution

- Preserve `ADR-0005` for the already accepted LangGraph orchestration decision.
- Renumber the self-deployment staging-boundary proposal to `ADR-0006`.
- Rename the self-deployment ADR file accordingly.
- Update all canonical self-deployment references from `ADR-0005` to `ADR-0006`.
- Reconcile `.cybercore/project.yaml` and `PROJECT_STATE.md` to the actual post-merge state after PR #39, PR #40, and PR #41.

## Authority and semantics

This correction does **not** accept ADR-0006. Its status remains Proposed.

This correction does **not** change the staging-boundary policy, authorize a live InterServer write, authorize production mutation, change secret-storage policy, or grant LangGraph/provider execution authority.

## Verified basis

- Current canonical main at correction start: `2cdfe5ffd1f6cd16e5a7a64cbc2c5f82c364e187`.
- PR #39 merged as `4f582583789346724813a2c515fe30450c173b0c`; its final CI #58 and CodeQL #55 passed.
- PR #40 merged as `56ccb7b8ea3871b592b79b2601da29122e677183`; its final CI/CodeQL and Python 3.11–3.14 gates passed.
- PR #41 merged as `2cdfe5ffd1f6cd16e5a7a64cbc2c5f82c364e187`; exact-head CI #69 and CodeQL #66 passed, with 244 tests passing on Python 3.11.
- Repository search showed the duplicate self-deployment ADR plus self-deployment references in `PROJECT_STATE.md` and `engineering/work-blocks/WB-0028-self-deployment-staging-loop-v0.md`.

## Rollback

The correction is documentation/state-only. Rollback is a normal revert of the corrective commit. Reintroducing duplicate ADR identifiers is not recommended; if numbering policy changes later, both ADRs and all references must be migrated together.
