# Staging Readiness Gate v0

Date: 2026-08-20
Status: Candidate architecture note

## Context

PR #47 added a disabled/manual plan-only staging workflow and manifest validator. PR #48 reconciled that merge and documented the next readiness slice.

WB-0030 implements that readiness slice without crossing the remote-write boundary.

## Gate model

The readiness gate is a local validation layer over non-secret evidence. It treats missing or unknown evidence as a blocker.

The gate has two classes of requirements:

1. hard false flags that must remain false in this work block;
2. readiness statuses that must eventually be verified or approved before a future remote-write request.

## Hard false flags

- remote write requested: false;
- remote write allowed: false;
- production write allowed: false;
- plaintext secret values present: false.

## Future promotion statuses

- staging URL verified;
- staging path verified;
- secret aliases verified;
- rollback verified;
- effect verifier verified;
- fresh operator authorization approved.

## Security property

The current example is intentionally blocked. A passing readiness validator would mean the system is ready to request a separate remote-write authorization. It would not itself perform or authorize deployment.

## Boundary

No InterServer connection, provider mutation, DirectAdmin action, SSH/SFTP/rsync, DNS, mail, billing, VPS, WordPress, Nextcloud, production write, or plaintext-secret handling is introduced.
