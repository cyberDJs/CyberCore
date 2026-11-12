# CyberCore seven-Skill autonomy workflow — review candidate

**Status:** Draft only; not a runtime installation, standing grant, or production change.  
**Target:** `cyberDJs/CyberCore`; canonical successor of PR #159. Canonical main remains the only source of truth.  
**Selection:** exactly the seven real ChatGPT Skills selected through strict `/skillset` routing and approved by the operator.  
**Machine-readable contract:** `configs/autonomy/cybercore-skillset.yaml`.

## Why this uses existing components

CyberCore already contains CASER preflight, CI snapshot reconciliation, Action Kernel authorization,
a real pinned CyberHIVE dry-run contract, and a proposed durable LongRun boundary (ADR-0007).
The autonomy UX contract defines compact reporting and an hourly ChatGPT change monitor.
Do not add a second scheduler, change LongRun runtime, or widen Action Kernel permissions.

The workflow **composes human/agent practices**; the YAML is not executable by CyberCore until
a separately reviewed runtime adapter and authority exist.

## Producer → consumer contracts

| Order | Exact Skill | Input | Output | Failure |
|---|---|---|---|---|
| 1 | `cyberdjs-portfolio-index` | project scope, live repo refs | canonical lane, parallel work, cleanup candidates | drift/ambiguity → stop and classify |
| 2 | `github-repo-auditor` | canonical lane, repo evidence | authoritative repo snapshot, CI/review evidence | missing evidence → UNKNOWN |
| 3 | `caser` | approved scope, snapshot, risks | bounded plan, receipts, exact HEAD | retry ≤3 per root cause, otherwise block |
| 4 | `cyberdjs-github-workflow` | bounded plan, exact HEAD, authority | scoped branch/PR actions, workflow evidence | permission or drift → stop |
| 5 | `systematic-debugging-and-root-cause-engineer` | failing gates/findings | proven root cause, minimal fix, regression evidence | unproven cause → no speculative fix |
| 6 | `cyberdjs-github-workflow` *(reused)* | minimal fix, prior HEAD, drift/ownership | repaired-or-rechecked exact HEAD + fresh workflow evidence | drift/failed recheck → stop/replan |
| 7 | `adversary-lens` | post-repair candidate, security boundaries | independent security findings, residual risk | P1/P2 → blocked |
| 8 | `release-change-manager` | post-repair verification, residual risk, authority | GO / HOLD / merge readiness / effect plan | missing authority/evidence → HOLD |

There are still exactly **seven selected Skills**; the GitHub workflow Skill is intentionally reused for
the repair/recheck node. A diagnosed `minimal_fix` never flows directly to security/release. It must
return through the write/recheck boundary, revalidate drift/ownership, and produce a freshly verified
exact HEAD and workflow evidence. When no fix is required, that node is a no-op write-wise but still
performs the identity/drift recheck before forwarding evidence.

Debugging and security verification are logically separate from the builder path. Release readiness
consumes only post-repair/recheck evidence and must not infer security PASS from CI or a generic
code-review receipt.

## Permission and concurrency

- A0: read sanitized sources, compare branches/PRs/checks, summarize. Never read or disclose
  secret-bearing logs or credential values via A0.
- A1: analyze, plan, design safe tests and evidence without changing external state.
- A2: within already-approved target and change budget, implement reversible isolated-branch
  changes, test, open/update Draft PR and document receipts.
- A3: canonical merge or staging write requires exact scoped human authority (including a valid
  explicit standing authorization when it covers the exact action), plus exact identity, CI,
  protection and independent review.
- A4: production changes, access to secret values including read/disclosure, ACL/credentials,
  deletions and force pushes. Never autonomous. Production requires its own approved MOP,
  restore evidence, effect verification, release identity and separate human authorization.

Parallel workers may only share read-only snapshots. Before every write verify
`repo + PR + HEAD + base + ownership + expected file blob SHA`. Source drift triggers
`REPLAN_REQUIRED`; stale preflight is discarded. Provider preflight and content SHA are guards,
not an atomic cross-system lock. No force-push or branch deletion.

## Reporting and attention budget

The hourly ChatGPT checkpoint watches material changes but is not a guaranteed always-on process.
`src/cybercore/operator_reporting.py` is **presentation-only**: it does not fetch providers,
authenticate evidence, authorize merges, send messages or schedule work. An authenticated caller
must supply sanitized fields.

A one-screen Czech report answers **STAV → CO → PROČ → DOPAD → DALŠÍ → SCHVÁLENÍ**.
Missing direct main-push evidence is `UNKNOWN`; PR-head CI never proves main-push success.
Independent security verdicts cannot be inferred from CodeQL or generic Codex reviews.

## Acceptance / evaluation

1. Stale HEAD/base → REPLAN_REQUIRED before an external write.
2. No production deploy/secret access/branch deletion/force push without separate exact authority.
3. Missing main-push proof remains UNKNOWN.
4. Material blocker reports user impact and one next action.
5. No tokens, credential values or raw sensitive prompts in reports.
6. Exact-head Python matrix, Ruff/quality, package, CodeQL, real CyberHIVE and independent
   code/security review where required.
7. Post-merge read-back and main-push verification; merge alone is not production success.
8. No redundant status messages when state is unchanged.

## Rollout, rollback, accountability

This candidate adds documentation/configuration and a pure presentation utility with unit tests.
It does not modify GitHub Actions, runtime entrypoints, production monitoring, secrets, permissions
or external services.

If rejected, close the Draft PR without merge and preserve evidence; branch deletion remains a
separately protected cleanup action.

**Next candidate after this review:** wiring the formatter to an approved authenticated evidence
collector and event-deduplication store is a separate design and must not create standing
infrastructure privileges.
