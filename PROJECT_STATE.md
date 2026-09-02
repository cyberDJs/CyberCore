# CyberCore Project State

_Last updated: 2026-09-02_

## Source of truth

- Repository: `cyberDJs/CyberCore`
- Canonical product state: GitHub `main`
- Current canonical main: `1ada318abcd93c7980cc6adc975afb0decefbbec`
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
- PR #66 — WB-LR0001 Durable autonomous LongRun runtime — merged as current `main@1ada318abcd93c7980cc6adc975afb0decefbbec`.

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

Production mutation remains prohibited without a separate production MOP and explicit authority. No current reconciliation, LongRun, MCP, Cyber Voice, governed-execution, or staging work grants production authority.

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

PR #70 still does not grant direct shell/GitHub/provider execution, deployment, production mutation, recording persistence, or new credential authority.

## Current parallel candidate tracks

### PR #67 — CyberCore MCP Foundation v0.1

- State: `OPEN / DRAFT / CANDIDATE`.
- Purpose: read-only stdio MCP foundation with explicit bounded tools and fail-closed capability declaration.
- Explicitly excludes arbitrary shell, deploy, provider/cloud mutation and production write.
- The branch was created from an older canonical main and requires reconciliation against current `main@1ada318abcd93c7980cc6adc975afb0decefbbec` plus fresh exact-head gates before readiness.

### PR #71 — WB-0037 governed execution bridge v1

- State: `OPEN / NON-DRAFT / CANDIDATE / NEEDS_REVIEW`.
- Purpose: constrained SSH execution transport for bounded already-approved actions without exposing a general-purpose remote shell.
- PR base is `wb-0036-cyber-voice-foundation@3e8c757485db17ffcdfc70504d8e0e9bda5b4a87`, not canonical `main`.
- It requires canonical-base reconciliation, exact-head revalidation, and resolution of the WB-0037 identifier collision before any merge decision.
- This PR #69 reconciliation does not authorize deployment, VPS mutation, secret creation, arbitrary shell, arbitrary sudo, or arbitrary hosts.

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

The identifier is now used by two distinct tracks:

- merged PR #70 — Cyber Voice Realtime Foundation;
- open PR #71 — governed execution bridge v1.

PR #71 additionally targets a non-canonical historical base. Do not merge the two meanings or rewrite history; later governance cleanup must assign unambiguous identities before PR #71 can be considered ready.

## Open pull-request inventory

At the current reconciliation read, open PRs are:

- #71 — governed execution bridge v1 — candidate, non-canonical base, WB-0037 collision / needs review;
- #69 — current source-of-truth reconciliation candidate;
- #67 — MCP Foundation — draft candidate requiring current-main reconciliation;
- #61 — old WB-0035 VPS/Vikunja draft — identity conflict / needs review;
- #45 — old staging-plan candidate — stale/supersession review required;
- #13 — old structured registry v0 draft — stale/supersession review required;
- #5 — old provider-framework draft — stale/supersession review required.

PR #66 is no longer a candidate: it is merged and canonical. This reconciliation does not close, merge, rename, rebase, deploy, or provider-execute any unrelated PR.

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

## Priority sequence

1. Verify PR #69 on its new exact head with CI, CodeQL and fresh independent review; merge only after separate explicit operator approval.
2. Reconcile/revalidate PR #67 MCP Foundation against the resulting canonical main before readiness.
3. Reconcile PR #71 against canonical main and resolve the WB-0037 identity collision before any merge decision.
4. Resolve WB-0035/WB-0036/WB-0037 identifier collisions and stale PRs through explicit supersession/renumber/closure decisions; do not rewrite history.
5. Start a separate engineering block for concurrency-safe first-write semantics before any future staging-write authorization request.

<!-- CYBERCORE:CHECKPOINT:START -->
<!-- CYBERCORE:PROJECT-STATE-CHECKPOINT:pr69-current-sot-reconciliation -->
## Manual repository checkpoint

- Coordination PR: #69
- Coordination branch: `docs/post-pr65-pr68-sot-reconciliation`
- Canonical base observed for reconciliation: `1ada318abcd93c7980cc6adc975afb0decefbbec`
- PR #65: merged and canonical
- PR #68: merged and canonical
- PR #70: merged and canonical
- PR #66 LongRun: merged and canonical
- PR #67 MCP: draft candidate; current-main reconciliation required
- PR #71 governed execution bridge: candidate; non-canonical base; WB-0037 conflict / needs review
- WB-0035 identity: CONFLICT / NEEDS_REVIEW
- WB-0036 identity: CONFLICT / NEEDS_REVIEW
- WB-0037 identity: CONFLICT / NEEDS_REVIEW
- First staging remote write: BLOCKED
- Production write allowed: false
- Secret values recorded: false
- Google Drive CASER-E mirror: VERIFIED / NON-CANONICAL
<!-- CYBERCORE:CHECKPOINT:END -->
