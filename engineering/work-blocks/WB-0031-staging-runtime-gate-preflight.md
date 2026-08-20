# WB-0031 — Staging Runtime Gate Preflight

## Status

Active candidate.

## Canonical base

- Repository: `cyberDJs/CyberCore`
- Base: `main@2de294bb3334e4194769f3b883d58a2e5e3a8ea5`
- Predecessor: `WB-0030 — Staging Readiness Gate`, merged through PR #49

## Goal

Prepare the evidence, authorization, rollback, and verification requirements for a future first live staging remote-write work block without performing any remote write.

## Scope

Allowed:

- non-secret documentation;
- state and audit evidence;
- closed checklist for staging target identity evidence;
- closed checklist for secret alias readiness evidence without secret values;
- rollback proof requirements;
- effect-verifier proof requirements;
- operator authorization requirements for a later remote-write work block;
- tests or validators only if they remain local and non-mutating.

Out of scope:

- InterServer SSH/SFTP/API/DirectAdmin interaction;
- live staging remote write;
- production write or production promotion;
- DNS, mail, billing, VPS, WordPress, Nextcloud, or provider mutation;
- reading, storing, printing, or transmitting plaintext secrets;
- creating or changing GitHub Environment secrets;
- treating aliases or documentation as proof that a secret value exists.

## Required evidence shape

A future remote-write request must have safe evidence for:

1. staging URL identity;
2. staging filesystem path identity;
3. production document root exclusion;
4. required secret aliases present without value disclosure;
5. rollback method and rollback test status;
6. effect verifier checks;
7. fresh operator authorization reference;
8. stop-line acknowledgement for production and provider mutation.

## Exit criteria

This work block can stop at `READY_FOR_MERGE` when:

- PR #49 post-merge state is reconciled;
- `WB-0031` is recorded as the active candidate;
- the new preflight requirements remain non-secret and non-mutating;
- hosted CI and CodeQL pass on the exact head;
- manual review passes;
- no unresolved review threads remain.

Merge still requires explicit operator authorization from Jan Kočí.
