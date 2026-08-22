# CyberCore Project State

_Last updated: 2026-08-22 04:48 CEST_

## Source of truth

- Repository: `cyberDJs/CyberCore`
- Stable branch: `main`
- Canonical product state: GitHub `main`
- Evidence/archive/collaboration layer: Google Drive `CyberCore/CASER-E`
- Active branch: `docs/wb-0032-phase-b-preflight`
- Active pull request: #53 — WB-0032 Phase B documentation/preflight
- Active artifact: `WB-0032 — InterServer Staging Capability Discovery`
- Active work block: `WB-0032 — InterServer Staging Capability Discovery`
- Last verified `main`: `304f4234e4f52c2375d904b45d1ed0c4fe31511c`
- Governance rule: provider mutation, secret mutation, staging-apply, and production mutation authority remains reserved to explicit Jan Kočí authorization
- CI policy: GitHub Actions verification is required before merge
- CodeQL policy: Advanced setup is verified; GitHub Default setup is disabled to avoid conflicting scans

## Current milestone

PR #52 defined `WB-0032 — InterServer Staging Capability Discovery`, reconciled PR #51, and was squash-merged into canonical `main` as `304f4234e4f52c2375d904b45d1ed0c4fe31511c`.

Jan Kočí subsequently granted the separate WB-0032 Phase B authority required by the canonical work block: **InterServer staging only, read-only/non-mutating capability discovery**, including read-only SSH/SFTP/DirectAdmin/provider probes as needed. Upload, overwrite, deletion, chmod/chown, symlink creation, provider configuration changes, credential creation/rotation/reset, staging remote write, and production access remain prohibited.

The active slice is PR #53. It turns that authority into an explicit fail-closed discovery procedure based on current InterServer and DirectAdmin documentation before authenticated provider contact.

## Active objective

Continue the first safe CyberCore self-deployment loop for InterServer shared-hosting staging:

1. preserve accepted ADR-0006 staging-only boundary;
2. treat merged WB-0030 and WB-0031 as the canonical fail-closed readiness/runtime-preflight foundation;
3. treat merged PR #52 as the canonical WB-0032 definition and authority boundary;
4. execute WB-0032 Phase B only within Jan Kočí's current read-only/non-mutating authorization;
5. use an explicit semantic endpoint/command allowlist rather than assuming `GET == safe`;
6. independently gate response sensitivity so a non-mutating endpoint is still blocked when it may expose secret/session material;
7. keep real provider capability `UNKNOWN_UNTIL_VERIFIED` until observed from a network-capable, credential-safe runtime;
8. keep `remote_write_requested`, `remote_write_allowed`, and `production_write_allowed` false throughout WB-0032;
9. keep `staging_apply` blocked until a later work block verifies all runtime gates and receives fresh explicit Jan Kočí remote-write authorization;
10. use LG-0001/LG-0002 as read-only source-of-truth orchestration support, not mutation authority.

## Current status

- Work block: `WB-0032` Phase B documentation/preflight active
- Branch: `docs/wb-0032-phase-b-preflight`
- Pull request: #53
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
- WB-0032 definition/kickoff / PR #52: merged as `304f4234e4f52c2375d904b45d1ed0c4fe31511c`
- WB-0032 Phase B read-only authority: granted by Jan Kočí on 2026-08-22
- InterServer REST/OpenAPI documentation: reviewed
- InterServer MCP documentation: reviewed
- DirectAdmin API documentation: reviewed
- Deployment protocol/target capability: `UNKNOWN_UNTIL_VERIFIED`
- Exact staging service/path identity: `UNKNOWN_UNTIL_VERIFIED`
- Live InterServer discovery: authorized, but no authenticated provider response has yet been observed in this execution environment
- Isolated-runner public `/apiv2/ping` attempt: runner DNS/network unavailable; this is not evidence that InterServer is down
- Live InterServer staging deployment: blocked until target identity, deployment protocol/capability, secret readiness, rollback, effect-verifier, and fresh explicit Jan Kočí remote-write authorization gates pass
- Provider/DirectAdmin/SSH/DNS/mail/billing mutation: none
- Remote staging writes: none
- Production access/mutation: none
- Secret values stored in ordinary evidence: none
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

Existing credentials may be consumed only inside an approved runtime/secret-handling path needed for the authorized read-only probe. Evidence may record only safe references, aliases, provider names, scopes, timestamps, fingerprints/hashes where safe, owner/status fields, and verification state.

If an endpoint's response surface may expose credential/session material and cannot be bounded before invocation, the endpoint remains blocked rather than relying on post-hoc redaction.

## Self-deployment boundary

The current self-deployment work is staging-only.

Allowed in WB-0032 Phase B under the current Jan Kočí authority:

- current InterServer/DirectAdmin documentation inspection;
- `GET /apiv2/ping` and `GET /apiv2/info` public probes;
- authenticated `GET /apiv2/websites` to enumerate owned webhosting candidates;
- `GET /apiv2/websites/{id}/reverse_dns` only after an unambiguous candidate staging service is identified;
- InterServer MCP discovery only after the exact tool schema and read-only scope are inspected;
- target DirectAdmin `/static/swagger.json` inspection after target identity is established;
- documented read-only DirectAdmin API calls, preferring `/api/...`, with `CMD_API_SHOW_DOMAINS` as a documented legacy fallback where needed;
- minimal SSH/SFTP read-only metadata inspection only when needed to prove the staging document root and production-path exclusion;
- non-secret capability/evidence recording.

Blocked throughout WB-0032:

- any `POST`, `PATCH`, `PUT`, or `DELETE` InterServer API operation;
- any endpoint or command with unclear mutability;
- `GET /apiv2/websites/{id}` until its full response surface is independently proven free of secret/session material for the intended use;
- auto-login/session generation such as `/websites/{id}/login`;
- welcome-email resend endpoints;
- backup creation/download operations unless separately re-reviewed and explicitly needed for metadata only;
- production deployment or production content traversal/read;
- DNS, mail, billing, DirectAdmin, VPS, WordPress, Nextcloud, or provider mutation;
- live InterServer staging remote write;
- upload, overwrite, delete, mkdir/touch/cp/mv/rm, chmod/chown, symlink creation/replacement;
- reading or storing plaintext secrets in ordinary evidence channels;
- creating/changing/rotating/resetting credentials;
- treating documentation, aliases, synthetic tests, or failed local networking as proof of real provider capability;
- executing `staging_apply` or equivalent remote mutation.

Phase B authority cannot authorize mutation. A later staging-write work block requires a fresh, separate Jan Kočí remote-write authorization.

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

### PR #52 — WB-0032 definition and kickoff

Merged into `main` as:

```text
304f4234e4f52c2375d904b45d1ed0c4fe31511c
```

Reconciled PR #51, defined WB-0032's two-phase model, and established the fresh Jan Kočí authority gate required before Phase B read-only provider discovery. It did not perform or authorize staging writes or production/provider mutation.

Verification recorded before merge:

- exact head `ed77854c4cbf128f9c2bcc4c8d8f09eb3d855adc`;
- CI #176 PASS;
- CodeQL #173 PASS;
- fresh Codex adversarial review: no major issues;
- all review threads resolved;
- manual AI review PASS.

## Current work block

### WB-0032 — InterServer Staging Capability Discovery

PR #53 is the active documentation/preflight slice for the separately authorized Phase B.

The read-only discovery must establish real evidence for:

- non-production staging URL/domain identity;
- staging path/document-root identity and production exclusion without production-content traversal;
- available deployment protocol(s) and target capability;
- least-privilege deployment-user scope;
- required secret-alias readiness without value disclosure in evidence;
- rollback capability;
- effect-verifier capability;
- credential-rotation operational state without performing rotation.

The current authorization permits the bounded read-only discovery but cannot be interpreted as authority for `staging_apply`, upload, file creation/modification, credential rotation, provider setting changes, or production access.

## Security follow-up

- Six high-severity transitive `npm audit` findings remain deferred security debt in the isolated visual documentation toolchain.
- Provider credential-rotation verification remains an unresolved operational blocker until handled by a separately approved procedure without secret values in ordinary evidence stores.
- WB-0032 may record credential-rotation operational state during the approved read-only discovery, but does not authorize rotation itself.
- Live staging deploy remains blocked behind target identity, deployment capability, secret readiness, rollback, effect-verifier, and fresh Jan Kočí remote-write authorization gates.

## Next action

Complete exact-head CI/CodeQL and adversarial review for PR #53. Repair valid findings. Then run the authorized Phase B discovery from a network-capable runtime with an existing approved credential path, following the explicit semantic allowlist and response-sensitivity gate. Keep all real provider fields `UNKNOWN_UNTIL_VERIFIED` until observed.

Do not perform any staging write, production access/mutation, provider mutation, credential creation/rotation/reset, or plaintext-secret persistence.

<!-- CYBERCORE:CHECKPOINT:START -->
<!-- CYBERCORE:PROJECT-STATE-CHECKPOINT:pr53-wb0032-phase-b-preflight -->
## Manual repository checkpoint

- Generated: `2026-08-22T04:48:00+02:00`
- Branch: `docs/wb-0032-phase-b-preflight`
- Pull request: #53
- Active artifact: `WB-0032`
- Active work block: `WB-0032 — InterServer Staging Capability Discovery`
- Last verified main: `304f4234e4f52c2375d904b45d1ed0c4fe31511c`
- Phase B authority: explicit Jan Kočí read-only/non-mutating InterServer staging discovery authorization granted
- Provider capability: `UNKNOWN_UNTIL_VERIFIED`
- Remote write allowed: false
- Production write allowed: false
- Secret values recorded: false
- Project Kernel: present
- Project State: PR #52 merged; PR #53 active; WB-0032 Phase B authorized and preflighted; live provider evidence still pending a network-capable approved runtime
<!-- CYBERCORE:CHECKPOINT:END -->
