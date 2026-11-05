# CASER v4.1 — exact-head CI evidence gate

Status: candidate / opt-in. Tracking: #136. This is a pure evidence
validator, **not** a GitHub client, a review verdict, a branch-protection
replacement, or authority to merge.

## Contract

`cybercore.caser41_ci_evidence.evaluate_ci_evidence` accepts an exact 40-character
lowercase commit SHA, a snapshot of named checks, and a nonempty required-check
set. The default set covers CI quality/package, four Python test jobs, CodeQL,
and the real CyberHIVE contract workflow.

`CheckObservation.commit_sha` MUST originate from an authenticated provider
adapter that verifies the result belongs to the exact PR head. Do not copy
the expected SHA into arbitrary returned observations to make them pass.

Reject unknown/missing or duplicate required contexts, wrong SHA, pending
jobs and all conclusions other than explicit `success`. Extra check contexts
do not satisfy required checks; external branch rules may require additional
contexts not captured by this default. Callers must verify current branch
protection policy and exact PR head **again** immediately before merge.

## Threats and boundaries

- This evaluator only validates supplied data; forged observations can pass
  unless their origin and integrity are established by the caller.
- The current GitHub workflow result may turn green before all required jobs
  and branch protection status contexts have propagated.
- Human review, resolved comments, expiry of approvals, CodeQL findings,
  runtime behavior, production identity, and CASER policy gates are separate.
- Never treat `GateVerdict.passed` as merge or production approval.
- A paused or interrupted run must re-read the canonical PR head and statuses;
  old snapshots cannot be replayed as fresh authorization.

## Regression coverage

Tests demonstrate rejection of missing matrix jobs, stale SHA, duplicate
contexts, in-progress and failing jobs, empty requirements and invalid SHA.
No runtime services, credentials or CI configuration are modified.

## Rollback

Stop calling the optional evaluator; preserve existing workflow checks and
security policy. The module introduces no persistent state or migrations.
