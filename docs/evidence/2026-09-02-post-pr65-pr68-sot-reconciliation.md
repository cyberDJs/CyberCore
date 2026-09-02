# CyberCore Source-of-Truth Reconciliation

## Scope

Repository and evidence-state reconciliation only. No staging, provider, DNS, TLS, credential, billing, production, application, VPS, or remote-write mutation is authorized or performed by this change.

The initial PR #69 reconciliation was opened after PR #65 and PR #68. While review was in progress, canonical `main` advanced again through PR #70 and PR #66. This evidence record therefore extends the same reconciliation to the current canonical state rather than freezing an obsolete snapshot.

## Canonical source

- Repository: `cyberDJs/CyberCore`
- Canonical branch: `main`
- Canonical main observed for this reconciliation: `1ada318abcd93c7980cc6adc975afb0decefbbec`
- Google Drive `CyberCore/CASER-E`: evidence/archive/collaboration mirror, not canonical product state
- Coordination PR: #69
- Coordination branch: `docs/post-pr65-pr68-sot-reconciliation`

A compare from the original PR #69 base `f245e89030a573ae3594a44ad42a828245bb2bba` to current `main@1ada318abcd93c7980cc6adc975afb0decefbbec` shows `main` 22 commits ahead and no changes to the three PR #69 reconciliation files. The reconciliation can therefore remain a minimal state/evidence-only branch update without a history rewrite or unrelated code rebase.

## Canonical changes missing from the prior state snapshot

The pre-reconciliation `PROJECT_STATE.md` / `.cybercore/project.yaml` snapshot described PR #55 / WB-0034 as active and `d74497e...` as last verified main. GitHub canonical reality has advanced materially.

Relevant merged work now includes:

- PR #55 — WB-0034 first staging deployment preflight — merged as `090433264f4338828db293a327d5083bacf1813f`;
- PR #63 — WB-0034 path-scoped explicit FTPS security amendment — merged as `2f8b5b54ba8745871dd3a183c739a32473e8535a`;
- PR #64 — bounded FTPS runtime and effect verifier — merged as `f12eb91ea8dd718f9f3c2d366d578859dab31132`;
- PR #68 — Cyber Voice Foundation — merged as `bb18ffedff43970e27fdd0e86ffeb469a8d465de`;
- PR #65 — first-write recovery/runtime safety hardening — merged as `f245e89030a573ae3594a44ad42a828245bb2bba`;
- PR #70 — Cyber Voice Realtime Foundation — merged as `65682cbe2f129048ea6c672107c3208d44cbe4ea`;
- PR #66 — WB-LR0001 Durable autonomous LongRun runtime — merged as current `main@1ada318abcd93c7980cc6adc975afb0decefbbec`.

PR #65 exact approved head was `e239ce48cb18a7152adcaa006b8cc74c49c646f2`; CI #585 and CodeQL #584 passed and the fresh exact-head Codex review completed before merge.

## Current canonical capabilities added after the initial PR #69 draft

### PR #70 — Cyber Voice Realtime Foundation

Canonical state now includes provider-neutral realtime/audio contracts, bounded audio buffers, provider-neutral VAD/STT/TTS/transport protocols, a realtime voice state machine, speech-driven barge-in, and an STT bridge into the existing governed `Utterance` path.

The merge does not introduce direct shell/GitHub/provider execution, deployment, production mutation, recording persistence, or new credential authority.

### PR #66 — Durable LongRun runtime

Canonical state now includes the first bounded 16h+ durable LongRun control-plane slice: immutable mission manifest/digest, SQLite durable state and append-only event ledger, fail-closed governor, watchdog controls, deterministic resumability, MARATHON-16 benchmark profile, and ADR-0007.

The merge explicitly does not grant production writes, credential/permission/billing mutation, remote deployment, provider binding, or distributed queue infrastructure.

## Current safety boundary

- First-write remote mutation remains `BLOCKED`.
- The bounded FTPS writer cannot safely prove atomic no-overwrite under concurrency.
- PR #65 recovery is read-only and MLST-only; it performs no delete, rename, upload, chmod or chown.
- A future live staging write requires a separately reviewed atomic create-if-absent mechanism or independently verified exclusive mutation access plus fresh explicit operator authority.
- Production mutation remains outside current authority.
- PR #69 does not authorize any execution path introduced or proposed by LongRun, Cyber Voice, MCP, PR #71, or stale provider work.

## Google Drive reconciliation

Connected Drive inspection resolved `CyberCore/CASER-E` with `working/` and `evidence/` subfolders. `working/` still contains the older `CyberCore Audit 2026-08-17 — Working`.

The native Google Doc `CyberCore SOT Reconciliation — post PR65 / PR68` was created, read back, and verified in `CASER-E/evidence`. Provider-private Drive identifiers are intentionally not committed to this repository.

The earlier machine-readable state incorrectly retained `caser_e_evidence_mirror: reconciliation_pending` and instructed operators to create a mirror that already existed. PR #69 now corrects that state to `verified_noncanonical` and removes the duplicate mirror action from the `next` queue.

The Drive artifact remains an evidence mirror only. GitHub `main` remains canonical product state.

## Open pull-request reality

Current open CyberCore PRs observed during this reconciliation:

- #71 — `feat(wb0037): governed execution bridge v1` — open/non-draft candidate; base is historical `wb-0036-cyber-voice-foundation`, not canonical `main`;
- #69 — this source-of-truth reconciliation candidate;
- #67 — CyberCore MCP Foundation v0.1 — draft candidate created from an older main and requiring current-main reconciliation;
- #61 — old draft `WB-0035` InterServer VPS + Vikunja plan — historical identity collision; no provider order/payment action is authorized by this reconciliation;
- #45 — old staging-plan candidate — stale/supersession review required;
- #13 — old structured registry v0 draft — stale/supersession review required;
- #5 — old provider-framework draft — stale/supersession review required.

PR #66 is no longer open; it is merged and canonical. No unrelated open PR is merged, closed, renumbered, rebased, deployed, or provider-executed by this reconciliation.

## Identity conflicts

### WB-0035 — CONFLICT / NEEDS_REVIEW

The identifier is used by both:

- merged PR #64 — bounded FTPS runtime/effect verifier; and
- open draft PR #61 — InterServer VPS + Vikunja plan.

Do not treat these as one work block. Historical provenance must be preserved; future cleanup requires an explicit naming/supersession decision.

### WB-0036 — CONFLICT / NEEDS_REVIEW

The identifier is used by both merged changes:

- PR #65 — first-write recovery/runtime safety hardening; and
- PR #68 — Cyber Voice Foundation.

Both are canonical Git history. Do not rewrite history to hide the collision. A later governance cleanup should assign unambiguous registry aliases/identities while preserving original PR titles and commit provenance.

### WB-0037 — CONFLICT / NEEDS_REVIEW

The identifier is now used by two distinct tracks:

- merged PR #70 — Cyber Voice Realtime Foundation; and
- open PR #71 — governed execution bridge v1.

PR #71 also targets a non-canonical historical base. It requires canonical-base reconciliation and an explicit identity cleanup before any merge decision. This evidence record does not rename or rewrite either history.

## Reconciliation decision

Current canonical state must reflect `main@1ada318abcd93c7980cc6adc975afb0decefbbec`, PR #70 and PR #66 as merged canonical work, the verified non-canonical CASER-E mirror, and the newly observed WB-0037 collision.

Priority order after this reconciliation candidate:

1. run exact-head CI, CodeQL and a fresh independent review for PR #69; merge only with separate explicit operator approval;
2. reconcile/revalidate PR #67 MCP Foundation against current canonical main;
3. reconcile PR #71 against canonical main and resolve the WB-0037 collision before any merge decision;
4. resolve WB-0035/WB-0036/WB-0037 collisions and stale PRs (#61, #45, #13, #5) through explicit supersession/renumber/closure decisions;
5. start a separate engineering block for concurrency-safe first-write semantics before requesting any live staging-write authority.
