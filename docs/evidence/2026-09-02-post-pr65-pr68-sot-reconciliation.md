# CyberCore Source-of-Truth Reconciliation

## Scope

Repository and evidence-state reconciliation only. No staging, provider, DNS, TLS, credential, billing, production, or application mutation is authorized or performed by this change.

## Canonical source

- Repository: `cyberDJs/CyberCore`
- Canonical branch: `main`
- Canonical main observed for this reconciliation: `f245e89030a573ae3594a44ad42a828245bb2bba`
- Google Drive `CyberCore/CASER-E`: evidence/archive/collaboration mirror, not canonical product state

## Canonical changes missing from the prior state snapshot

The previous `PROJECT_STATE.md` / `.cybercore/project.yaml` snapshot still described PR #55 / WB-0034 as active and `d74497e...` as last verified main. Current GitHub reality has advanced materially.

Relevant merged work now includes:

- PR #55 — WB-0034 first staging deployment preflight — merged as `090433264f4338828db293a327d5083bacf1813f`;
- PR #63 — WB-0034 path-scoped explicit FTPS security amendment — merged as `2f8b5b54ba8745871dd3a183c739a32473e8535a`;
- PR #64 — `feat(wb0035): add bounded FTPS runtime and effect verifier` — merged as `f12eb91ea8dd718f9f3c2d366d578859dab31132`;
- PR #68 — `feat(wb0036): Cyber Voice Foundation` — merged as `bb18ffedff43970e27fdd0e86ffeb469a8d465de`;
- PR #65 — `fix(wb0036): make first-write recovery non-destructive and block unsafe FTPS writes` — merged as current `main@f245e89030a573ae3594a44ad42a828245bb2bba`.

PR #65 exact approved head was `e239ce48cb18a7152adcaa006b8cc74c49c646f2`; CI #585 and CodeQL #584 passed and the fresh exact-head Codex review completed before merge.

## Current safety boundary

- First-write remote mutation remains `BLOCKED`.
- The WB-0035 FTPS writer cannot safely prove atomic no-overwrite under concurrency.
- WB-0036 recovery is read-only and MLST-only; it performs no delete, rename, upload, chmod or chown.
- A future live staging write requires a separately reviewed atomic create-if-absent mechanism or independently verified exclusive mutation access plus fresh explicit operator authority.
- Production mutation remains outside current authority.

## Open pull-request reality

Current open CyberCore PRs observed during reconciliation:

- #69 — this post-PR65/PR68 SOT reconciliation candidate;
- #67 — CyberCore MCP Foundation v0.1 — draft; created from an older main and requires post-PR65/68 revalidation before readiness;
- #66 — WB-LR0001 Durable autonomous LongRun runtime — open/non-draft; created from an older main and requires post-PR65/68 revalidation before any merge decision;
- #61 — old draft `WB-0035` InterServer VPS + Vikunja plan — historical identity collision; no provider order/payment action is authorized by this reconciliation;
- #45 — old staging-plan candidate — stale/supersession review required;
- #13 — old structured registry v0 draft — stale/supersession review required;
- #5 — old provider-framework draft — stale/supersession review required.

No unrelated open PR is merged, closed, renumbered, rebased, or provider-executed by this reconciliation.

## Identity conflicts

### WB-0035 — CONFLICT / NEEDS_REVIEW

The identifier is used by both:

- merged PR #64 — bounded FTPS runtime/effect verifier; and
- open draft PR #61 — InterServer VPS + Vikunja plan.

Do not treat these as one work block. Historical provenance must be preserved; future cleanup requires an explicit naming/supersession decision.

### WB-0036 — CONFLICT / NEEDS_REVIEW

The identifier is used by both merged changes:

- PR #65 — first-write rollback/runtime safety hardening; and
- PR #68 — Cyber Voice Foundation.

Both are canonical Git history. Do not rewrite history to hide the collision. A later governance cleanup should assign unambiguous registry aliases/identities while preserving original PR titles and commit provenance.

## Google Drive reconciliation

Connected Drive inspection resolved `CyberCore/CASER-E` with `working/` and `evidence/` subfolders. `working/` still contains the older `CyberCore Audit 2026-08-17 — Working`.

A new native Google Doc named `CyberCore SOT Reconciliation — post PR65 / PR68` was created and verified in `CASER-E/evidence`. Its readback records the same canonical GitHub main, PR #69 candidate identity, recent merge state, remote-write blocker, parallel candidate tracks, identity conflicts, stale-PR queue and priority sequence. Provider-private Drive identifiers are intentionally not committed to this public repository.

The Drive artifact is an evidence mirror only. GitHub `main` remains canonical product state.

## Reconciliation decision

Current canonical state should stop naming WB-0034 / PR #55 as active. The immediate coordination focus is source-of-truth reconciliation plus review of parallel current tracks, not staging write execution.

Priority order after this reconciliation candidate:

1. verify this reconciliation against current `main` and merge only with explicit authority;
2. rebase/revalidate PR #66 LongRun against the new canonical main;
3. rebase/revalidate PR #67 MCP Foundation against the new canonical main;
4. resolve work-block identity collisions and stale PRs (#61, #45, #13, #5) through explicit supersession/closure decisions;
5. start a separate engineering block for concurrency-safe first-write semantics before requesting any live staging-write authority.
