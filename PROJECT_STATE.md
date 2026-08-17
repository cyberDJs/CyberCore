# CyberCore Project State

_Last updated: 2026-08-17 14:09 CEST_

## Source of truth

- Repository: `cyberDJs/CyberCore`
- Stable branch: `main`
- Canonical product state: GitHub `main`
- Evidence/archive/collaboration layer: Google Drive `CyberCore/CASER-E`
- Active branch: `docs/state-reconcile-security-baseline`
- Active pull request: `#37`
- Active artifact: `OPS-0001 — Security and Source-of-Truth Baseline`
- Last verified `main`: `3fbbc846f82ed98c3f7c69047792ffeb3abd19f6`
- Governance rule: no production mutation without explicit human approval
- CI policy: GitHub Actions verification is required before merge; `main`
  branch protection is active and verified through ruleset
  `main-branch-protection` (`18986451`)
- CodeQL policy: Advanced setup is verified; GitHub Default setup is disabled to avoid conflicting scans

## Current milestone

Security and Source-of-Truth Baseline active.

This supersedes the prior idle state after WB-0027. The next work is not a runtime or provider mutation; it is a read-first operational baseline that reconciles source-of-truth state and prepares safe, human-approved security work.

## Active objective

Execute `OPS-0001` as a read-first security and source-of-truth baseline:

1. confirm InterServer exposed credential revocation and rotation status without storing secret values;
2. reconcile GitHub canonical state, Google Drive CASER-E evidence, historical Drive copies, screenshots, and pasted operator reports;
3. produce a sanitized infrastructure snapshot plan before any production mutation;
4. draft a secret-rotation MOP with no secret values;
5. record production/development separation strategy;
6. recommend the next implementation work block only after blockers are verified closed or explicitly deferred.

## Current status

- Work block: `OPS-0001` active candidate
- Branch: `docs/state-reconcile-security-baseline`
- Pull request: `#37` open as Draft
- Runtime code changes: none
- Production/provider/DirectAdmin/SSH/DNS/mail/billing changes: none
- Secret values stored: none
- GitHub `main`: still canonical product state
- Google Drive CASER-E: evidence/archive/collaboration layer only, not canonical product state
- Initial PR #37 CI/CodeQL passed on `9a55503b189ac7d5df02b752a39df4e2264434e8`
- Manual remediation head `30ee4b23af3f1bb51b81f535b98e83b9eac171ed` has been pushed and still requires hosted CI/CodeQL before Ready for Review

## Secret-handling boundary

Plaintext secrets are denied in:

- GitHub;
- Google Drive;
- ChatGPT Library;
- Slack;
- chat;
- CASER documents;
- ordinary evidence logs.

Actual replacement secrets may only be placed in an OS-backed secret store or approved external vault after explicit human approval. Evidence may record only safe references, aliases, provider names, scopes, timestamps, fingerprints/hashes where safe, owner/status fields, and verification state.

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

Current Draft PR.

Purpose:

- reconcile `.cybercore/project.yaml` and this `PROJECT_STATE.md` after PR #35/#36;
- activate `OPS-0001` as the next read-first operational artifact;
- add CASER-SOURCER kickoff evidence tying GitHub canonical state to Google Drive CASER-E;
- enforce the expanded no-secret boundary including ChatGPT Library.

Manual remediation:

- `871c0aab9b5e47de2bd478ecae1ee95ad83b725c` broadened the project-kernel secret boundary;
- `2d3eee97bd58c8d7420cd9cf88c54cc6e96b097c` clarified the OPS-0001 no-secret boundary;
- `30ee4b23af3f1bb51b81f535b98e83b9eac171ed` retained the checkpoint block after project-state reconciliation.

Merge readiness:

- not Ready until Codex P1 feedback is resolved or obsolete;
- not Ready until hosted CI/CodeQL passes on the latest remediation commit;
- not Ready until second AI review is clean;
- not Ready until human approval is present on current head.

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

## Security follow-up

- Six high-severity transitive `npm audit` findings remain deferred security debt in the isolated visual documentation toolchain.
- InterServer exposed API key and 2FA/TOTP rotation status remains unresolved until verified by a human-approved MOP with no secret values in ordinary evidence stores.

## Next action

Finish PR #37 remediation, re-run hosted CI/CodeQL, re-request Codex review, run second AI review, then request human approval if clean.

<!-- CYBERCORE:CHECKPOINT:START -->
<!-- CYBERCORE:PROJECT-STATE-CHECKPOINT:manual-pr37-remediation -->
## Manual repository checkpoint

- Generated: `2026-08-17T14:09:00+02:00`
- Branch: `docs/state-reconcile-security-baseline`
- Pull request: `#37`
- Active artifact: `OPS-0001`
- Last verified main: `3fbbc846f82ed98c3f7c69047792ffeb3abd19f6`
- Working tree: connector-managed PR branch
- Test evidence: initial CI/CodeQL passed on `9a55503b189ac7d5df02b752a39df4e2264434e8`; remediation commits require fresh hosted CI/CodeQL before Ready for Review
- Project Kernel: present
- Project State: reconciled manually for PR #37
<!-- CYBERCORE:CHECKPOINT:END -->
