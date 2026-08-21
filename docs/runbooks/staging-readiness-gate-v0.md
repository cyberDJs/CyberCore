# Staging Readiness Gate v0

Date: 2026-08-21
Work blocks: `WB-0030`, extended by `WB-0031`

## Purpose

Validate that CyberCore cannot proceed to a first live InterServer staging write until the required non-secret evidence contract is satisfied. WB-0031 extends the original gate with an explicit deployment-protocol / target-capability block.

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
- `production_document_root_excluded: VERIFIED`
- `deployment_protocol_status: VERIFIED`
- `deployment_protocol` must be an allowlisted local contract value: `SFTP` or `SSH`
- `target_capability_status: VERIFIED`
- `target_capability_reference: INTERSERVER_STAGING_TARGET_CAPABILITY_REFERENCE`
- `secret_alias_status: VERIFIED`
- `rollback_status: VERIFIED`
- `effect_verifier_status: VERIFIED`
- `operator_authorization_status: APPROVED`

The `blocked_until` list must also contain `deployment_protocol_status: VERIFIED` and `target_capability_status: VERIFIED` in addition to the existing gate statuses.

## Non-negotiable false flags

- `remote_write_requested: false`
- `remote_write_allowed: false`
- `production_write_allowed: false`
- `plaintext_secret_values_present: false`
- `capability_evidence_secret_values_recorded: false`
- `capability_evidence_remote_write_performed: false`

## Capability evidence boundary

A local evidence document may pass the closed schema only when the capability fields are set to their required values. That PASS verifies the **shape of the evidence contract only**. It is not proof that the real InterServer target supports the selected protocol, and it does not authorize a provider connection or deployment.

Real target capability remains `UNKNOWN_UNTIL_VERIFIED` until a later, separately authorized work block performs the permitted verification and records safe evidence without secret values.

## Stop line

Any `UNKNOWN`, unsupported protocol, missing capability block, missing `blocked_until` capability status, unexpected field, wrong scalar type, denied literal, remote-write claim, production-write claim, or plaintext-secret indicator keeps the gate blocked.

This runbook does not authorize InterServer access or remote writes.
