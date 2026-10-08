# CyberCore Project State

_Last updated: 2026-10-08_

## Source of truth

- Repository: `cyberDJs/CyberCore`
- Canonical product state: GitHub `main`
- Canonical main ref: GitHub `main` (resolve live)
- Last verified canonical checkpoint: `6c4aa8507257cad1cd615915a3ae9613f55a8103`
- Evidence/archive/collaboration layer: Google Drive `CyberCore/CASER-E`
- Current coordination artifact: none — repository is intentionally idle
- Current coordination branch: none
- Current coordination pull request: none
- Active branch: none
- Active work block: none
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

PR #79 remains immutable canonical history with four unresolved historical review threads, but the underlying defects are now repaired by canonical PR #95. The old review threads remain provenance; they no longer describe the current `main` implementation.

## Current milestone

Repository governance is reconciled to live GitHub through `main@6c4aa8507257cad1cd615915a3ae9613f55a8103`. There is no active pull request and no implicitly selected successor work block.

Recent canonical merges after the previous 2026-09-29 state snapshot:

- PR #104 — WB-0038H post-merge source-of-truth closeout — merged as `79bfd510ad9048bd168e3b1cb4ef0068de1e36d6`;
- PR #109 — Slack ingress bridge for Plus clients — merged as `7def417b8a8e9e25f53fb1f6a627c7b2a9c7efea`;
- PR #99 — WB-0039 Cyber Voice Intelligence Bridge forward-port — merged as `25874ece2019fbdf77db783f6c97204a976b0675`;
- PR #100 — WB-0038F-R2 evidence-only reconciliation — merged as `b2ef9088728930707cd9bad3dd5cd33e855c5480`;
- PR #110 — current-main Vikunja/VPS planning reset — merged as `6c4aa8507257cad1cd615915a3ae9613f55a8103`.

Exact current-main verification observed on 2026-10-08:

- CI on `6c4aa8507257cad1cd615915a3ae9613f55a8103`: PASS;
- CodeQL on the same SHA: PASS;
- Python 3.11 / 3.12 / 3.13 / 3.14 test jobs: PASS;
- quality: PASS;
- package: PASS;
- pre-reconciliation live open pull requests: 0; while this candidate PR #111 is open, live count is 1; after merge/close the intended canonical idle count is 0.

## Active objective

None. The repository is intentionally idle after reconciliation. New work must start as an explicit separately-scoped artifact from live `main`; historical draft branches and old approvals are not current authority.

## Current status

- Work block: none / IDLE
- Active branch: none
- Active pull request: none
- Canonical main: `6c4aa8507257cad1cd615915a3ae9613f55a8103`
- PR #104: merged canonical
- PR #99: merged canonical
- PR #100: merged canonical, evidence-only reconciliation
- PR #109: merged canonical
- PR #110: merged canonical
- Runtime deployment authority: not granted
- Staging application write authority: not granted
- Production mutation authority: not granted
- Source-of-truth drift identified on 2026-10-08: reconciled by this repository-only candidate

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
- PR #79 — WB-0038C governed bootstrap artifact — merged as `6293a31bac00c2f833e6eb5131eeafdafd9acc0a`; historical review debt was repaired by PR #95;
- PR #75 — WB-0038A Cyber Voice live audio acceptance repair — merged as `70ccecc719e004767412cdf2e2cb51cf43fb8ff6`;
- PR #83 — WB-0040 governed runner v1 — merged as `9363324a1ae19473fe02e8a5f680321c44915600`;
- PR #91 — atomic STOU staging preview writer — merged as `1f26d57fc46e35d64043ad0b1e2dd2f12b2ac37b`;
- PR #90 — governed Cloudflare DNS provider v0.1 — merged as `0ec2e00449e65e9750ab2eb75710dd8a02486068`;
- PR #87 — WB-0038B local barge-in shadow evidence probe — merged as `a2eff9b00df678573e5ed148f647d72cdb576140`;
- PR #93 — Sarah/WEDOS authoritative-DNS documentation — merged as `ffc2c582e1f2c0301a373f7d9d6e0b771b4d9441`;
- PR #78 — WB-LR0004 Provider Model Binding — merged as `bb5fecce19aa7bf6ac0edaf0f780ff6364d020f1`;
- PR #95 — WB-0038E execution-boundary repair — merged as `3884f6b605a1fb3b0003b142044485cb9ba6ecce`;
- PR #96 — PR #95 post-merge source-of-truth closeout — merged as `1a22865747d0d8ea2bf97d3b455534b610a66a90`;
- PR #102 — WB-0038G consolidated rollback repair — merged as `b6c350ef40d21a3939fd0d3d6c0187a934303d31`; post-merge CI #975 PASS and CodeQL #976 PASS;
- PR #103 — WB-0038H canonical rollback hardening — merged as `336ee555faabec76bd9114844954260b47b09570`; exact-head CI #989 PASS, CodeQL #990 PASS, fresh Codex review clean, unresolved review threads 0; post-merge CI #990 PASS and CodeQL #991 PASS.
- Current verified main checkpoint: `6c4aa8507257cad1cd615915a3ae9613f55a8103` (merge PR #110); historical merge identities and authority boundaries remain unchanged.

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

PR #79 added a server/bootstrap side for the future `cybercore-exec` boundary. PR #95 repaired its protocol, authorization, timeout, privilege, receipt and rollback contracts and is now canonical.

The repository contract is therefore repaired, but runtime deployment readiness is still not implied: no subsystem deployment, SSH identity/credential installation, live Polkit/sshd mutation, production authorization verifier, or Vikunja mutation was performed. Those remain separately approval-gated.

## Current parallel candidate tracks

### PR #75 — WB-0038A Cyber Voice live audio acceptance repair

- State: `MERGED / CANONICAL`.
- Merge commit: `70ccecc719e004767412cdf2e2cb51cf43fb8ff6`.
- The repair preserves the existing Voice authority boundary and does not grant deployment or production mutation authority.

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

No merge priority is inferred merely from PR number or recency; each candidate must be independently reconciled and gated. The former PR #79 repair priority is historical: its implementation findings were repaired by canonical PR #95.

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

Immediately before this reconciliation branch/PR was created, live GitHub reported **0 open pull requests**. During review, PR #111 is the sole open pull request; after it is merged or closed, the intended canonical idle state returns to **0**.

Historical candidates previously listed as open are now resolved as follows:

- PR #104 — merged canonical;
- PR #100 — merged as evidence-only reconciliation;
- PR #99 — merged canonical WB-0039 forward-port;
- PR #98 — closed/unmerged historical source evidence;
- PR #74 — closed/unmerged historical predecessor of merged PR #99;
- PR #67 — closed/unmerged historical MCP candidate; any revival requires a new current-main work item;
- PR #61 — closed/unmerged historical Vikunja candidate; superseded for planning purposes by merged PR #110.

No closed branch or historical approval is current execution authority.

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

Merged PR #79 still has four unresolved historical review threads in its own discussion history. Their underlying implementation findings were repaired by PR #95; the threads remain preserved as provenance rather than being rewritten as if they never existed.

Open PR #94 contains one unique response-hardening delta not included in PR #95: remote clients receive a fixed request-validation failure string rather than internal parser/authorization detail. That should be extracted into a minimal current-main change before PR #94 is superseded.

## Priority sequence

No successor is activated by this reconciliation. Current backlog candidates, requiring explicit selection before work starts:

1. resolve WB-0035 / WB-0036 / WB-0037 identifier collisions without rewriting immutable history;
2. review and remediate the six high-severity transitive visual-toolchain npm findings;
3. extract and re-evaluate any still-unique request-validation response sanitizer from historical PR #94 against current `main`;
4. design concurrency-safe first-write semantics before requesting staging application write authority;
5. reconcile stale historical GitHub issues and close only those proven completed or superseded;
6. continue Nextcloud issue #62 recoverability proof before any production remediation;
7. refresh the non-canonical CASER-E mirror after this reconciliation is canonical.

## Next action

Remain IDLE until an explicit next work item is selected. This reconciliation does not authorize merge of itself, deployment, SSH/VPS mutation, DNS/provider/billing actions, credential changes, staging application writes, or production mutation.

<!-- CYBERCORE:CHECKPOINT:START -->
<!-- CYBERCORE:PROJECT-STATE-CHECKPOINT:idle-current-main-reconciled -->
## Manual repository checkpoint

- Canonical main: `6c4aa8507257cad1cd615915a3ae9613f55a8103`
- Open pull requests before reconciliation: 0
- Reconciliation candidate during review: PR #111 only
- Intended canonical open pull requests after PR #111 closes: 0
- Coordination artifact: none / IDLE
- PR #104: merged canonical as `79bfd510ad9048bd168e3b1cb4ef0068de1e36d6`
- PR #99: merged canonical as `25874ece2019fbdf77db783f6c97204a976b0675`
- PR #100: merged evidence-only reconciliation as `b2ef9088728930707cd9bad3dd5cd33e855c5480`
- PR #109: merged Slack ingress bridge as `7def417b8a8e9e25f53fb1f6a627c7b2a9c7efea`
- PR #110: merged current-main Vikunja/VPS plan reset as `6c4aa8507257cad1cd615915a3ae9613f55a8103`
- Current-main CI: PASS
- Current-main CodeQL: PASS
- Production write allowed: false
- Staging application write allowed: false
- Secret values recorded: false
- WB-0035 / WB-0036 / WB-0037 identifier collisions: OPEN governance debt
- Visual toolchain security debt: 6 high-severity transitive npm findings / OPEN
- Google Drive CASER-E mirror: NON-CANONICAL / requires refresh after canonical reconciliation
<!-- CYBERCORE:CHECKPOINT:END -->
