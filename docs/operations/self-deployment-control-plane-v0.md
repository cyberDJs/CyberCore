# Self-Deployment Control Plane v0

Date: 2026-08-19
Work block: `WB-0028`

## Control-plane states

```text
REQUESTED
-> PLANNED
-> PREFLIGHT_PASSED
-> AUTHORIZED_FOR_STAGING
-> STAGING_DEPLOYED
-> EFFECT_VERIFIED
-> RECEIPT_RECORDED
```

Failure states:

```text
BLOCKED
FAILED
ROLLED_BACK
UNVERIFIED
```

## Responsibilities

| Component | Responsibility |
|---|---|
| CASER | run/session control, state, checkpoints |
| CASER-SOURCER | provenance, evidence classification, source-of-truth freshness |
| V-ONE / operator authority | what is allowed |
| CASTER-MINAL / runner | execution when available |
| Verifier / QA | actual effect verification |

## Minimum gate model

- Repository mutation: allowed on non-canonical branch after preflight.
- PR merge: explicit Jan Kočí authorization plus required checks.
- Staging remote write: explicit Jan Kočí authorization plus target preflight.
- Production mutation: separate production MOP and explicit approval.

## v0 limitation

This control plane currently exists as a documented contract. A later work block must implement a manifest validator and manually triggered staging workflow before any live deployment.