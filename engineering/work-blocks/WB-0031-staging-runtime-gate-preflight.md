# WB-0031 — Staging Runtime Gate Preflight

## Status

Implementation active in PR #51.

## Canonical base

- Repository: `cyberDJs/CyberCore`
- Base: `main@4a1374cbef7d142f8386ea7774208effc05d54ec`
- Active branch: `feat/wb-0031-runtime-gate-preflight`
- Pull request: #51
- Predecessor: PR #50, which reconciled PR #49 / WB-0030 and started WB-0031

## Goal

Implement the local fail-closed evidence, authorization, rollback, deployment-capability, and verification gate for a future first live staging remote-write work block without performing any InterServer connection or remote write.

## Scope

Allowed:

- non-secret documentation, state, and audit evidence;
- closed staging-target identity evidence requirements;
- closed deployment-protocol and target-capability evidence requirements;
- closed secret-alias readiness evidence without secret values;
- rollback proof requirements;
- effect-verifier proof requirements;
- operator authorization requirements for a later remote-write work block;
- local validators and regression tests that remain non-mutating.

Out of scope:

- InterServer SSH/SFTP/API/DirectAdmin interaction;
- any live provider capability probe;
- live staging remote write;
- production write or production promotion;
- DNS, mail, billing, VPS, WordPress, Nextcloud, or provider mutation;
- reading, storing, printing, or transmitting plaintext secrets;
- creating, changing, or reading GitHub Environment secret values;
- treating target metadata as proof that a deployment protocol/capability has been verified;
- treating aliases, documentation, or synthetic test evidence as proof that a real secret value or provider capability exists.

## Implemented evidence contract

A future remote-write request must have safe evidence for:

1. staging URL identity;
2. staging filesystem path identity;
3. production document root exclusion;
4. `deployment_protocol_status: VERIFIED`;
5. a deployment protocol from the closed local allowlist;
6. `target_capability_status: VERIFIED` plus the fixed safe capability reference;
7. capability evidence that records no secret values and performed no remote write;
8. required secret aliases present without value disclosure;
9. rollback method and rollback test status;
10. effect verifier checks;
11. fresh operator authorization reference;
12. stop-line acknowledgement for production and provider mutation.

`blocked_until` must contain both deployment-protocol and target-capability requirements. Missing, duplicate, unexpected, wrong-typed, or extra evidence fails closed.

## Safety invariant

Even a synthetic fully verified readiness document must keep:

- `remote_write_requested: false`;
- `remote_write_allowed: false`;
- `production_write_allowed: false`;
- `capability_evidence_remote_write_performed: false`;
- `capability_evidence_secret_values_recorded: false`.

A local PASS means only that the evidence document satisfies the closed contract. It does not prove the real InterServer target is capable and does not authorize `staging_apply`.

## Exit criteria

This work block can stop at `READY_FOR_MERGE` when:

- PR #50 post-merge state is reconciled to `main@4a1374cbef7d142f8386ea7774208effc05d54ec`;
- PR #51 is the active implementation slice;
- deployment protocol / target capability are part of the readiness schema and machine-readable `blocked_until` contract;
- regression tests cover missing/unknown/extra capability evidence, unsupported protocol values, exact types, and secret/remote-write claims;
- hosted CI and CodeQL pass on the exact head;
- fresh adversarial Codex review and manual AI review pass;
- no unresolved material review threads remain.

Merge still requires separate explicit operator authorization from Jan Kočí.
