# Self-Deployment Target Registry v0

Date: 2026-08-19
Work block: `WB-0028`

## Purpose

The target registry stores non-secret deployment target metadata for CyberCore self-deployment.

## Current target

```text
interserver-shared-hosting-staging
```

## Allowed fields

- target id;
- provider;
- environment class;
- non-secret URL placeholders;
- non-secret path labels/placeholders;
- deployment method status;
- secret aliases;
- preflight requirements;
- rollback mode;
- evidence requirements.

## Denied fields

- passwords;
- API tokens;
- SSH private keys;
- TOTP seeds;
- cookies;
- recovery codes;
- production credential values.

## Lifecycle

```text
DRAFT
-> TARGET_IDENTIFIED
-> CAPABILITY_VERIFIED
-> SECRETS_ALIASED
-> ROLLBACK_VERIFIED
-> READY_FOR_DRY_RUN
-> READY_FOR_STAGING_APPLY
```

## Current lifecycle state

`DRAFT`

Reason: staging URL/path/deployment method/rollback/effect verifier are not yet verified.