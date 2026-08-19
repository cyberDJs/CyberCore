# Self-Deployment Evidence Receipt v0

Date: 2026-08-19
Work block: `WB-0028`

## Purpose

Define the minimum non-secret receipt that a future staging deployment run must produce.

## Receipt fields

```yaml
version: 1
receipt_type: staging_deploy_receipt
run_id: TBD
created_at: TBD
repository: cyberDJs/CyberCore
source_branch: TBD
source_commit: TBD
target_id: interserver-shared-hosting-staging
deploy_mode: plan_only | dry_run | staging_apply
operator_authorization_reference: TBD
artifact_identity: TBD
rollback_mode: TBD
verifier:
  status: PASS | FAIL | UNKNOWN
  checked_at: TBD
  evidence: TBD
outcome: VERIFIED | UNVERIFIED | FAILED | ROLLED_BACK | BLOCKED
secret_values_recorded: false
```

## Rules

- A deploy execution receipt is not effect verification.
- A staging URL health check is required before `VERIFIED`.
- Missing verifier evidence means `UNVERIFIED`.
- Any secret value in a receipt is a security failure.
- Production promotion requires a separate receipt and approval path.

## Current state

No live staging deployment receipt exists yet. This document defines the contract for the future runner.