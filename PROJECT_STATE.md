# CyberCore Project State

_Last updated: 2026-08-21 20:52 CEST_

## Source of truth

- Repository: `cyberDJs/CyberCore`
- Stable branch: `main`
- Canonical product state: GitHub `main`
- Evidence/archive/collaboration layer: Google Drive `CyberCore/CASER-E`
- Active branch: `feat/wb-0031-runtime-gate-preflight`
- Active pull request: #51 — WB-0031 runtime gate preflight implementation
- Active artifact: `WB-0031 — Staging Runtime Gate Preflight`
- Active work block: `WB-0031 — Staging Runtime Gate Preflight`
- Last verified `main`: `4a1374cbef7d142f8386ea7774208effc05d54ec`
- Governance rule: no production mutation without explicit human approval
- CI policy: GitHub Actions verification is required before merge
- CodeQL policy: Advanced setup is verified; GitHub Default setup is disabled to avoid conflicting scans

## Current milestone

PR #50 reconciled PR #49 and started `WB-0031 — Staging Runtime Gate Preflight`; it merged into canonical `main` as `4a1374cbef7d142f8386ea7774208effc05d54ec`.

The active slice is PR #51, which implements the WB-0031 deployment-protocol / target-capability gate inside the existing fail-closed readiness validator. This slice remains local and non-mutating: it does not contact InterServer, read secret values, perform a staging remote write, or authorize production/provider mutation.

## Active objective

Continue the first safe CyberCore self-deployment loop for InterServer shared-hosting staging:

1. preserve accepted ADR-0006 staging-only boundary;
2. treat `WB-0030` as the canonical fail-closed readiness foundation;
3. implement `WB-0031` as a closed non-secret gate for target identity, deployment protocol/target capability, secret alias readiness, rollback proof, effect-verifier proof, and operator authorization references;
4. keep `remote_write_requested`, `remote_write_allowed`, and `production_write_allowed` false in this work block;
5. keep `staging_apply` blocked unless a later work block verifies all runtime gates and receives fresh explicit remote-write authorization;
6. use LG-0001/LG-0002 as read-only source-of-truth orchestration support, not as mutation authority.

## Current status

- Work block: `WB-0031` implementation active
- Branch: `feat/wb-0031-runtime-gate-preflight`
- Pull request: #51
- WB-0028 foundation / PR #39: merged as `4f582583789346724813a2c515fe30450c173b0c`
- ADR-0006 lifecycle status: Accepted
- ADR-0006 decision date: 2026-08-20
- ADR-0006 authority: Jan Kočí
- ADR-0006 decision state: `DECIDED`
- WB-0029 / PR #47: merged as `09750d7c5b2e49b9b4006c1288391d6d5c6066d5`
- PR #48 post-merge reconciliation: merged as `dd389e87eb2684a4c90a816d35c0472e0b5e1fee`
- WB-0030 / PR #49: merged as `2de294bb3334e4194769f3b883d58a2e5e3a8ea5`
- PR #50 post-merge reconciliation / WB-0031 kickoff: merged as `4a1374cbef7d142f8386ea7774208effc05d54ec`
- Deployment protocol/target capability: still `UNKNOWN_UNTIL_VERIFIED`; PR #51 validates the evidence shape, not the real provider capability
- Live InterServer staging deployment: blocked until target identity, deployment protocol/capability, secret, rollback, effect-verifier, and fresh explicit authorization gates pass
- Production/provider/DirectAdmin/SSH/DNS/mail/billing changes: none
- Secret values stored: none
- GitHub `main`: canonical product state
- Google Drive CASER-E: evidence/archive/collaboration layer only, not canonical product state

## Secret-handling boundary

Plaintext secrets are denied in:

- GitHub;
- Google Drive;
- ChatGPT Library;
- Slack;
- chat;
- CASER documents;
- ordinary evidence logs.

Actual replacement or deployment secrets may only be placed in an OS-backed secret store or an approved external vault after explicit approval. Evidence may record only safe references, aliases, provider names, scopes, timestamps, fingerprints/hashes where safe, owner/status fields, and verification state.

## Self-deployment boundary

The current self-deployment work is staging-only.

Allowed in WB-0031 / PR #51:

- closed non-secret readiness evidence for deployment protocol and target capability;
- local validation logic that fails closed when capability evidence is missing, unknown, unexpected, wrong-typed, or claims secret-value capture / remote write;
- tests for those fail-closed conditions;
- target-contract, work-block, state, and audit updates;
- no-remote-write validation artifacts.

Blocked without separate explicit approval:

- production deployment;
- DNS, mail, billing, DirectAdmin, VPS, WordPress, Nextcloud, or provider mutation;
- any live InterServer connection used to verify or mutate the target;
- live InterServer staging remote write;
- reading or storing plaintext secrets;
- creating, changing, or reading GitHub Environment secret values;
- treating target metadata as proof that deployment protocol/capability has been verified;
- executing `staging_apply` or equivalent remote mutation without all runtime gates and fresh explicit operator authorization.

## Recent completed state changes

### PR #47 — WB-0029 disabled/manual staging workflow validator

Merged into `main` as:

```text
09750d7c5b2e49b9b4006c1288391d6d5c6066d5
```

Delivered a plan-only staging manifest, fail-closed staging target and manifest validator, manual `workflow_dispatch` dry-run workflow, tests for blocking `staging_apply`, no-remote-write receipt semantics, runbook, and kickoff evidence.

### PR #48 — PR47 post-merge state reconciliation

Merged into `main` as:

```text
dd389e87eb2684a4c90a816d35c0472e0b5e1fee
```

Recorded PR #47 / WB-0029 as merged, closed stale superseded PRs #42 and #46, and added next-slice planning docs and remote-write gate checklist.

### PR #49 — WB-0030 staging readiness gate

Merged into `main` as:

```text
2de294bb3334e4194769f3b883d58a2e5e3a8ea5
```

Delivered a fail-closed staging readiness gate, closed readiness evidence schema, hardened YAML preflight, manual `workflow_dispatch` readiness validator, regression tests for fail-closed bypass channels, runbook, audit evidence, and no-remote-write receipt semantics.

Verification recorded in the merge commit:

- exact head `334189a867ec071b085465cd1340e51e459c4bf6`;
- CI #135 PASS;
- CodeQL #132 PASS;
- fresh Codex adversarial review: no major issues;
- all review threads resolved;
- manual AI review PASS.

### PR #50 — PR49 post-merge reconciliation and WB-0031 kickoff

Merged into `main` as:

```text
4a1374cbef7d142f8386ea7774208effc05d54ec
```

Recorded PR #49 / WB-0030 as canonical, defined WB-0031, and made deployment protocol / target capability an explicit runtime gate while keeping InterServer remote writes blocked.

Verification recorded in the merge commit:

- exact head `1f4e3544852a549a8f88ef14db4e35a305c15fcd`;
- CI #143 PASS;
- CodeQL #140 PASS;
- fresh Codex review: no major issues;
- all review threads resolved;
- manual AI review PASS.

## Current work block

### WB-0031 — Staging Runtime Gate Preflight

PR #51 implements the local fail-closed portion of this work block. The readiness document now has a dedicated `deployment_capability_readiness` mapping and the validator requires:

- `deployment_protocol_status: VERIFIED`;
- an explicitly allowlisted deployment protocol value;
- `target_capability_status: VERIFIED`;
- a fixed safe target-capability evidence reference;
- `capability_evidence_secret_values_recorded: false`;
- `capability_evidence_remote_write_performed: false`;
- matching deployment-protocol and target-capability entries in `blocked_until`.

The example remains intentionally blocked. Tests may construct a synthetic fully verified evidence document to prove the local validator can become ready while `remote_write_requested`, `remote_write_allowed`, and `production_write_allowed` remain false. This is not evidence that the real InterServer capability is verified and is not authority to connect or deploy.

## Security follow-up

- Six high-severity transitive `npm audit` findings remain deferred security debt in the isolated visual documentation toolchain.
- Provider credential-rotation verification remains an unresolved operational blocker until handled by a separately approved procedure without secret values in ordinary evidence stores.
- WB-0031 does not resolve those blockers; it keeps live staging deploy blocked behind target identity, deployment capability, secret, rollback, effect-verifier, and fresh authorization gates.

## Next action

Run exact-head hosted CI/CodeQL and fresh adversarial review for PR #51. Repair valid findings and stop at `READY_FOR_MERGE`. Do not perform any InterServer connection, live remote write, provider mutation, production mutation, DNS, mail, billing, DirectAdmin, VPS, WordPress, Nextcloud, or plaintext-secret handling.

<!-- CYBERCORE:CHECKPOINT:START -->
<!-- CYBERCORE:PROJECT-STATE-CHECKPOINT:pr51-wb0031-runtime-gate-preflight -->
## Manual repository checkpoint

- Generated: `2026-08-21T20:52:00+02:00`
- Branch: `feat/wb-0031-runtime-gate-preflight`
- Pull request: #51
- Active artifact: `WB-0031`
- Active work block: `WB-0031 — Staging Runtime Gate Preflight`
- Last verified main: `4a1374cbef7d142f8386ea7774208effc05d54ec`
- Test evidence: exact-head hosted CI/CodeQL and fresh review required before Ready for Review
- Project Kernel: present
- Project State: PR #50 merged; WB-0031 implementation active in PR #51; InterServer remote-write and production gates remain blocked
<!-- CYBERCORE:CHECKPOINT:END -->
