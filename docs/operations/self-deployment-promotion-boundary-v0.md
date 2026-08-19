# Self-Deployment Promotion Boundary v0

Date: 2026-08-19
Work block: `WB-0028`

## Rule

Staging success is not production approval.

## Promotion ladder

```text
PLAN_ONLY
-> DRY_RUN
-> STAGING_APPLY
-> EFFECT_VERIFIED_STAGING
-> PRODUCTION_MOP_REQUIRED
```

## Production requirements

Production promotion requires a separate future workflow with:

- explicit human approval;
- backup/restore evidence;
- production MOP;
- rollback method;
- effect verifier;
- receipt;
- post-deploy observation.

## Current state

WB-0028 stops before production promotion.