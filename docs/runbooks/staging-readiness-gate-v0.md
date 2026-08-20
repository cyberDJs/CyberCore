# Staging Readiness Gate v0

Date: 2026-08-20
Work block: `WB-0030`

## Purpose

Validate that CyberCore cannot proceed to first live InterServer staging write until the required non-secret evidence is present.

## Command

```text
python scripts/validate_staging_readiness.py --expect-blocked
```

The example readiness file is intentionally blocked. The command succeeds only when the gate remains blocked.

## Readiness evidence file

```text
.cybercore/deploy/readiness/interserver-staging-readiness.example.yaml
```

## Required verified fields before any future remote-write request

- `staging_url_status: VERIFIED`
- `staging_path_status: VERIFIED`
- `secret_alias_status: VERIFIED`
- `rollback_status: VERIFIED`
- `effect_verifier_status: VERIFIED`
- `operator_authorization_status: APPROVED`

## Non-negotiable false flags

- `remote_write_requested: false`
- `remote_write_allowed: false`
- `production_write_allowed: false`
- `plaintext_secret_values_present: false`

## Stop line

Any `UNKNOWN`, denied literal, remote-write claim, production-write claim, or plaintext-secret indicator keeps the gate blocked.

This runbook does not authorize remote writes.
