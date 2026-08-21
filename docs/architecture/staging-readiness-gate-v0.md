# Staging Readiness Gate v0

Date: 2026-08-21
Status: Candidate architecture note, extended by WB-0031

## Context

PR #47 added a disabled/manual plan-only staging workflow and manifest validator. PR #48 reconciled that merge. WB-0030 then introduced the local fail-closed readiness evidence validator without crossing the remote-write boundary.

WB-0031 extends that readiness contract with an explicit deployment-protocol / target-capability gate. The extension remains local and non-mutating; it does not verify the real InterServer target by connecting to it.

## Gate model

The readiness gate is a local validation layer over non-secret evidence. Missing, unknown, unexpected, or wrong-typed evidence is a blocker.

The gate has three classes of requirements:

1. hard false flags that must remain false in this work block;
2. closed target, deployment-capability, secret-alias, rollback, and effect-verifier statuses that must be verified before a later remote-write request can be considered;
3. fresh operator authorization that must be approved separately from the local evidence validation.

## Hard false flags

- remote write requested: false;
- remote write allowed: false;
- production write allowed: false;
- plaintext secret values present: false;
- capability evidence secret values recorded: false;
- capability evidence remote write performed: false.

## Deployment capability contract

The readiness document contains a closed `deployment_capability_readiness` mapping. It requires:

- `deployment_protocol_status: VERIFIED`;
- `deployment_protocol` from the local allowlist (`SFTP` or `SSH`);
- `target_capability_status: VERIFIED`;
- `target_capability_reference: INTERSERVER_STAGING_TARGET_CAPABILITY_REFERENCE`;
- `capability_evidence_secret_values_recorded: false`;
- `capability_evidence_remote_write_performed: false`.

`blocked_until` must include both `deployment_protocol_status: VERIFIED` and `target_capability_status: VERIFIED`.

The protocol allowlist is a local contract constraint, not a statement that the real provider currently supports a selected protocol. The staging target contract remains `capability_status: UNKNOWN_UNTIL_VERIFIED` until a later separately authorized verification step establishes real target capability.

## Future promotion statuses

- staging URL verified;
- staging path verified;
- production document root exclusion verified;
- deployment protocol verified;
- staging target capability verified;
- secret aliases verified;
- rollback verified;
- effect verifier verified;
- fresh operator authorization approved.

## Security property

The current example is intentionally blocked. A synthetic or local passing readiness document means only that the evidence document satisfies the closed schema and status contract. It does **not** prove real InterServer capability and does not itself perform or authorize deployment.

Real provider capability verification and any later `staging_apply` remain separate authority gates.

## Boundary

No InterServer connection, provider mutation, DirectAdmin action, SSH/SFTP execution, DNS, mail, billing, VPS, WordPress, Nextcloud, production write, or plaintext-secret handling is introduced by WB-0031.
