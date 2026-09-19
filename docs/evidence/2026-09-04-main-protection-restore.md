# CyberCore main protection restore evidence — 2026-09-04

## Scope

Repository: `cyberDJs/CyberCore`

Approved action: restore the missing `main` protection contract and then
reconcile source-of-truth documentation. This evidence records the already
completed repository-settings restore, the later approval-gate correction, and
their read-only verification. It does not authorize merge, deployment,
production mutation, secret changes, or any additional repository-settings
change.

## Pre-restore observation

Canonical `main` at the protection preflight resolved to:

`14d4c6c4beb6b03aaedfaf2a76a521a038c98cb1`

Live repository-settings observations before restore:

- repository rulesets: `[]`;
- `main` branch: `protected=false`;
- legacy branch-protection enforcement reported off;
- the documented historical ruleset `18986451` was not present in the live
  ruleset collection.

The CI and CodeQL workflows were still present on `main`. Their live required
job names matched the original WB-0026 contract:

- `tests (python 3.11)`;
- `tests (python 3.12)`;
- `tests (python 3.13)`;
- `tests (python 3.14)`;
- `quality`;
- `package`;
- `codeql`.

The informational workflow display check `CodeQL` remains distinct from the
required lowercase job context `codeql`.

## Historical contract

PR #32 / WB-0026 recorded the original ruleset as:

- id: `18986451`;
- name: `main-branch-protection`;
- target ref: `~DEFAULT_BRANCH`;
- enforcement: active;
- bypass actors: none;
- pull request required;
- one approving review required;
- stale approvals dismissed after push;
- review-thread resolution required;
- deletion and non-fast-forward protection enabled;
- merge methods: merge, squash, rebase;
- strict required status checks enabled;
- seven required contexts listed above.

That identifier and one-review requirement are retained as historical evidence
only.

## Approved restore

After explicit approval `APPROVE CYBERCORE MAIN PROTECTION RESTORE`, a
replacement active ruleset was created using the historical WB-0026 contract as
the restoration baseline:

- id: `22291749`;
- name: `main-branch-protection`;
- target: `branch`;
- target ref: `~DEFAULT_BRANCH`;
- enforcement: `active`;
- bypass actors: none;
- `current_user_can_bypass: never`.

Effective rules verified immediately after creation:

- deletion protection;
- non-fast-forward protection;
- pull request required;
- one approving review required at that restoration snapshot;
- stale approvals dismissed after push;
- review-thread resolution required;
- CODEOWNERS review not required;
- last-push approval not required;
- merge methods `merge`, `squash`, `rebase`;
- strict required status-check policy;
- `do_not_enforce_on_create=false`;
- all seven required status contexts.

GitHub also returned
`require_extra_approval_for_unattributed_changes=true` on the restored pull
request rule. This server-returned state is recorded explicitly rather than
silently omitted.

## Initial post-restore verification

Read-only verification after the settings restore observed:

- ruleset `22291749`: present and `active`;
- `current_user_can_bypass: never`;
- effective bypass actors: none;
- `main`: `protected=true`;
- effective `main` rules included the pull-request, review-thread, deletion,
  non-fast-forward, and seven required-check gates.

PR #83 was also inspected as a non-mutating enforcement sanity check. Its head
`a12eac4eba0e7f0dc77682ad427b45774cd6fa32` remained open, was behind current
`main`, and still had four current unresolved P1 review findings. The restored
strict/update and review-thread gates therefore provided independent reasons it
must not be merged in that state.

## Approval-gate reconciliation

A later source-of-truth check on 2026-09-04 compared the restored live ruleset
with the newer documented governance model from merged PR #38. PR #38 records
that external human review is optional for documentation/state-only
non-production pull requests, while merge still requires explicit operator
authorization and all required GitHub checks.

The restore had therefore reintroduced a stale historical enforcement detail:
`required_approving_review_count: 1`.

After separate explicit approval
`APPROVE CYBERCORE RULESET APPROVAL-GATE REPAIR`, only the ordinary approving
review count on ruleset `22291749` was changed from `1` to `0`.

Read-only verification after that correction observed:

- ruleset id unchanged: `22291749`;
- enforcement unchanged: `active`;
- target unchanged: `~DEFAULT_BRANCH`;
- bypass actors unchanged: none;
- `current_user_can_bypass` unchanged: `never`;
- deletion protection preserved;
- non-fast-forward protection preserved;
- pull request requirement preserved;
- `required_approving_review_count: 0`;
- review-thread resolution preserved;
- CODEOWNERS review still not required;
- last-push approval still not required;
- `require_extra_approval_for_unattributed_changes=true` still reported by
  GitHub;
- strict required status checks preserved;
- `do_not_enforce_on_create=false` preserved;
- all seven required status contexts preserved.

PR #88 remained on exact head
`57d0bf27c1c3804424352ee8a8d9c0ac238199da` at the immediate post-settings
verification and changed from GitHub `mergeable_state: blocked` to
`mergeable_state: clean` without adding an external approval. That transition
confirmed the stale ordinary-review gate had been the active blocker.

The GitHub reviewer count is not a substitute for project authorization. The
applicable explicit operator approval remains required for merge and other
governed actions, and consequential mutation classes retain their separate
approval gates.

## Provenance gap

The cause of the original ruleset disappearance is **unknown**.

A probe for organization audit-log evidence did not return usable deletion
provenance through the currently available access path. Therefore this record
does not attribute the deletion to any actor, timestamp, plan transition, or
automation.

## Source-of-truth rule

For current repository-settings decisions, use live GitHub state first and this
recovery evidence second. Do not use historical ruleset id `18986451` or its
historical one-review requirement as current settings identifiers.

Current protection state after the 2026-09-04 reconciliation:

- ruleset: `22291749`;
- ordinary approving-review count: `0`;
- pull request required;
- review-thread resolution required;
- strict seven-context status-check policy retained;
- bypass actors: none;
- `current_user_can_bypass: never`.

Any future modification, weakening, bypass, replacement, or deletion of this
protection requires separate explicit repository-settings approval.
