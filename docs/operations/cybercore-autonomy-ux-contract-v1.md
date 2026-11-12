# CyberCore/CASER operator UX and autonomy contract v1

Status: **proposal / review candidate** (not a standing permission grant)  
Date: 2026-11-12  
Scope: ChatGPT-assisted engineering for `cyberDJs/CyberCore`, with linked CyberHIVE checks

## The user experience we're optimizing

The operator should not need to type "dal" or "stav?" repeatedly to discover a completed check or a routine repair. Progress should be factual, short, contextual and relevant to the product, not a transcript of tool invocations.

Every material update answers **five questions** in one screen:

1. **Stav:** VERIFIED / READY_FOR_MERGE / BLOCKED / FAILED / UNKNOWN (and exact PR + SHA).
2. **Co:** what changed; link directly to evidence.
3. **Proč:** root cause or hypothesis, labeled as such.
4. **Dopad:** what the user can now do, what remains unsafe, and which project milestone moves.
5. **Dál:** the next *action* (by agent vs. by operator), including approval only if actually required.

Default micro-format (Czech):

> **CyberCore PR #NNN — BLOCKED · exact SHA**  
> **Co:** Quality failed on Ruff; Python tests and real CyberHIVE passed.  
> **Proč:** newly added test line spacing disagrees with formatter.  
> **Dopad:** no change to runtime; merge remains gated.  
> **Dělám:** scoped format-only fix, re-run exact-head checks.  
> **Od Tebe:** nic; ozvu se až s výsledkem nebo skutečným blokérem.

Use plain language alongside the engineering term. Link PR/commit/check runs; never hide a failed gate behind an overall "green". Distinguish *PR-head CI* from *post-merge main-push CI*. A missing provider result is `UNKNOWN`, **not success** or failure.

## Autonomous action classes

| Class | Default | Examples | Stop/approval |
|---|---|---|---|
| A0 Observe | autonomous only for sanitized non-secret evidence | read current HEAD/base, compare drift, inspect public/sanitized logs, reviews, workflow status and docs | secret-value access, credential-bearing logs or disclosure are A4; never ingest secret bytes |
| A1 Prepare | autonomous in user-approved scope | root-cause analysis, synthetic tests, isolated plans, evidence, draft proposal | do not pretend preparation is execution |
| A2 Scoped repair | only within already approved work, permissions and budgets | minimal fix in non-canonical branch, add tests, run checks, open Draft PR, document results | re-check HEAD before *every* write; no scope expansion |
| A3 Promotion | explicit operator authorization | merge PR, branch protection changes, scoped staging apply or external operational write | exact SHA, independent checks and action-bound human approval; production deployment is NEVER A3 |
| A4 Protected | no standing approval | secret access/reading/disclosure, credentials/ACL mutation, deletion, force push, ANY production deployment | STOP; separate informed authorization. Production deployment is unavailable in current v0 authority, even after ordinary A3 approval; needs a separately reviewed production MOP, backup/restore proof and effect verification |

Approval is **scope- and identity-bound**, not inferred from "pokračuj" after a protected gate. Existing security and CASER policies take precedence. An autonomous monitor is **read-only** unless a separate explicitly authorized action is in scope. A Draft PR is not a release.

## Execution loop

1. **Reality refresh.** Establish latest `main`, relevant PR HEAD/base, current branch state, active parallel work and trustworthy CI/review evidence; deduplicate existing efforts.
2. **Pick one highest-value next step.** Prefer removal of an actual failing gate over more review-request comments or speculative new PRs.
3. **Dual preflight** for writes: scope, authority, expected diff, rollback, drift, ownership/locks, test path and independent verifier. A detected HEAD/base/SoT change means `REPLAN_REQUIRED`: abort the write, reconcile competing ownership and refresh the plan plus any identity-bound approval. A stale preflight cannot be reused. GitHub content-blob SHA guards updates; read-before-write alone does not create an atomic cross-worker lease.
4. **Do a bounded chunk.** Prefer a complete, reviewable repair or verification result instead of fragmented "done one line" updates. Maximum three failed repair attempts per confirmed cause.
5. **Exact-head gate**: Python test matrix, Ruff/quality, package, CodeQL, real pinned CyberHIVE contract where applicable, independent code/security review and unresolved thread checks. These are distinct statuses.
6. **Effect check.** Confirm the actual new branch SHA and PR state from a second read. After merges, verify `main` SHA and **main-push** checks separately; CI connector returning PR-only runs cannot prove main-push success.
7. **Receipt + handoff.** Persist changed files, test links, risk/rollback notes and pending authority decision; then continue when safe or stop at a real gate.

## Update triggers and anti-noise rules

**Event-driven reporting** on significant facts: failed or recovered checks, actionable P1/P2 review, resolved blocker, unexpected SHA drift, branch conflicts, merged PR, new milestone, security-sensitive decision, or unavailability of evidence. For each, say **what changed and product impact**.

**Periodic observation:** existing ChatGPT automation "CyberCore živý checkpoint" checks hourly (Europe/Prague) and alerts **only for a material change**. Its existence is a scheduler, not a permanent agent process, and cannot guarantee an instant notification at event time. In-chat progress is emitted when material evidence is found; avoid repetitive generic updates. Do not duplicate existing CyberHIVE weekly digest.

**Severity routing:**
- **Urgent:** security P1, production risk, data loss, unexpected mutation, secret access request — notify with sanitized exact evidence and preserve/stop writes; no unilateral live mitigation or sensitive log retrieval.
- **Actionable:** red CI, CodeQL alerts, merge conflict, review P2, drift — apply authorized scoped fix or report bounded blocker.
- **FYI:** green check, ordinary code-review receipts or state unchanged — aggregate, don't spam.

**Do not:** post the same `@codex security review` repeatedly when the connector only produces generic code-review receipts; call that limitation out and route to genuinely independent security review. A code-review “no major findings” is not an independent security PASS.

## What this changes for usability

- Fewer prompts asking for "stav?" because monitored state changes trigger a compact report.
- Easier prioritization: one actionable blocker and next step instead of a long log.
- Clear impact: `main` changed vs only tests changed; contract passed vs deployment proven; functionality available vs still blocked.
- Lower risk: exact SHA and review authority, conservative behavior on unknown CI results.
- Less attention cost: don't repeatedly notify for checks that have not changed.

## Success criteria and rollout

This document defines a **candidate operating contract**; it does not install an agent runtime or alter production behavior. Validate it during the next 3–5 real CyberCore PRs:

- Every meaningful update includes exact identity/evidence, cause, user impact and ownership of the next action.
- No erroneous main-push CI PASS claims, no unauthorised merges/deploys, no branch overwrites.
- Material gate transitions appear in the next scheduled check if connector visibility permits; unchanged state generates no notification.
- User only has to authorize genuine A3/A4 boundaries; repeated approval requests for A0–A2 are counted as workflow defects.
- Prefer one canonical PR over parallel write candidates; close stale branches only under explicit cleanup approval.

Rollback: disable the existing ChatGPT monitor if notifications are noisy; withdraw/close this Draft PR if the UX contract is rejected. No source runtime or production integration is changed here.
