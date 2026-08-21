# CyberCore Project State

_Last updated: 2026-08-20 22:12 CEST_

## Source of truth

- Repository: `cyberDJs/CyberCore`
- Stable branch: `main`
- Canonical product state: GitHub `main`
- Evidence/archive/collaboration layer: Google Drive `CyberCore/CASER-E`
- Active branch: `docs/post-pr49-reconciliation`
- Active pull request: #50 — PR #49 post-merge state reconciliation and WB-0031 kickoff
- Active artifact: `WB-0031 — Staging Runtime Gate Preflight`
- Active work block: `WB-0031 — Staging Runtime Gate Preflight`
- Last verified `main`: `2de294bb3334e4194769f3b883d58a2e5e3a8ea5`
- Governance rule: no production mutation without explicit human approval
- CI policy: GitHub Actions verification is required before merge
- CodeQL policy: Advanced setup is verified; GitHub Default setup is disabled to avoid conflicting scans

## Current milestone

`WB-0030 — Staging Readiness Gate` merged through PR #49 and is now canonical on `main` as `2de294bb3334e4194769f3b883d58a2e5e3a8ea5`.

The current work is a post-merge reconciliation and next-slice kickoff: record PR #49 as merged, update canonical project state, and define `WB-0031 — Staging Runtime Gate Preflight` from `main@2de294bb3334e4194769f3b883d58a2e5e3a8ea5`.

## Active objective

Continue the first safe CyberCore self-deployment loop for InterServer shared-hosting staging:

1. preserve accepted ADR-0006 staging-only boundary;
2. treat `WB-0030` as the canonical fail-closed readiness gate;
3. prepare `WB-0031` as a non-remote-write preflight for target identity, deployment protocol/target capability, secret alias readiness, rollback proof, effect-verifier proof, and operator authorization references;
4. keep `staging_apply` blocked unless a later work block verifies all runtime gates and receives fresh explicit remote-write authorization;
5. use LG-0001/LG-0002 as read-only source-of-truth orchestration support, not as mutation authority.

## Current status

- Work block: `WB-0031` active candidate
- Branch: `docs/post-pr49-reconciliation`
- Pull request: #50
- WB-0028 foundation / PR #39: merged as `4f582583789346724813a2c515fe30450c173b0c`
- ADR-0006 lifecycle status: Accepted
- ADR-0006 decision date: 2026-08-20
- ADR-0006 authority: Jan Kočí
- ADR-0006 decision state: `DECIDED`
- WB-0029 / PR #47: merged as `09750d7c5b2e49b9b4006c1288391d6d5c6066d5`
- PR #48 post-merge reconciliation: merged as `dd389e87eb2684a4c90a816d35c0472e0b5e1fee`
- WB-0030 / PR #49: merged as `2de294bb3334e4194769f3b883d58a2e5e3a8ea5`
- Live InterServer staging deployment: blocked until target identity, deployment capability, secret, rollback, effect-verifier, and fresh explicit authorization gates pass
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

Allowed in WB-0031:

- non-secret preflight documentation;
- closed evidence requirements for target identity, deployment protocol/target capability, secret aliases, rollback, effect verifier, and operator authorization references;
- checks that define what must be true before a later remote-write request can be considered;
- local non-mutating tests or validators plus docs/state/audit updates;
- no-remote-write planning artifacts.

Blocked without separate explicit approval:

- production deployment;
- DNS, mail, billing, DirectAdmin, VPS, WordPress, Nextcloud, or provider mutation;
- live InterServer remote write;
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

## Current work block

### WB-0031 — Staging Runtime Gate Preflight

This work block prepares the evidence and authorization shape for a future first live staging remote-write request without performing that request.

It must define:

- how staging URL and staging path identity can be verified without touching production;
- how the deployment protocol/method and staging target capability will be verified before `staging_apply` without treating target metadata as proof;
- how secret aliases can be verified without reading or storing secret values;
- how rollback readiness will be proven before any write;
- how effect verification will prove staging changed and production did not;
- what fresh operator authorization must contain before a later remote-write work block starts.

## Security follow-up

- Six high-severity transitive `npm audit` findings remain deferred security debt in the isolated visual documentation toolchain.
- InterServer exposed API key and 2FA/TOTP rotation status remains unresolved until verified by a human-approved MOP with no secret values in ordinary evidence stores.
- WB-0031 does not resolve those blockers; it keeps live staging deploy blocked behind target identity, deployment capability, secret, rollback, effect-verifier, and fresh authorization gates.

## Next action

Run hosted CI/CodeQL for PR #50 and stop at `READY_FOR_MERGE`. Do not perform any live remote write, provider mutation, production mutation, DNS, mail, billing, DirectAdmin, VPS, WordPress, Nextcloud, or plaintext-secret handling.

<!-- CYBERCORE:CHECKPOINT:START -->
<!-- CYBERCORE:PROJECT-STATE-CHECKPOINT:pr49-post-merge-wb0031 -->
## Manual repository checkpoint

- Generated: `2026-08-20T22:12:00+02:00`
- Branch: `docs/post-pr49-reconciliation`
- Pull request: #50
- Active artifact: `WB-0031`
- Active work block: `WB-0031 — Staging Runtime Gate Preflight`
- Last verified main: `2de294bb3334e4194769f3b883d58a2e5e3a8ea5`
- Test evidence: hosted CI/CodeQL required on PR #50 before merge
- Project Kernel: present
- Project State: WB-0030 merged; WB-0031 active candidate; remote-write and production gates remain blocked
<!-- CYBERCORE:CHECKPOINT:END -->
