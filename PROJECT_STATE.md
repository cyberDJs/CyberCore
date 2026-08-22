# CyberCore Project State

_Last updated: 2026-08-22 02:08 CEST_

## Source of truth

- Repository: `cyberDJs/CyberCore`
- Stable branch: `main`
- Canonical product state: GitHub `main`
- Evidence/archive/collaboration layer: Google Drive `CyberCore/CASER-E`
- Active branch: `docs/wb-0032-capability-discovery`
- Active pull request: #52 — PR51 reconciliation and WB-0032 kickoff
- Active artifact: `WB-0032 — InterServer Staging Capability Discovery`
- Active work block: `WB-0032 — InterServer Staging Capability Discovery`
- Last verified `main`: `d4ac1c0fa8139cf5fb6a45e81d16a83c912bf684`
- Governance rule: no production mutation without explicit human approval
- CI policy: GitHub Actions verification is required before merge
- CodeQL policy: Advanced setup is verified; GitHub Default setup is disabled to avoid conflicting scans

## Current milestone

PR #51 implemented `WB-0031 — Staging Runtime Gate Preflight` and was squash-merged into canonical `main` as `d4ac1c0fa8139cf5fb6a45e81d16a83c912bf684`.

The active slice is PR #52. It reconciles canonical state after PR #51 and defines `WB-0032 — InterServer Staging Capability Discovery`. This kickoff slice is repository-only: it does not contact InterServer, read secret values, perform a staging remote write, or authorize production/provider mutation.

## Active objective

Continue the first safe CyberCore self-deployment loop for InterServer shared-hosting staging:

1. preserve accepted ADR-0006 staging-only boundary;
2. treat `WB-0030` and merged `WB-0031` as the canonical fail-closed readiness/preflight foundation;
3. define `WB-0032` as the work block that will convert the remaining InterServer runtime unknowns into safe evidence;
4. keep PR #52 / WB-0032 Phase A repository-only with no live provider contact;
5. require a fresh explicit operator authorization before WB-0032 Phase B performs any live read-only InterServer capability discovery;
6. keep `remote_write_requested`, `remote_write_allowed`, and `production_write_allowed` false throughout WB-0032;
7. keep `staging_apply` blocked until a later work block verifies all runtime gates and receives fresh explicit remote-write authorization;
8. use LG-0001/LG-0002 as read-only source-of-truth orchestration support, not as mutation authority.

## Current status

- Work block: `WB-0032` definition/kickoff active
- Branch: `docs/wb-0032-capability-discovery`
- Pull request: #52
- WB-0028 foundation / PR #39: merged as `4f582583789346724813a2c515fe30450c173b0c`
- ADR-0006 lifecycle status: Accepted
- ADR-0006 decision date: 2026-08-20
- ADR-0006 authority: Jan Kočí
- ADR-0006 decision state: `DECIDED`
- WB-0029 / PR #47: merged as `09750d7c5b2e49b9b4006c1288391d6d5c6066d5`
- PR #48 post-merge reconciliation: merged as `dd389e87eb2684a4c90a816d35c0472e0b5e1fee`
- WB-0030 / PR #49: merged as `2de294bb3334e4194769f3b883d58a2e5e3a8ea5`
- PR #50 post-merge reconciliation / WB-0031 kickoff: merged as `4a1374cbef7d142f8386ea7774208effc05d54ec`
- WB-0031 / PR #51: merged as `d4ac1c0fa8139cf5fb6a45e81d16a83c912bf684`
- Deployment protocol/target capability: still `UNKNOWN_UNTIL_VERIFIED`; WB-0031 validates evidence shape, not the real provider capability
- Live InterServer capability discovery: blocked until a separate fresh read-only operator authorization is granted
- Live InterServer staging deployment: blocked until target identity, deployment protocol/capability, secret, rollback, effect-verifier, and fresh explicit remote-write authorization gates pass
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

Allowed in WB-0032 Phase A / PR #52:

- post-merge reconciliation for PR #51;
- non-secret work-block definition, project state, and audit evidence;
- explicit discovery questions for target identity, deployment capability, secret-alias readiness, rollback, effect verification, and credential-rotation operational state;
- a written separate authority gate for a later read-only provider discovery;
- no-remote-write planning artifacts.

Blocked unconditionally in PR #52:

- any live InterServer connection, including read-only SSH/SFTP/API/DirectAdmin capability probes;
- production deployment;
- DNS, mail, billing, DirectAdmin, VPS, WordPress, Nextcloud, or provider mutation;
- live InterServer staging remote write;
- reading or storing plaintext secrets in ordinary evidence channels;
- creating, changing, or reading GitHub Environment secret values;
- credential rotation;
- treating target metadata, aliases, documentation, or synthetic evidence as proof that real provider capability exists;
- executing `staging_apply` or equivalent remote mutation.

No approval may broaden PR #52 itself beyond this repository-only Phase A scope. A later WB-0032 Phase B is a separate execution step and may begin only after a fresh explicit authorization for read-only/non-mutating discovery. Phase B cannot authorize upload, overwrite, deletion, chmod/chown, symlink creation, credential rotation, provider configuration changes, staging remote write, or production access.

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

### PR #51 — WB-0031 staging runtime gate preflight

Merged into `main` as:

```text
d4ac1c0fa8139cf5fb6a45e81d16a83c912bf684
```

Delivered the local fail-closed deployment-protocol / target-capability preflight, closed evidence semantics, hardened target YAML parsing, regression coverage for duplicate/merge/anchor/alias/recursion/depth bypasses, and preserved the invariant that a local readiness PASS grants no remote-write authority.

Verification recorded in the merge commit:

- exact head `aa02ea82b7e86f851b60386b1d07f97d149912f8`;
- CI #166 PASS;
- CodeQL #163 PASS;
- fresh Codex adversarial review: no major issues;
- all review threads resolved;
- manual AI review PASS.

## Current work block

### WB-0032 — InterServer Staging Capability Discovery

PR #52 defines WB-0032 and reconciles PR #51. The work block separates repository-only kickoff from later live read-only discovery.

The later discovery must establish real evidence for:

- non-production staging URL/domain identity;
- staging path/document-root identity and production exclusion;
- available deployment protocol(s) and target capability;
- least-privilege deployment-user scope;
- required secret-alias readiness without value disclosure;
- rollback capability;
- effect-verifier capability;
- credential-rotation operational state without credential values.

Before the first live InterServer contact, WB-0032 requires a fresh explicit authorization naming the InterServer staging scope and read-only/non-mutating access. Upload, overwrite, delete, chmod/chown, symlink creation, credential rotation, provider configuration change, and production access remain prohibited.

## Security follow-up

- Six high-severity transitive `npm audit` findings remain deferred security debt in the isolated visual documentation toolchain.
- Provider credential-rotation verification remains an unresolved operational blocker until handled by a separately approved procedure without secret values in ordinary evidence stores.
- WB-0032 may record credential-rotation operational state during an approved read-only discovery, but does not authorize rotation itself.
- Live staging deploy remains blocked behind target identity, deployment capability, secret readiness, rollback, effect-verifier, and fresh remote-write authorization gates.

## Next action

Run exact-head hosted CI/CodeQL and fresh adversarial review for PR #52. Repair valid findings and stop at `READY_FOR_MERGE`. Do not perform any InterServer connection, live remote write, provider mutation, production mutation, DNS, mail, billing, DirectAdmin, VPS, WordPress, Nextcloud, credential rotation, or plaintext-secret handling.

<!-- CYBERCORE:CHECKPOINT:START -->
<!-- CYBERCORE:PROJECT-STATE-CHECKPOINT:pr52-wb0032-capability-discovery -->
## Manual repository checkpoint

- Generated: `2026-08-22T02:08:00+02:00`
- Branch: `docs/wb-0032-capability-discovery`
- Pull request: #52
- Active artifact: `WB-0032`
- Active work block: `WB-0032 — InterServer Staging Capability Discovery`
- Last verified main: `d4ac1c0fa8139cf5fb6a45e81d16a83c912bf684`
- Test evidence: exact-head hosted CI/CodeQL and fresh review required before Ready for Review
- Project Kernel: present
- Project State: PR #51 merged; WB-0032 definition/kickoff active in PR #52; live InterServer discovery requires separate explicit read-only authorization; remote-write and production gates remain blocked
<!-- CYBERCORE:CHECKPOINT:END -->
