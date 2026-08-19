# CyberCore Project State

_Last updated: 2026-08-19 22:07 CEST_

## Source of truth

- Repository: `cyberDJs/CyberCore`
- Stable branch: `main`
- Canonical product state: GitHub `main`
- Evidence/archive/collaboration layer: Google Drive `CyberCore/CASER-E`
- Active branch: `docs/adr-0006-decision-readiness`
- Active pull request: `#44` — post-PR43 reconciliation and ADR-0006 decision readiness
- Active artifact: `WB-0028 — Self-Deployment Staging Loop v0`
- Active work block: `WB-0028 — Self-Deployment Staging Loop v0`
- Last verified `main`: `4ca00fb7e1a6b618746afb2045e230a1763256e4`
- Governance rule: no production mutation without explicit human approval
- CI policy: GitHub Actions verification is required before merge; `main` branch protection is active
- CodeQL policy: Advanced setup is verified; GitHub Default setup is disabled to avoid conflicting scans

## Current milestone

`WB-0028 — Self-Deployment Staging Loop v0` remains the active work stream after its documentation/state foundation merged through PR #39.

PR #40 added accepted `ADR-0005 — LangGraph as Optional Orchestration Runtime` and LG-0001. PR #41 added LG-0002 trusted source ingest. PR #43 resolved the duplicate ADR identifier by preserving accepted LangGraph ADR-0005 and renumbering the self-deployment staging-boundary proposal to `ADR-0006`.

PR #44 now reconciles the canonical state after PR #43 and records the decision-readiness review for ADR-0006. The review recommendation is **ACCEPT**, while the ADR lifecycle status remains **Proposed** until explicit operator authorization.

## Active objective

Continue the first safe CyberCore self-deployment loop for InterServer shared-hosting staging:

1. preserve the staging-only self-deploy architecture;
2. keep the non-secret InterServer staging target contract authoritative for the current work stream;
3. keep the manual staging preparation and rollback/effect-verification model reviewable;
4. decide whether to accept proposed `ADR-0006 — Self-Deployment Staging Boundary`;
5. keep live remote deployment blocked until staging target identity, secret aliases, deployment capability, rollback, and effect verifier are verified;
6. use LG-0001/LG-0002 as read-only source-of-truth orchestration support, not as mutation authority.

## Current status

- Work block: `WB-0028` active
- Branch: `docs/adr-0006-decision-readiness`
- Pull request: `#44` open as Draft during final verification
- WB-0028 foundation / PR #39: merged as `4f582583789346724813a2c515fe30450c173b0c`
- LG-0001 / PR #40: merged as `56ccb7b8ea3871b592b79b2601da29122e677183`
- LG-0002 / PR #41: merged as `2cdfe5ffd1f6cd16e5a7a64cbc2c5f82c364e187`
- ADR identifier reconciliation / PR #43: merged as `4ca00fb7e1a6b618746afb2045e230a1763256e4`
- ADR-0006 lifecycle status: Proposed
- ADR-0006 review state: `READY_FOR_DECISION`
- ADR-0006 review recommendation: ACCEPT
- Runtime code changes: LG-0001 and LG-0002 are on `main`; PR #44 is documentation/state/decision evidence only
- Live InterServer staging deployment: blocked until target gates pass
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

Actual replacement or deployment secrets may only be placed in an OS-backed secret store or an approved external vault after explicit approval. A GitHub Environment secret for `interserver-staging` is only a proposed future option until an accepted governance decision authorizes it. Evidence may record only safe references, aliases, provider names, scopes, timestamps, fingerprints/hashes where safe, owner/status fields, and verification state.

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
- accepting ADR-0006.

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

### PR #39 — WB-0028 self-deployment staging foundation

Merged into `main` as:

```text
4f582583789346724813a2c515fe30450c173b0c
```

Delivered:

- activated WB-0028 as the staging-only self-deployment work stream;
- added target contract, architecture, runbooks, rollback/effect-verifier, authority and stop-line documentation;
- kept live InterServer deployment and production mutation blocked;
- introduced the self-deployment staging-boundary ADR proposal, later renumbered from ADR-0005 to ADR-0006 after collision detection.

Verification:

- hosted CI run #58 passed on final PR head `1601f69170e96e9a35b4d89ca25a88a2b86d4f3a`;
- CodeQL run #55 passed on the same head.

### PR #40 — LG-0001 Source-of-Truth Reconciler

Merged into `main` as:

```text
56ccb7b8ea3871b592b79b2601da29122e677183
```

Delivered:

- accepted `ADR-0005 — LangGraph as Optional Orchestration Runtime`;
- added deterministic read-only LG-0001 reconciliation;
- classified `CURRENT | DRIFT | CONFLICT | UNKNOWN`;
- detected existing remediation to prevent duplicate corrective work.

Verification:

- hosted CI and CodeQL passed on final head `aef5469c2ea0dca84dac1b39a289289775584f27`;
- Python 3.11–3.14 matrix, Ruff, Pyright, package build and wheel smoke passed.

### PR #41 — LG-0002 Trusted Source Ingest

Merged into `main` as:

```text
2cdfe5ffd1f6cd16e5a7a64cbc2c5f82c364e187
```

Delivered:

- added trusted GitHub/Google Drive provider-observation binding into LG-0001;
- prevented provider payloads from self-declaring authority;
- added fail-closed validation for unsupported authorities/providers and unsafe provenance locators;
- kept the graph read-only with no provider/network/write/production authority.

Verification:

- exact-head CI run #69 passed;
- exact-head CodeQL run #66 passed;
- Python 3.11 reported **244 passed**; Python 3.11–3.14 matrix passed;
- Ruff, Pyright, package build and wheel smoke passed;
- P1/P2 review findings were remediated before merge.

### PR #43 — ADR identifier and post-merge reconciliation

Merged into `main` as:

```text
4ca00fb7e1a6b618746afb2045e230a1763256e4
```

Delivered:

- preserved accepted `ADR-0005 — LangGraph as Optional Orchestration Runtime`;
- renumbered the proposed self-deployment staging boundary to `ADR-0006`;
- reconciled project state after PR #39, PR #40, and PR #41;
- kept ADR-0006 Proposed and preserved all staging/production authority gates.

Verification:

- exact-head CI run #73 passed;
- exact-head CodeQL run #70 passed;
- final P2 state/review findings were remediated before merge.

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
| WB-0028 foundation / PR #39 | `4f582583789346724813a2c515fe30450c173b0c` | CI #58 and CodeQL #55 passed |
| LG-0001 / PR #40 | `56ccb7b8ea3871b592b79b2601da29122e677183` | CI and CodeQL passed; Python 3.11–3.14 gates passed |
| LG-0002 / PR #41 | `2cdfe5ffd1f6cd16e5a7a64cbc2c5f82c364e187` | 244 passed on Python 3.11; CI #69 and CodeQL #66 passed |
| ADR identifier reconciliation / PR #43 | `4ca00fb7e1a6b618746afb2045e230a1763256e4` | CI #73 and CodeQL #70 passed |

## Security follow-up

- Six high-severity transitive `npm audit` findings remain deferred security debt in the isolated visual documentation toolchain.
- InterServer exposed API key and 2FA/TOTP rotation status remains unresolved until verified by a human-approved MOP with no secret values in ordinary evidence stores.
- WB-0028 does not resolve those blockers; it makes live staging deploy depend on target and secret verification.

## Next action

Make the explicit operator decision on `ADR-0006 — Self-Deployment Staging Boundary`. The decision-readiness review recommends **ACCEPT**. If accepted, separately decide whether to authorize the next disabled/manual staging workflow + manifest/target-validator slice. Live staging and production writes remain blocked until their existing target, secret, rollback, effect-verification, and human-authorization gates are satisfied.

<!-- CYBERCORE:CHECKPOINT:START -->
<!-- CYBERCORE:PROJECT-STATE-CHECKPOINT:adr0006-decision-readiness -->
## Manual repository checkpoint

- Generated: `2026-08-19T22:07:00+02:00`
- Branch: `docs/adr-0006-decision-readiness`
- Pull request: `#44`
- Active artifact: `WB-0028`
- Active work block: `WB-0028`
- Last verified main: `4ca00fb7e1a6b618746afb2045e230a1763256e4`
- Working tree: connector-managed ADR review/reconciliation PR branch
- Test evidence: hosted CI/CodeQL required on final PR #44 head before Ready for Review
- Project Kernel: present
- Project State: PR #43 merged and reconciled; ADR-0006 is Proposed + READY_FOR_DECISION with review recommendation ACCEPT
<!-- CYBERCORE:CHECKPOINT:END -->
