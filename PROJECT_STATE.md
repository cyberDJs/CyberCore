# CyberCore Project State

_Last updated: 2026-09-02_

## Source of truth

- Repository: `cyberDJs/CyberCore`
- Canonical product state: GitHub `main`
- Current canonical main: `f245e89030a573ae3594a44ad42a828245bb2bba`
- Evidence/archive/collaboration layer: Google Drive `CyberCore/CASER-E`
- Current coordination artifact: post-PR65/PR68 source-of-truth reconciliation
- Current coordination branch: `docs/post-pr65-pr68-sot-reconciliation`
- Current coordination pull request: #69
- Governance: provider mutation, secret mutation, staging apply, production mutation, canonical merge, and authority changes require their applicable explicit approval gates
- CI policy: exact-head GitHub Actions verification is required before merge
- CodeQL policy: exact-head CodeQL verification is required before merge
- Independent review: fresh exact-head review is required for material changes before merge readiness

GitHub `main` remains canonical. CASER-E is a mirror/evidence layer and cannot override a fresher authoritative GitHub state.

## Current canonical milestone

The stale WB-0034 / PR #55 snapshot has been superseded by later canonical merges.

Most relevant recent merged state:

- PR #55 — WB-0034 first staging deployment preflight — merged as `090433264f4338828db293a327d5083bacf1813f`;
- PR #63 — WB-0034 path-scoped explicit FTPS security amendment — merged;
- PR #64 — bounded FTPS runtime and effect verifier — merged as `f12eb91ea8dd718f9f3c2d366d578859dab31132`;
- PR #68 — Cyber Voice Foundation — merged as `bb18ffedff43970e27fdd0e86ffeb469a8d465de`;
- PR #65 — first-write recovery/runtime safety hardening — merged as current `main@f245e89030a573ae3594a44ad42a828245bb2bba`.

PR #65 was merged only after exact-head CI #585 PASS, CodeQL #584 PASS, fresh exact-head Codex review completion, and resolved review findings.

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

Production mutation remains prohibited without a separate production MOP and explicit authority. No current reconciliation, LongRun, MCP, Cyber Voice, or staging work grants production authority.

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

## Current parallel candidate tracks

### PR #66 — WB-LR0001 Durable autonomous LongRun runtime

- State: `OPEN / NON-DRAFT / CANDIDATE`
- Purpose: durable 16h+ autonomous control-plane runtime with mission digest, SQLite state/event ledger, governor, watchdog, resumability, benchmark and ADR boundary.
- Explicit exclusions include production writes, credential/billing mutation and remote deployment.
- The branch was created from an older canonical main. It requires post-PR65/PR68 base reconciliation and exact-head revalidation before any merge decision.

### PR #67 — CyberCore MCP Foundation v0.1

- State: `OPEN / DRAFT / CANDIDATE`
- Purpose: read-only stdio MCP foundation with explicit bounded tools and fail-closed capability declaration.
- Explicitly excludes arbitrary shell, deploy, provider/cloud mutation and production write.
- The branch was created from an older canonical main. It requires post-PR65/PR68 base reconciliation and exact-head revalidation before readiness.

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

## Open pull-request inventory

At the reconciliation read, open PRs were:

- #69 — post-PR65/PR68 SOT reconciliation — current coordination candidate;
- #67 — MCP Foundation — draft candidate;
- #66 — LongRun runtime — candidate;
- #61 — old WB-0035 VPS/Vikunja draft — identity conflict / needs review;
- #45 — old staging-plan candidate — stale/supersession review required;
- #13 — old structured registry v0 draft — stale/supersession review required;
- #5 — old provider-framework draft — stale/supersession review required.

This reconciliation does not close, merge, rename, rebase, or execute any of those PRs.

## Cyber Voice canonical state

PR #68 established the Cyber Voice Foundation as a governed human operating interface:

- `Utterance -> Intent -> ActionRequest` contracts;
- interruption/cancellation semantics;
- fail-closed HOWEDO continuity and OATHDO governance gateways;
- plan+revision-bound approval verification;
- voice approval intent cannot self-authorize execution;
- audit-friendly lifecycle events.

It does not add microphone/STT/TTS/wake-word handling, speaker authentication, direct shell/provider execution, deployment, or production mutation.

## CASER-E drift

Connected Google Drive inspection resolved:

- `CyberCore/CASER-E/working`
- `CyberCore/CASER-E/evidence`

`working` still contains `CyberCore Audit 2026-08-17 — Working`. At inspection time the `evidence` folder did not contain a current post-PR65/PR68 reconciliation artifact.

The current reconciliation evidence is maintained first in GitHub as `docs/evidence/2026-09-02-post-pr65-pr68-sot-reconciliation.md` and is mirrored to CASER-E as evidence. The Drive copy remains non-canonical.

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

1. Verify PR #69 exact-head CI, CodeQL and independent review; merge only after explicit operator approval.
2. Reconcile/revalidate PR #66 LongRun against the resulting canonical main.
3. Reconcile/revalidate PR #67 MCP Foundation against the resulting canonical main.
4. Resolve identifier collisions and stale PRs through explicit supersession/renumber/closure decisions; do not rewrite history.
5. Start a separate engineering block for concurrency-safe first-write semantics before any future staging-write authorization request.

<!-- CYBERCORE:CHECKPOINT:START -->
<!-- CYBERCORE:PROJECT-STATE-CHECKPOINT:pr69-post-pr65-pr68-sot-reconciliation -->
## Manual repository checkpoint

- Coordination PR: #69
- Coordination branch: `docs/post-pr65-pr68-sot-reconciliation`
- Canonical base: `f245e89030a573ae3594a44ad42a828245bb2bba`
- PR #65: merged and canonical
- PR #68: merged and canonical
- LongRun PR #66: candidate; post-merge revalidation required
- MCP PR #67: draft candidate; post-merge revalidation required
- WB-0035 identity: CONFLICT / NEEDS_REVIEW
- WB-0036 identity: CONFLICT / NEEDS_REVIEW
- First staging remote write: BLOCKED
- Production write allowed: false
- Secret values recorded: false
- Google Drive CASER-E: evidence mirror, non-canonical
<!-- CYBERCORE:CHECKPOINT:END -->
