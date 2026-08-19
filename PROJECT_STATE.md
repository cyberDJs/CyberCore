# CyberCore Project State

_Last updated: 2026-08-19 15:07 CEST_

## Source of truth

- Repository: `cyberDJs/CyberCore`
- Stable branch: `main`
- Canonical product state: GitHub `main`
- Evidence/archive/collaboration layer: Google Drive `CyberCore/CASER-E`
- Active branch: `feat/wb-0028-self-deploy-staging-loop`
- Active pull request: `#39`
- Active artifact: `WB-0028 — Self-Deployment Staging Loop v0`
- Active work block: `WB-0028 — Self-Deployment Staging Loop v0`
- Last verified `main`: `cd4e8426b0e97d7362d6061653d56f27274bca5b`
- Governance rule: no production mutation without explicit human approval
- CI policy: GitHub Actions verification is required before merge; `main` branch protection is active
- CodeQL policy: Advanced setup is verified; GitHub Default setup is disabled to avoid conflicting scans

## Current milestone

`WB-0028 — Self-Deployment Staging Loop v0` is active as a candidate work block.

PR #38 has been merged into `main` as `cd4e8426b0e97d7362d6061653d56f27274bca5b`. The previous post-merge state reconciliation is complete, and the next development slice starts the staging-only self-deployment foundation.

## Active objective

Define the first safe CyberCore self-deployment loop for InterServer shared-hosting staging:

1. define a staging-only self-deploy architecture;
2. create a non-secret InterServer staging target contract;
3. create a manual staging preparation runbook;
4. propose the self-deployment staging boundary as an ADR candidate;
5. record kickoff evidence;
6. keep live remote deployment blocked until staging target identity, secret aliases, rollback, and effect verifier are verified.

## Current status

- Work block: `WB-0028` active candidate
- Branch: `feat/wb-0028-self-deploy-staging-loop`
- Pull request: `#39` open as Draft
- Runtime code changes: none in this initial slice
- Live InterServer staging deployment: blocked until target gates pass
- Production/provider/DirectAdmin/SSH/DNS/mail/billing changes: none
- Secret values stored: none
- PR #38: merged into `main` as `cd4e8426b0e97d7362d6061653d56f27274bca5b`
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

Actual replacement or deployment secrets may only be placed in an OS-backed secret store, an approved external vault, or a GitHub Environment secret for `interserver-staging` after explicit approval. Evidence may record only safe references, aliases, provider names, scopes, timestamps, fingerprints/hashes where safe, owner/status fields, and verification state.

## Self-deployment boundary

The current self-deployment work is staging-only.

Allowed in WB-0028:

- branch, docs, target registry, runbook, ADR candidate, audit evidence;
- staging plan and dry-run design;
- future manual workflow proposal that fails closed when target data or secret aliases are missing.

Blocked without separate explicit approval:

- production deployment;
- DNS, mail, billing, DirectAdmin, VPS, WordPress, Nextcloud, or provider mutation;
- live InterServer remote write;
- reading or storing plaintext secrets;
- accepting ADR-0004.

## Recent completed state changes

### PR #35 — WB-0027 post-merge state reconciliation

Squash-merged into `main` as:

```text
26d1947f3f75ed95192a0c9ad59506e965d90ab3
```

Delivered:

- reconciled project state after PR #34;
- fixed inactive-artifact persistence so YAML null/empty values are not treated as active artifact state;
- verified checkpoint persistence remains stable across repeats.

Verification:

- hosted CI and CodeQL passed;
- regression tests passed with **223 passed**;
- independent approval: `nulleimy`.

### PR #36 — README landing-page redesign

Squash-merged into `main` as:

```text
3fbbc846f82ed98c3f7c69047792ffeb3abd19f6
```

Delivered:

- reduced README into a GitHub-native landing page;
- retained architecture and lifecycle visuals;
- linked detailed architecture/specification material instead of duplicating it;
- no runtime changes.

Verification:

- `git diff --check`;
- `PYTHON=.venv/bin/python scripts/verify.sh` with **223 tests passed**;
- `scripts/verify_visual_docs.sh`;
- README relative links and referenced local assets verified;
- AI review #1: Codex;
- AI review #2: independent assistant review;
- human approval: `nulleimy`.

### PR #37 — Security and Source-of-Truth Baseline activation

Merged into `main` as:

```text
6b74a56ee32278e5048ca3553bd7d87c1dd07645
```

Delivered:

- reconciled `.cybercore/project.yaml` and `PROJECT_STATE.md` after PR #35/#36;
- activated `OPS-0001` as the next read-first operational artifact;
- added CASER-SOURCER kickoff evidence tying GitHub canonical state to Google Drive CASER-E;
- enforced the expanded no-secret boundary including ChatGPT Library;
- retained parser-compatible `Active work block` state;
- made approved plaintext-secret destinations unconditional: OS-backed secret store or approved external vault only.

Verification:

- hosted CI and CodeQL passed on final head `d7dff64cf0fd8b62c61daef833ce4851ffc34794`;
- review threads resolved;
- human approval present before merge.

### PR #38 — PR #37 post-merge reconciliation

Merged into `main` as:

```text
cd4e8426b0e97d7362d6061653d56f27274bca5b
```

Delivered:

- recorded PR #37 as merged;
- kept `OPS-0001` active as the operational baseline;
- removed stale open/ready wording for PR #37;
- added a post-merge audit note;
- updated review model so Amy / `nulleimy` is not required for docs/state-only non-production PRs.

Verification:

- hosted CI and CodeQL passed on final head `68697f41549fcb35df8867b9b9116677398e00e7`;
- Codex P2 wording thread resolved;
- manual AI review passed;
- explicit operator authorization was provided for merge.

## Completed checkpoint summary

| Artifact / PR | Merge commit | Verification |
|---|---|---|
| PR #18 — Interactive demo, Project Kernel and CCL runtime foundation | `df222d59635398d325d467110a7139210fe46396` | 14 passed |
| WB-0015 / PR #19 — Repository checkpoint runtime | `4ef4bbf` | 18 passed |
| WB-0016 / PR #20 — Controlled checkpoint persistence | `de4f8f211ef1bf88db65b00ffb5ee577e9c20a86` | 23 passed |
| WB-0017 / PR #21 — Verification evidence automation | `d21e3bc3875bf298939585958c90167fa36dd76c` | 46 passed |
| WB-0018 / PR #22 — Idempotent canonical memory | `1e174e9180e64c3bfc5c70fa52d5c7e399ead9eb` | 52 passed |
| WB-0019 / PR #23 — Controlled post-merge state transitions | `ca2da8b72563e65d0818861e00ff38ca6f12b75e` | 66 passed |
| WB-0020 / PR #24 — Remote-aware repository identity | `5ac0db5278acc57710f4987ba34e605cdaaf2ec3` | 78 passed |
| WB-0021 / PR #25 — Repository identity diagnostics | `6c9a4cff56731e8e53bfb886fde6c61a2340a085` | 86 passed |
| WB-0022 / PR #26 — Canonical repository identity policy | `e674edc707a17ab8eb9ba1af9d40ae7a80657334` | 98 passed |
| WB-0023 / PR #27 — Trusted operation context | `03a04c5ad73489775552df34e21baa559f2a41da` | 109 passed |
| WB-0024 / PR #29 — Operation context disclosure policy | `1ba003f8e17448ac8f962955f88d6214c58c6cb2` | 201 passed |
| WB-0025 / PR #30 — CI foundation | `dbd61e9094d2b45ce11468d12b3700c66979cd0b` | 214 passed; GitHub Actions 6/6 passed |
| WB-0025 / PR #31 — CodeQL and merge gates | `bd635ca56bd2cb7ce0b221c03e9664b128095d25` | 218 passed; CI and CodeQL passed |
| WB-0026 / PR #32 — Verified main branch protection | `00b408dd9439caa7e6c660737d1123d0eaa1c12f` | 218 passed; CI and CodeQL passed; `nulleimy` approval |
| WB-0027 / PR #34 — Visual Documentation and Learn Capture v0.1 | `94cb1998274e31e9ce3314f59d2e0ae290bc40cc` | 221 passed; CI and CodeQL passed; `nulleimy` approval |
| WB-0027 post-merge / PR #35 — State reconciliation and inactive-artifact persistence | `26d1947f3f75ed95192a0c9ad59506e965d90ab3` | 223 passed; CI and CodeQL passed; `nulleimy` approval |
| README landing-page redesign / PR #36 | `3fbbc846f82ed98c3f7c69047792ffeb3abd19f6` | 223 passed; CI and CodeQL passed; AI+human gate passed |
| OPS-0001 activation / PR #37 | `6b74a56ee32278e5048ca3553bd7d87c1dd07645` | CI and CodeQL passed; human approval; merged |
| PR #37 post-merge reconciliation / PR #38 | `cd4e8426b0e97d7362d6061653d56f27274bca5b` | CI and CodeQL passed; manual AI review; merged |

## Security follow-up

- Six high-severity transitive `npm audit` findings remain deferred security debt in the isolated visual documentation toolchain.
- InterServer exposed API key and 2FA/TOTP rotation status remains unresolved until verified by a human-approved MOP with no secret values in ordinary evidence stores.
- WB-0028 does not resolve those blockers; it makes live staging deploy depend on target and secret verification.

## Next action

Run hosted CI/CodeQL for PR #39. If green, review the non-production self-deployment boundary and decide whether to add the first disabled/manual staging workflow in the next slice.

<!-- CYBERCORE:CHECKPOINT:START -->
<!-- CYBERCORE:PROJECT-STATE-CHECKPOINT:wb0028-self-deploy-candidate -->
## Manual repository checkpoint

- Generated: `2026-08-19T15:07:00+02:00`
- Branch: `feat/wb-0028-self-deploy-staging-loop`
- Pull request: `#39`
- Active artifact: `WB-0028`
- Active work block: `WB-0028`
- Last verified main: `cd4e8426b0e97d7362d6061653d56f27274bca5b`
- Working tree: connector-managed PR branch
- Test evidence: hosted CI/CodeQL required before merge
- Project Kernel: present
- Project State: transitioned to WB-0028 active candidate
<!-- CYBERCORE:CHECKPOINT:END -->