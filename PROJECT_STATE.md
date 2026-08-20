# CyberCore Project State

_Last updated: 2026-08-20 09:54 CEST_

## Source of truth

- Repository: `cyberDJs/CyberCore`
- Stable branch: `main`
- Canonical product state: GitHub `main`
- Evidence/archive/collaboration layer: Google Drive `CyberCore/CASER-E`
- Active branch: `feat/wb-0030-staging-readiness-gate`
- Active pull request: pending — WB-0030 staging readiness gate
- Active artifact: `WB-0030 — Staging Readiness Gate`
- Active work block: `WB-0030 — Staging Readiness Gate`
- Last verified `main`: `dd389e87eb2684a4c90a816d35c0472e0b5e1fee`
- Governance rule: no production mutation without explicit human approval
- CI policy: GitHub Actions verification is required before merge
- CodeQL policy: Advanced setup is verified; GitHub Default setup is disabled to avoid conflicting scans

## Current milestone

`WB-0030 — Staging Readiness Gate` is the active candidate after PR #48 reconciled PR #47 / WB-0029 post-merge state.

This slice adds a fail-closed readiness evidence validator for future staging remote writes. It does not authorize live InterServer access, does not read secrets, and does not perform remote writes.

## Active objective

Continue the first safe CyberCore self-deployment loop for InterServer shared-hosting staging:

1. preserve accepted ADR-0006 staging-only boundary;
2. add readiness evidence fields for target identity, secret aliases, rollback, effect verifier, and operator authorization;
3. validate that readiness is blocked until all gate fields are verified or approved;
4. keep `staging_apply` blocked unless a later work block has verified all runtime gates and receives fresh explicit remote-write authorization;
5. use LG-0001/LG-0002 as read-only source-of-truth orchestration support, not as mutation authority.

## Current status

- Work block: `WB-0030` active candidate
- Branch: `feat/wb-0030-staging-readiness-gate`
- Pull request: pending
- WB-0028 foundation / PR #39: merged as `4f582583789346724813a2c515fe30450c173b0c`
- ADR-0006 lifecycle status: Accepted
- ADR-0006 decision date: 2026-08-20
- ADR-0006 authority: Jan Kočí
- ADR-0006 decision state: `DECIDED`
- WB-0029 / PR #47: merged as `09750d7c5b2e49b9b4006c1288391d6d5c6066d5`
- PR #48 post-merge reconciliation: merged as `dd389e87eb2684a4c90a816d35c0472e0b5e1fee`
- Live InterServer staging deployment: blocked until target gates and fresh explicit remote-write authorization pass
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

Allowed in WB-0030:

- readiness evidence schema/example;
- local validation logic;
- tests proving the readiness gate fails closed;
- documentation and audit evidence;
- no-remote-write CLI behavior with explicit `--expect-blocked` support.

Blocked without separate explicit approval:

- production deployment;
- DNS, mail, billing, DirectAdmin, VPS, WordPress, Nextcloud, or provider mutation;
- live InterServer remote write;
- reading or storing plaintext secrets;
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

## Current work block

### WB-0030 — Staging Readiness Gate

This work block adds:

- `.cybercore/deploy/readiness/interserver-staging-readiness.example.yaml`;
- `validate_remote_write_readiness`;
- `scripts/validate_staging_readiness.py`;
- tests that prove the readiness example is intentionally blocked;
- tests that reject remote-write claims and plaintext secret literals.

## Security follow-up

- Six high-severity transitive `npm audit` findings remain deferred security debt in the isolated visual documentation toolchain.
- InterServer exposed API key and 2FA/TOTP rotation status remains unresolved until verified by a human-approved MOP with no secret values in ordinary evidence stores.
- WB-0030 does not resolve those blockers; it keeps live staging deploy blocked behind target, secret, rollback, effect verifier, and fresh authorization gates.

## Next action

Open PR for WB-0030 and run CI/CodeQL. Stop at `READY_FOR_MERGE`. Do not perform any live remote write, provider mutation, production mutation, DNS, mail, billing, DirectAdmin, VPS, WordPress, Nextcloud, or plaintext-secret handling.

<!-- CYBERCORE:CHECKPOINT:START -->
<!-- CYBERCORE:PROJECT-STATE-CHECKPOINT:wb0030-staging-readiness-gate -->
## Manual repository checkpoint

- Generated: `2026-08-20T09:54:00+02:00`
- Branch: `feat/wb-0030-staging-readiness-gate`
- Pull request: pending
- Active artifact: `WB-0030`
- Active work block: `WB-0030 — Staging Readiness Gate`
- Last verified main: `dd389e87eb2684a4c90a816d35c0472e0b5e1fee`
- Test evidence: hosted CI/CodeQL required on the PR before merge
- Project Kernel: present
- Project State: WB-0030 active candidate; remote-write and production gates remain blocked
<!-- CYBERCORE:CHECKPOINT:END -->
