# CyberCore Project State

_Last updated: 2026-09-02_

## Source of truth

- Repository: `cyberDJs/CyberCore`
- Canonical product state: GitHub `main`
- Current canonical main: `111ef0f09f44894278499d9ffaca9ab18eccf404`
- Evidence/archive/collaboration layer: Google Drive `CyberCore/CASER-E`
- Current coordination artifact: PR #69 source-of-truth reconciliation
- Current coordination branch: `docs/post-pr65-pr68-sot-reconciliation`
- Current coordination pull request: #69
- Governance: provider mutation, secret mutation, staging apply, production mutation, canonical merge, and authority changes require their applicable explicit approval gates
- CI policy: exact-head GitHub Actions verification is required before merge
- CodeQL policy: exact-head CodeQL verification is required before merge
- Independent review: fresh exact-head review is required for material changes before merge readiness

GitHub `main` remains canonical. CASER-E is a mirror/evidence layer and cannot override a fresher authoritative GitHub state.

## Current canonical state

The stale WB-0034 / PR #55 snapshot has been superseded by later canonical merges.

Most relevant recent merged state:

- PR #55 — WB-0034 first staging deployment preflight — merged as `090433264f4338828db293a327d5083bacf1813f`;
- PR #63 — WB-0034 path-scoped explicit FTPS security amendment — merged as `2f8b5b54ba8745871dd3a183c739a32473e8535a`;
- PR #64 — bounded FTPS runtime and effect verifier — merged as `f12eb91ea8dd718f9f3c2d366d578859dab31132`;
- PR #68 — Cyber Voice Foundation — merged as `bb18ffedff43970e27fdd0e86ffeb469a8d465de`;
- PR #65 — first-write recovery/runtime safety hardening — merged as `f245e89030a573ae3594a44ad42a828245bb2bba`;
- PR #70 — Cyber Voice Realtime Foundation — merged as `65682cbe2f129048ea6c672107c3208d44cbe4ea`;
- PR #66 — WB-LR0001 Durable autonomous LongRun runtime — merged as `1ada318abcd93c7980cc6adc975afb0decefbbec`;
- PR #73 — WB-0038 Cyber Voice Local Speech Runtime — merged as `a206c5d0758fc604d0bec5fb26dfd96b33469f62`;
- PR #71 — WB-0037 governed execution bridge v1 — merged as current `main@111ef0f09f44894278499d9ffaca9ab18eccf404`.

PR #65 was merged only after exact-head CI #585 PASS, CodeQL #584 PASS, fresh exact-head Codex review completion, and resolved review findings. This reconciliation does not retroactively broaden any authority granted to those work blocks.

## Current safety boundary

### First staging write

`REMOTE WRITE BLOCKED`

The repository contains a bounded explicit-FTPS first-write runtime from PR #64, but PR #65 established that ordinary FTP absence checks followed by `STOR` cannot prove atomic no-overwrite under concurrent access.

Current canonical behavior therefore keeps the unsafe first-write mutation path unreachable. Read-only recovery:

- probes only the sealed canary directory and two approved artifact paths;
- uses exact-path `MLST` only;
- performs no directory enumeration;
- fails closed on ambiguous `550`, malformed replies, wrong paths/types, invalid facts, invalid control-line boundaries, or any metadata ambiguity;
- performs no `DELE`, `RMD`, rename, upload, chmod, or chown.

A future live staging write requires a separately reviewed mechanism providing either:

1. atomic create-if-absent semantics for the approved artifact contract; or
2. independently verified exclusive mutation access for the complete write interval.

Only after that evidence exists may a new exact staging-write packet and fresh operator authorization be requested.

### Production

Production mutation remains prohibited without a separate production MOP and explicit authority. No current reconciliation, LongRun, MCP, Cyber Voice, governed execution, or staging work grants production authority.

## Verified staging baseline

The existing non-production InterServer staging baseline remains valid unless superseded by new evidence:

- InterServer shared-hosting service `website_id=1439764`;
- staging hostname `staging.eimyherrer.com`;
- staging document root `/home/eimyherr/domains/staging.eimyherrer.com/public_html`;
- production document-root metadata `/home/eimyherr/domains/eimyherrer.com/public_html`;
- staging/production document-root non-overlap verified;
- Cloudflare authoritative DNS;
- staging A record DNS-only;
- HTTP/HTTPS reachability verified;
- DirectAdmin -> Cloudflare DNS-01 -> Let's Encrypt wildcard renewal path verified;
- standing unattended renewal authority remains limited to the existing wildcard certificate and existing integration.

That authority does not broaden into staging application deployment authority.

## Canonical LongRun state

PR #66 established the first bounded durable LongRun runtime as canonical state. It includes a mission manifest/digest, SQLite durable state and append-only event ledger, a fail-closed value/effect governor, watchdog controls, deterministic resumability, a MARATHON-16 profile, and ADR-0007.

Its explicit exclusions remain important: no production writes, credential/permission/billing mutation, remote deployment, provider binding, or distributed queue infrastructure is granted by the merge.

## Cyber Voice canonical state

PR #68 established the governed Cyber Voice foundation:

- `Utterance -> Intent -> ActionRequest` contracts;
- interruption/cancellation semantics;
- fail-closed HOWEDO continuity and OATHDO governance gateways;
- plan+revision-bound approval verification;
- voice approval intent cannot self-authorize execution;
- audit-friendly lifecycle events.

PR #70 added the provider-neutral realtime/audio foundation on top of that governed path:

- deterministic PCM audio contracts and bounded buffers;
- provider-neutral VAD/STT/TTS/realtime transport protocols;
- realtime voice state machine and barge-in handling;
- STT output bridged into the existing governed `Utterance` path;
- metadata-only lifecycle events by default.

PR #73 added the local/offline speech reference runtime:

- read-only audio-device discovery and compatibility validation;
- local PCM microphone/speaker transport;
- sherpa-onnx VAD, streaming STT and VITS TTS adapters;
- local session bridge into the governed realtime voice runtime;
- local JSON model/device configuration and voice CLI commands.

PR #73 explicitly excludes automatic model downloads, cloud speech credentials/endpoints, recording persistence, speaker biometrics, CASEBOOK/CASER persistence, direct shell/GitHub/provider execution, deployment and production mutation. Microphone/STT input remains untrusted intent, not authority.

## Governed execution bridge canonical state

PR #71 established WB-0037 governed execution bridge v1 as canonical state. It provides a constrained SSH transport for bounded already-approved actions with exact target, plan, revision and authorization binding, an allowlisted operation family, `shell=False`, execution receipts, and separation between execution receipt and independent verification.

The merge does not itself authorize deployment, VPS mutation, secret creation, arbitrary shell, arbitrary sudo, arbitrary hosts, or production mutation.

## Current parallel candidate tracks

### PR #72 — WB-LR0002 LongRun Operator Runtime

- State: `OPEN / NON-DRAFT / CANDIDATE`.
- Purpose: strict mission/profile loader, `longrun start|resume|status|events`, repo-sandboxed durable SQLite state, event-ledger inspection and deterministic read-only integrity harness.
- Explicitly excludes model/provider binding, independent evaluator adapter, production writes, credential/permission/billing mutation, deployment/runtime promotion, branch-protection changes and distributed queues.
- It was opened from `main@1ada318abcd93c7980cc6adc975afb0decefbbec` and therefore requires reconciliation against current `main@111ef0f09f44894278499d9ffaca9ab18eccf404` plus fresh exact-head gates before readiness.

### PR #67 — CyberCore MCP Foundation v0.1

- State: `OPEN / DRAFT / CANDIDATE`.
- Purpose: read-only stdio MCP foundation with explicit bounded tools and fail-closed capability declaration.
- Explicitly excludes arbitrary shell, deploy, provider/cloud mutation and production write.
- The branch was created from an older canonical main and requires reconciliation against current `main@111ef0f09f44894278499d9ffaca9ab18eccf404` plus fresh exact-head gates before readiness.

## Work-block identity conflicts

### WB-0035 — `CONFLICT / NEEDS_REVIEW`

The identifier currently refers to two distinct histories:

- merged PR #64 — bounded FTPS runtime/effect verifier;
- open draft PR #61 — InterServer VPS + Vikunja plan.

These are not one work block. PR #61 is historical/stale until an explicit supersession or renumbering decision is made. Its older provider-order authority must not be treated as current execution authority without fresh preflight and explicit scope confirmation.

### WB-0036 — `CONFLICT / NEEDS_REVIEW`

The identifier is present in two separate merged canonical changes:

- PR #65 — first-write recovery/runtime safety hardening;
- PR #68 — Cyber Voice Foundation.

Both must remain in immutable Git history. Governance cleanup must add unambiguous aliases/registry identities rather than rewriting historical commits or PR titles.

### WB-0037 — `CONFLICT / NEEDS_REVIEW`

The identifier is now used by two distinct merged canonical tracks:

- PR #70 — Cyber Voice Realtime Foundation;
- PR #71 — governed execution bridge v1.

Do not merge the two meanings or rewrite history; governance cleanup must assign unambiguous registry identities while preserving both original PR titles and commit provenance.

## Open pull-request inventory

At the current reconciliation read, open PRs are:

- #72 — WB-LR0002 LongRun Operator Runtime — candidate requiring current-main reconciliation;
- #69 — current source-of-truth reconciliation candidate;
- #67 — MCP Foundation — draft candidate requiring current-main reconciliation;
- #61 — old WB-0035 VPS/Vikunja draft — identity conflict / needs review;
- #45 — old staging-plan candidate — stale/supersession review required;
- #13 — old structured registry v0 draft — stale/supersession review required;
- #5 — old provider-framework draft — stale/supersession review required.

PR #66, PR #71 and PR #73 are no longer candidates: they are merged and canonical. This reconciliation does not close, merge, rename, rebase, deploy, or provider-execute any unrelated PR.

## CASER-E evidence state

Connected Google Drive inspection resolved `CyberCore/CASER-E/working` and `CyberCore/CASER-E/evidence`.

The native Google Doc `CyberCore SOT Reconciliation — post PR65 / PR68` was created, read back, and verified in `CASER-E/evidence`. It is a non-canonical evidence mirror. Provider-private Drive identifiers are intentionally not committed to GitHub.

The repository evidence record remains `docs/evidence/2026-09-02-post-pr65-pr68-sot-reconciliation.md`. GitHub `main` remains canonical product state.

## Secret-handling boundary

Plaintext secrets remain denied in:

- GitHub;
- Google Drive;
- ChatGPT Library;
- Slack;
- chat;
- CASER documents;
- ordinary evidence logs.

Secret material belongs only in an approved OS-backed secret store or approved external vault. Reconciliation records may contain safe identifiers, scopes and readiness states, never secret values.

## Security follow-up

The isolated visual-documentation toolchain still has **six high-severity transitive `npm audit` findings**. Repository documentation explicitly classifies them as deferred security debt for WB-0027; they do not affect the Python runtime package, but they remain open until the pinned visual-tool dependencies are updated in a separately reviewed maintenance change.

This reconciliation records that debt; it does not weaken, suppress, or mark the findings resolved.

## Priority sequence

1. Verify PR #69 on its new exact head with CI, CodeQL and fresh independent review; merge only after separate explicit operator approval.
2. Reconcile/revalidate PR #72 LongRun Operator Runtime against the resulting canonical main before readiness.
3. Reconcile/revalidate PR #67 MCP Foundation against the resulting canonical main before readiness.
4. Resolve WB-0035/WB-0036/WB-0037 identifier collisions and stale PRs through explicit supersession/renumber/closure decisions; do not rewrite history.
5. Address the six high-severity transitive visual-toolchain `npm audit` findings in a separately reviewed maintenance change.
6. Start a separate engineering block for concurrency-safe first-write semantics before any future staging-write authorization request.

<!-- CYBERCORE:CHECKPOINT:START -->
<!-- CYBERCORE:PROJECT-STATE-CHECKPOINT:pr69-current-sot-reconciliation -->
## Manual repository checkpoint

- Coordination PR: #69
- Coordination branch: `docs/post-pr65-pr68-sot-reconciliation`
- Canonical base observed for reconciliation: `111ef0f09f44894278499d9ffaca9ab18eccf404`
- PR #65: merged and canonical
- PR #68: merged and canonical
- PR #70: merged and canonical
- PR #66 LongRun: merged and canonical
- PR #73 Cyber Voice Local Speech Runtime: merged and canonical
- PR #71 governed execution bridge: merged and canonical
- PR #72 LongRun Operator Runtime: open candidate; current-main reconciliation required
- PR #67 MCP: draft candidate; current-main reconciliation required
- WB-0035 identity: CONFLICT / NEEDS_REVIEW
- WB-0036 identity: CONFLICT / NEEDS_REVIEW
- WB-0037 identity: CONFLICT / NEEDS_REVIEW
- Visual toolchain security debt: 6 high-severity transitive npm findings / OPEN
- First staging remote write: BLOCKED
- Production write allowed: false
- Secret values recorded: false
- Google Drive CASER-E mirror: VERIFIED / NON-CANONICAL
<!-- CYBERCORE:CHECKPOINT:END -->
