# CyberCore seven-Skill autonomy workflow — review candidate

**Status:** Draft only; not a runtime installation, standing grant, or production change.
**Target:** `cyberDJs/CyberCore`; existing PR #159. Canonical main remains the only source of truth.
**Selection:** exactly the seven real ChatGPT Skills approved by the operator.
**Machine-readable contract:** `configs/autonomy/cybercore-skillset.yaml`.

## Why this uses existing components

CyberCore already contains CASER preflight, CI snapshot reconciliation,
Action Kernel authorization, a real pinned CyberHIVE dry-run contract,
and a proposed durable LongRun boundary (ADR-0007). PR #159 already defines
a compact UX contract and an hourly ChatGPT change monitor. Do not add a second
agent scheduler, change the LongRun runtime, or widen Action Kernel permissions.

The workflow **composes human/agent practices**; the YAML is not executable by
CyberCore until a separately reviewed runtime adapter and authority exist.

## Producer → consumer contracts

| Order | Exact Skill | Input | Output | Failure |
|---|---|---|---|---|
| 1 | `caser-sourcer` | repo, SHA, evidence | source snapshot + freshness + provenance | UNKNOWN → stop |
| 2 | `ai-agent-designer` | goal, snapshot | least-complex agent scope, evaluation criteria | scope drift → replan |
| 3 | `capability-composer` | seven selected Skills, bounds | bounded DAG and ownership | missing edge → block |
| 4 | `caser` | approved scope, DAG, current SHA | read-only checks, isolated candidate writes/receipts | retry ≤3, otherwise block |
| 5 | `capability-observability` | sanitized receipts, gate states | concise human report and event metadata | missing evidence → UNKNOWN |
| 6 | `ai-evaluation-red-team` | candidate commit + tests | independent challenge and finding ledger | P1/P2 → blocked |
| 7 | `release-change-manager` | verification, operator approval | HOLD / approval request / verified effect plan | no authority → HOLD |

Steps 5 and 6 may run independently after step 4. Step 7 depends on both.

## Permission and concurrency

- A0: read sanitized sources, compare branches/PRs/checks, and summarize.
  **Never** read or disclose secret-bearing logs or credential values via A0.
- A1: analyze, plan, design safe tests and evidence without changing external state.
- A2: within the already-approved target and change budget, implement reversible
  isolated-branch changes, test, open/update Draft PR and document receipts.
- A3: canonical merge or staging write requires a **separate exact-identity,
  environment-bound operator approval** plus CI, protection and independent review.
- A4: production changes, access to secret values (including read/disclosure),
  ACL/credentials, deletions, force pushes. **Never autonomous.** Current
  production self-deployment authority is DENIED, even after ordinary A3 approval.
  Production requires its own approved MOP, restore evidence, effect verification,
  release identity and separate human authorization.

Parallel workers may only share read-only snapshots. Before every write, verify
`repo + PR + HEAD + base + ownership + expected file blob SHA`. A changed source
triggers `REPLAN_REQUIRED` and aborts the write; no stale approval can be
reused. Provider preflight and content SHA are not an atomic cross-system lock.
No force-push or branch deletion.

## Reporting and attention budget

The existing ChatGPT checkpoint (hourly, Europe/Prague) watches material changes,
but it is not a guaranteed always-on process. The deterministic formatter in
`src/cybercore/operator_reporting.py` is **presentation-only**: it neither
fetches GitHub nor authenticates CI evidence, authorizes merges, sends messages,
or schedules anything. An authenticated caller must provide sanitized fields.

A one-screen Czech report answers: **STAV → CO → PROČ → DOPAD → DALŠÍ → SCHVÁLENÍ**.
Present the exact SHA and evidence link. Mention whether a changed artifact is
only tests/docs or changes runtime user-facing behavior. Only report changes
for material event kinds; repeat suppression requires a trusted durable
previous-event fingerprint (not implemented by the formatter).

Examples of material triggers:
- CI red / repaired, security P1/P2, invalid or changed SHA, merge conflict,
  branch protection change, material user-facing milestone, missing critical
  evidence, an approval boundary.
- Green check already communicated or no state change → suppress.

Never describe PR-head GitHub Actions as passing main-push CI. The current
GitHub connector limits `fetch_commit_workflow_runs` to PR-triggered runs;
lack of main-push data is `UNKNOWN`. An independent security verdict
cannot be inferred from CodeQL or generic Codex code-review receipts.

## Acceptance / evaluation

1. **Freshness:** any stale PR HEAD/base → REPLAN_REQUIRED before an external write.
2. **Authorization:** no merge/deploy/secret access or branch deletion without
   exact scoped authority; ordinary "dal" does not authorize protected changes.
3. **Evidence:** missing main-push proof remains UNKNOWN, never PASS.
4. **Signal:** material blocker shown with user impact and a single next action.
5. **Privacy:** no logs containing tokens, credential values or raw sensitive
   prompts in the report.
6. **Quality:** exact-head Python matrix, Ruff/quality, package, CodeQL, real
   CyberHIVE contract and independent code/security review where required.
7. **Effects:** post-merge read-back and independent runtime verification;
   merge alone does not equal production success.
8. **Product UX:** no redundant status messages if nothing changed; a short
   report says what improved or what the user still cannot do.

## Rollout, rollback, accountability

This PR adds documentation and a pure presentation utility with unit tests.
It does **not** modify GitHub Actions, source runtime entrypoints, production
monitoring or any external service.

Validation: exact-head CI / CodeQL / pinned real CyberHIVE workflow; separate
code/security review; ensure no new security exposure or compatibility impact.
If rejected, close the Draft PR without merge, preserve evidence and revert
only the isolated candidate branch after authorized cleanup. If the external
hourly monitor is too noisy, disable the monitor separately; that action is
not part of this PR.

**Next candidate after this review:** wire the formatter to an approved
authenticated evidence collector and event deduplication store as a separate
design, NOT by giving the model standing infrastructure privileges.
