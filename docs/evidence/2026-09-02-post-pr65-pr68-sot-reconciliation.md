# CyberCore Source-of-Truth Reconciliation

## Scope

Repository and evidence-state reconciliation only. No staging, provider, DNS, TLS, credential, billing, production, application, VPS, or remote-write mutation is authorized or performed by this change.

The initial PR #69 reconciliation was opened after PR #65 and PR #68. While review was in progress, canonical `main` advanced through PR #70, PR #66, PR #73, PR #71 and PR #72. This evidence record therefore extends the same reconciliation to the current canonical state rather than freezing an obsolete snapshot.

## Canonical source

- Repository: `cyberDJs/CyberCore`
- Canonical branch: `main`
- Canonical main observed for this reconciliation: `8b555ffad19d44e8badff457d754efdb91e0bca8`
- Google Drive `CyberCore/CASER-E`: evidence/archive/collaboration mirror, not canonical product state
- Coordination PR: #69
- Coordination branch: `docs/post-pr65-pr68-sot-reconciliation`

PR #72 did not modify the three PR #69 reconciliation files, so the reconciliation remains a minimal state/evidence-only branch update without a history rewrite or unrelated code rebase.

## Canonical changes missing from the prior state snapshot

The pre-reconciliation `PROJECT_STATE.md` / `.cybercore/project.yaml` snapshot described PR #55 / WB-0034 as active and `d74497e...` as last verified main. GitHub canonical reality has advanced materially.

Relevant merged work now includes:

- PR #55 — WB-0034 first staging deployment preflight — merged as `090433264f4338828db293a327d5083bacf1813f`;
- PR #63 — WB-0034 path-scoped explicit FTPS security amendment — merged as `2f8b5b54ba8745871dd3a183c739a32473e8535a`;
- PR #64 — bounded FTPS runtime and effect verifier — merged as `f12eb91ea8dd718f9f3c2d366d578859dab31132`;
- PR #68 — Cyber Voice Foundation — merged as `bb18ffedff43970e27fdd0e86ffeb469a8d465de`;
- PR #65 — first-write recovery/runtime safety hardening — merged as `f245e89030a573ae3594a44ad42a828245bb2bba`;
- PR #70 — Cyber Voice Realtime Foundation — merged as `65682cbe2f129048ea6c672107c3208d44cbe4ea`;
- PR #66 — WB-LR0001 Durable autonomous LongRun runtime — merged as `1ada318abcd93c7980cc6adc975afb0decefbbec`;
- PR #73 — WB-0038 Cyber Voice Local Speech Runtime — merged as `a206c5d0758fc604d0bec5fb26dfd96b33469f62`;
- PR #71 — WB-0037 governed execution bridge v1 — merged as `111ef0f09f44894278499d9ffaca9ab18eccf404`;
- PR #72 — WB-LR0002 LongRun Operator Runtime — merged as current `main@8b555ffad19d44e8badff457d754efdb91e0bca8`.

PR #65 exact approved head was `e239ce48cb18a7152adcaa006b8cc74c49c646f2`; CI #585 and CodeQL #584 passed and the fresh exact-head Codex review completed before merge.

## Current canonical capabilities added after the initial PR #69 draft

### PR #70 — Cyber Voice Realtime Foundation

Canonical state includes provider-neutral realtime/audio contracts, bounded audio buffers, provider-neutral VAD/STT/TTS/transport protocols, a realtime voice state machine, speech-driven barge-in, and an STT bridge into the existing governed `Utterance` path.

The merge does not introduce direct shell/GitHub/provider execution, deployment, production mutation, recording persistence, or new credential authority.

### PR #66 — Durable LongRun runtime

Canonical state includes the first bounded 16h+ durable LongRun control-plane slice: immutable mission manifest/digest, SQLite durable state and append-only event ledger, fail-closed governor, watchdog controls, deterministic resumability, MARATHON-16 benchmark profile, and ADR-0007.

The merge explicitly does not grant production writes, credential/permission/billing mutation, remote deployment, provider binding, or distributed queue infrastructure.

### PR #72 — LongRun Operator Runtime

Canonical state now also includes the operator-facing LongRun slice: strict YAML mission/profile loading to immutable `LongRunManifest`, repo-sandboxed SQLite state, `longrun start|resume|status|events`, durable event-ledger inspection, deterministic read-only repository-integrity evidence, safe `run_id` handling, and fail-closed useful-work exhaustion.

The merge explicitly excludes model/provider binding, independent evaluator authority, production writes, credential/permission/billing mutation, deployment/runtime promotion, branch-protection changes, and distributed queue infrastructure. The deterministic harness cannot impersonate an independent evaluator.

### PR #73 — Cyber Voice Local Speech Runtime

Canonical state now includes the local/offline speech reference runtime: read-only audio-device discovery, local PCM microphone/speaker transport, sherpa-onnx VAD/streaming STT/VITS TTS adapters, local session bridging into the governed realtime runtime, strict local model/device configuration, and voice CLI commands.

The merge explicitly excludes automatic model downloads, cloud speech credentials/endpoints, recording persistence, speaker biometrics/authentication, CASEBOOK/CASER persistence, direct shell/GitHub/provider execution, deployment and production mutation. Microphone/STT input remains untrusted intent, not identity or authority.

### PR #71 — governed execution bridge v1

Canonical state includes a constrained SSH execution transport for bounded already-approved actions with exact target, plan, revision and authorization binding, allowlisted operations, `shell=False`, execution receipts, and separation between execution receipt and independent verification.

The merge does not itself authorize deployment, VPS mutation, secret creation, arbitrary shell, arbitrary sudo, arbitrary hosts, or production mutation.

## Current safety boundary

- First-write remote mutation remains `BLOCKED`.
- The bounded FTPS writer cannot safely prove atomic no-overwrite under concurrency.
- PR #65 recovery is read-only and MLST-only; it performs no delete, rename, upload, chmod or chown.
- A future live staging write requires a separately reviewed atomic create-if-absent mechanism or independently verified exclusive mutation access plus fresh explicit operator authority.
- Production mutation remains outside current authority.
- PR #69 does not authorize any execution path introduced by LongRun, Cyber Voice, MCP, governed execution, or stale provider work.

## Google Drive reconciliation

Connected Drive inspection resolved `CyberCore/CASER-E` with `working/` and `evidence/` subfolders. `working/` still contains the older `CyberCore Audit 2026-08-17 — Working`.

The native Google Doc `CyberCore SOT Reconciliation — post PR65 / PR68` was created, read back, and verified in `CASER-E/evidence`. Provider-private Drive identifiers are intentionally not committed to this repository.

The earlier machine-readable state incorrectly retained `caser_e_evidence_mirror: reconciliation_pending` and instructed operators to create a mirror that already existed. PR #69 corrects that state to `verified_noncanonical` and removes the duplicate mirror action from the `next` queue.

The Drive artifact remains an evidence mirror only. GitHub `main` remains canonical product state. Its content must follow the current GitHub state and must not override it.

## Open pull-request reality

Current open CyberCore PRs observed during this reconciliation:

- #69 — this source-of-truth reconciliation candidate;
- #67 — CyberCore MCP Foundation v0.1 — draft candidate created from an older main and requiring current-main reconciliation;
- #61 — old draft `WB-0035` InterServer VPS + Vikunja plan — historical identity collision; no provider order/payment action is authorized by this reconciliation;
- #45 — old staging-plan candidate — stale/supersession review required;
- #13 — old structured registry v0 draft — stale/supersession review required;
- #5 — old provider-framework draft — stale/supersession review required.

PR #66, PR #71, PR #72 and PR #73 are no longer open candidates; they are merged and canonical. No unrelated open PR is merged, closed, renumbered, rebased, deployed, or provider-executed by this reconciliation.

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

The identifier is now used by two distinct merged canonical tracks:

- PR #70 — Cyber Voice Realtime Foundation; and
- PR #71 — governed execution bridge v1.

This evidence record does not rename or rewrite either history. Governance cleanup must assign unambiguous identities while preserving both original PR titles and commit provenance.

## Deferred security debt retained

Repository documentation still records six high-severity transitive `npm audit` findings in the isolated visual-documentation toolchain. They are deferred WB-0027 security debt and do not affect the Python runtime package, but they remain unresolved and require a separately reviewed pinned visual-tool dependency maintenance change.

PR #69 explicitly preserves this debt in both human-readable and machine-readable canonical state. It does not suppress, waive or mark the findings resolved.

## Reconciliation decision

Current canonical state must reflect `main@8b555ffad19d44e8badff457d754efdb91e0bca8`, PR #72 as merged canonical LongRun Operator Runtime, the verified non-canonical CASER-E mirror, the WB-0035/WB-0036/WB-0037 historical identifier collisions, and the still-open visual-toolchain security debt.

Priority order after this reconciliation candidate:

1. run exact-head CI, CodeQL and a fresh independent review for PR #69; merge only with separate explicit operator approval;
2. reconcile/revalidate PR #67 MCP Foundation against current canonical main;
3. resolve WB-0035/WB-0036/WB-0037 collisions and stale PRs (#61, #45, #13, #5) through explicit supersession/renumber/closure decisions;
4. remediate the six high-severity transitive visual-toolchain `npm audit` findings in a separately reviewed maintenance change;
5. start a separate engineering block for concurrency-safe first-write semantics before requesting any live staging-write authority.
