# CyberCore Project State

_Last updated: 2026-09-02_

## Source of truth

- Repository: `cyberDJs/CyberCore`
- Canonical product state: GitHub `main`
- Canonical main ref: GitHub `main` (resolve live)
- Last verified canonical checkpoint: `6293a31bac00c2f833e6eb5131eeafdafd9acc0a`
- Evidence/archive/collaboration layer: Google Drive `CyberCore/CASER-E`
- Current coordination artifact: none — terminal canonical state
- Current coordination branch: `main`
- Current coordination pull request: none
- Active branch: `main`
- Active work block: `none`
- Governance: provider mutation, secret mutation, staging apply, production mutation, canonical merge, and authority changes require their applicable explicit approval gates
- CI policy: exact-head GitHub Actions verification is required before merge
- CodeQL policy: exact-head CodeQL verification is required before merge
- Independent review: fresh exact-head review is required for material changes before merge readiness

GitHub `main` remains canonical. `Last verified canonical checkpoint` means the last independently observed commit identity; it is not an alias for moving `main` HEAD and is not by itself a quality sign-off. CASER-E is a mirror/evidence layer and cannot override a fresher authoritative GitHub state.

### PR #69 — docs(state): reconcile current canonical state through PR72

Merged into `main` as:

```text
cb3d705f82d53a1302f9f2ca80615325b1509468
```

Completed artifact: `PR69-CURRENT-SOT-RECONCILIATION`.

Verification:

- CI #636: **PASS**.
- CodeQL #635: **PASS**.
- Fresh exact-head Codex review on `932b2a19ca3050fe22af4acd2db23de51134509d`: **completed with no new unresolved findings**.

### PR #77 — docs(state): close out PR69 after merge

Merged into `main` as:

```text
36a16e805390c8c5214eeb4646b6ecf6c8efc4aa
```

Completed artifact: `PR69-POST-MERGE-SOT-CLOSEOUT`.

Verification:

- CI #655: **PASS** on exact head `428b4acf004f48caea3d17c2e75914f0e99ac7fd`.
- CodeQL #654: **PASS** on the same exact head.
- Fresh exact-head Codex review on `428b4acf004f48caea3d17c2e75914f0e99ac7fd`: **completed with no major issues**.
- Review threads before merge: **0**.

### PR #79 — feat(wb0038c): governed bootstrap artifact

Merged into `main` as:

```text
6293a31bac00c2f833e6eb5131eeafdafd9acc0a
```

Artifact: `WB-0038C-governed-bootstrap-artifact`.

Observed verification and debt:

- Final PR head: `c7bdf027000f9e0efede3cdc5ef9bfe4aecb8cb2`.
- CI #658: **PASS** on the final head.
- CodeQL #657: **PASS** on the final head.
- Four review threads remain unresolved on the merged PR.
- The final canonical code still has a protocol mismatch: the execution client emits `version: 1` while the server exact-key schema rejects `version`.
- The advertised `vikunja.backup.install` operation points at a privileged helper that the bootstrap manifest does not install.
- Mutating server operations allow 120 seconds while the supported SSH client times out after 30 seconds, leaving a possible unknown mutation outcome.
- A CodeQL clear-text sensitive-information review thread also remains unresolved.

Therefore PR #79 is **MERGED / CANONICAL / NEEDS_REPAIR**. Passing final CI and CodeQL do not erase unresolved review evidence.

## Current milestone

Canonical state is idle at checkpoint `6293a31bac00c2f833e6eb5131eeafdafd9acc0a`, with a bounded repair required for merged PR #79 before advancing another candidate track.

## Active objective

No active coordination work block. The next bounded engineering action is to repair the known PR #79 canonical findings against live GitHub `main`; only after that repair becomes canonical should another candidate track be selected.

Scope:

1. keep terminal post-merge closeout as a transaction that may end in idle state instead of making a state-maintenance PR its own successor artifact;
2. repair PR #79 protocol-version compatibility, missing privileged-helper contract, transport/server timeout mismatch, and the unresolved sensitive-output finding;
3. require exact-head tests, CI, CodeQL and fresh independent review for that repair before any readiness decision;
4. preserve all existing authority, security, staging and production boundaries;
5. refresh the non-canonical CASER-E mirror separately after terminal-closeout maintenance becomes canonical.

## Current status

- Work block: idle with canonical repair required
- Branch: `main`
- Project Kernel: present
- Runtime implementation: canonical state; terminal post-merge closeout maintenance is under review
- Tests: canonical PR #79 head passed CI #658 and CodeQL #657, but unresolved review findings remain open
- Pull request: none

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
- PR #71 — WB-0037 governed execution bridge v1 — merged as `111ef0f09f44894278499d9ffaca9ab18eccf404`;
- PR #72 — WB-LR0002 LongRun Operator Runtime — merged as `8b555ffad19d44e8badff457d754efdb91e0bca8`;
- PR #69 — source-of-truth reconciliation — merged as `cb3d705f82d53a1302f9f2ca80615325b1509468`;
- PR #76 — WB-LR0003 Independent Evaluation Acceptance — merged as `41a0994b3cef083f15b8280724dd788cd31a880e`;
- PR #77 — PR #69 post-merge source-of-truth closeout — merged as `36a16e805390c8c5214eeb4646b6ecf6c8efc4aa`;
- PR #79 — WB-0038C governed bootstrap artifact — merged as current observed checkpoint `6293a31bac00c2f833e6eb5131eeafdafd9acc0a`, with unresolved repair debt recorded above.

These records do not retroactively broaden authority granted to any merged work block. A merged artifact can remain canonical while also carrying explicitly recorded defects that require a follow-up repair.

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

Production mutation remains prohibited without a separate production MOP and explicit authority. No current reconciliation, LongRun, MCP, Cyber Voice, governed execution, bootstrap, or staging work grants production authority.

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

PR #72 established the operator-facing LongRun runtime as canonical state. It adds strict YAML mission/profile loading to immutable `LongRunManifest`, safe `run_id` handling, repo-sandboxed SQLite state, `longrun start|resume|status|events`, durable event-ledger inspection, deterministic read-only repository-integrity evidence, and fail-closed useful-work exhaustion.

PR #72 does not grant model/provider binding, independent evaluator authority, production writes, credential/permission/billing mutation, deployment/runtime promotion, branch-protection changes, or distributed queue infrastructure. Its deterministic harness cannot impersonate the independent evaluator.

PR #76 established Independent Evaluation Acceptance as canonical state. LongRun completion now requires successful execution plus a valid independent evaluator `PASS`, score meeting the manifest threshold, matching evaluator/executor evidence digest, and the configured minimum wall budget. The canonical merge also preserves fail-closed handling for missing evaluator/evidence, invalid evaluator output, evidence-digest mismatch and a deterministic operator judge that cannot impersonate mission acceptance.

PR #76 explicitly adds no model/provider binding, network execution, production writes, credential/permission/billing mutation, deployment/runtime promotion, or branch-protection changes.

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

PR #79 added a server/bootstrap side for the future `cybercore-exec` boundary, but the unresolved defects listed above mean the new client/server path is not yet accepted as operationally ready. No VPS mutation or deployment authority is granted by that merge.

## Current parallel candidate tracks

### PR #75 — WB-0038A Cyber Voice live audio acceptance repair

- State: `OPEN / DRAFT / CANDIDATE`.
- Purpose: repair native-rate microphone capture and synchronous-TTS overflow/barge-in handling exposed by the first physical acceptance run.
- Current branch was based on `main@8b555ffad19d44e8badff457d754efdb91e0bca8` and therefore requires reconciliation against live GitHub `main` plus fresh exact-head verification before readiness.
- Explicitly leaves Voice approval/execution authority, model downloads, deployment and production configuration unchanged.

### PR #74 — WB-0039 Cyber Voice Intelligence Bridge

- State: `OPEN / DRAFT / CANDIDATE`.
- Purpose: model-backed interpretation and general-knowledge response without moving approval or execution authority into the model.
- Current branch was based on `main@111ef0f09f44894278499d9ffaca9ab18eccf404` and therefore requires reconciliation against live GitHub `main` plus fresh exact-head verification before readiness.
- Explicitly excludes shell, SSH, GitHub, Slack, Drive, browser and infrastructure execution, automatic model downloads, cloud credentials, persistence and new approval authority.

### PR #67 — CyberCore MCP Foundation v0.1

- State: `OPEN / DRAFT / CANDIDATE`.
- Purpose: read-only stdio MCP foundation with explicit bounded tools and fail-closed capability declaration.
- Explicitly excludes arbitrary shell, deploy, provider/cloud mutation and production write.
- The branch was created from `main@f12eb91ea8dd718f9f3c2d366d578859dab31132` and requires reconciliation against live GitHub `main` plus fresh exact-head gates before readiness.

No merge priority is inferred merely from PR number or recency; each candidate must be independently reconciled and gated. The known canonical PR #79 repair takes precedence because it addresses defects already present on `main`.

## Work-block identity conflicts

### WB-0035 — `CONFLICT / NEEDS_REVIEW`

The identifier currently refers to two distinct histories:

- merged PR #64 — bounded FTPS runtime/effect verifier;
- open draft PR #61 — InterServer VPS + Vikunja plan.

These are not one work block. PR #61 is historical/stale until an explicit supersession or renumbering decision is made. Its older provider-order authority must not be treated as current execution authority without fresh preflight and explicit scope confirmation.

### WB-0036 — `CONFLICT / NEEDS_REVIEW`

The identifier is present in two separate merged canonical changes:

- PR #65 — first-write recovery/runtime safety hardening;
- merged PR #68 — Cyber Voice Foundation.

Both must remain in immutable Git history. Governance cleanup must add unambiguous aliases/registry identities rather than rewriting historical commits or PR titles.

### WB-0037 — `CONFLICT / NEEDS_REVIEW`

The identifier is now used by two distinct merged canonical tracks:

- PR #70 — Cyber Voice Realtime Foundation;
- PR #71 — governed execution bridge v1.

Do not merge the two meanings or rewrite history; governance cleanup must assign unambiguous registry identities while preserving both original PR titles and commit provenance.

## Open pull-request inventory

At the current observed checkpoint, open PRs requiring separate review include:

- #75 — WB-0038A Cyber Voice live audio acceptance repair — draft candidate requiring live-main reconciliation;
- #74 — WB-0039 Cyber Voice Intelligence Bridge — draft candidate requiring live-main reconciliation;
- #67 — MCP Foundation — draft candidate requiring live-main reconciliation;
- #61 — old WB-0035 VPS/Vikunja draft — identity conflict / needs review;
- #45 — old staging-plan candidate — stale/supersession review required;
- #13 — old structured registry v0 draft — stale/supersession review required;
- #5 — old provider-framework draft — stale/supersession review required.

PR #69, PR #76, PR #77 and PR #79 are merged and no longer open coordination candidates. This terminal-state maintenance does not close, merge, rename, rebase, deploy, or provider-execute any unrelated PR.

## CASER-E evidence state

Connected Google Drive inspection previously resolved `CyberCore/CASER-E/working` and `CyberCore/CASER-E/evidence`.

The native Google Doc `CyberCore SOT Reconciliation — post PR65 / PR68` remains non-canonical evidence and predates the PR #69, PR #76, PR #77 and PR #79 merges. It is therefore stale relative to live GitHub `main`.

Refresh the CASER-E mirror only after terminal-closeout maintenance becomes canonical, so the mirror tracks a stable governance contract rather than a candidate branch. Provider-private Drive identifiers remain intentionally absent from GitHub.

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

Separately, merged PR #79 has four unresolved review threads, including a sensitive-output CodeQL thread and three functional findings described above. These remain open canonical repair debt; this maintenance change does not suppress or resolve them.

## Priority sequence

1. Repair the canonical PR #79 WB-0038C findings in a separate bounded branch and require tests, exact-head CI, CodeQL and fresh independent review before merge readiness.
2. Only after that repair becomes canonical, select one bounded candidate among PR #75, PR #74 and PR #67 and reconcile it against live GitHub `main`; no merge priority is implied by recency.
3. Resolve WB-0035/WB-0036/WB-0037 identifier collisions and stale PRs through explicit supersession/renumber/closure decisions; do not rewrite history.
4. Address the six high-severity transitive visual-toolchain `npm audit` findings in a separately reviewed maintenance change.
5. Start a separate engineering block for concurrency-safe first-write semantics before any future staging-write authorization request.
6. Refresh the verified non-canonical CASER-E evidence mirror after terminal-closeout maintenance becomes canonical.

## Next action

Finish review of the terminal post-merge closeout contract, then repair the known PR #79 canonical findings against live GitHub `main`. Do not merge either change without its own exact-head gates and explicit operator approval.

<!-- CYBERCORE:CHECKPOINT:START -->
<!-- CYBERCORE:PROJECT-STATE-CHECKPOINT:terminal-post-merge-closeout -->
## Manual repository checkpoint

- Coordination PR: none
- Coordination branch: `main`
- Canonical main ref: GitHub `main` / resolve live
- Last observed canonical checkpoint: `6293a31bac00c2f833e6eb5131eeafdafd9acc0a`
- PR #69 SOT reconciliation: merged as `cb3d705f82d53a1302f9f2ca80615325b1509468`
- PR #76 LongRun Independent Evaluation Acceptance: merged as `41a0994b3cef083f15b8280724dd788cd31a880e`
- PR #77 post-merge SOT closeout: merged and gated as `36a16e805390c8c5214eeb4646b6ecf6c8efc4aa`
- PR #79 governed bootstrap artifact: merged as `6293a31bac00c2f833e6eb5131eeafdafd9acc0a`; CI #658 PASS; CodeQL #657 PASS; 4 unresolved review threads / NEEDS_REPAIR
- PR #75 Cyber Voice live audio acceptance repair: open draft candidate; live-main reconciliation required
- PR #74 Cyber Voice Intelligence Bridge: open draft candidate; live-main reconciliation required
- PR #67 MCP: open draft candidate; live-main reconciliation required
- WB-0035 identity: CONFLICT / NEEDS_REVIEW
- WB-0036 identity: CONFLICT / NEEDS_REVIEW
- WB-0037 identity: CONFLICT / NEEDS_REVIEW
- Visual toolchain security debt: 6 high-severity transitive npm findings / OPEN
- First staging remote write: BLOCKED
- Production write allowed: false
- Secret values recorded: false
- Google Drive CASER-E mirror: VERIFIED / NON-CANONICAL / STALE RELATIVE TO LIVE MAIN
<!-- CYBERCORE:CHECKPOINT:END -->