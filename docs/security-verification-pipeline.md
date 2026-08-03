# Security Verification Pipeline

WB-0025 Slice 1 established local and hosted verification for the Python
package. Slice 2 added reproducible CodeQL analysis for Python and defined the
merge-gate contract now enforced for `main`.

Repository automation does not mutate repository settings. After explicit
human approval, the `main-branch-protection` ruleset was activated for
`cyberDJs/CyberCore` and verified against PR #32. WB-0026 remains active until
PR #32 is reviewed, approved, merged, and protected `main` is verified after
merge.

## Supported Python Matrix

The CI test matrix starts at the package minimum, Python 3.11, and covers the
stable interpreters currently available through GitHub Actions setup-python:

- Python 3.11
- Python 3.12
- Python 3.13
- Python 3.14

The 3.14 interpreter was verified against the `actions/python-versions` manifest,
which lists stable Linux builds for Python 3.14.6.

## Local Setup

Install the package and development tooling into a virtual environment:

```bash
python -m venv .venv
.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -e ".[dev]"
```

Run the local verification entrypoint:

```bash
PYTHON=.venv/bin/python scripts/verify.sh
```

The script runs Ruff lint, Ruff format check, Pyright, pytest, compileall, and a
local wheel/sdist build. It does not format files or install anything globally.

## CI Checks

The primary workflow is `.github/workflows/ci.yml`.

- `tests (python 3.11)` through `tests (python 3.14)` install the package with
  development extras, run the full pytest suite, and compile `src` and `tests`.
- `quality` runs Ruff lint, Ruff format check, and Pyright on Python 3.11.
- `package` builds the wheel and sdist, verifies both expected artifacts exist,
  installs the built wheel into a fresh virtual environment, runs CLI smoke
  checks from outside the repository checkout, and uploads the distributions as
  a workflow artifact.

The workflow runs for pull requests targeting `main`, pushes to `main`, and
manual `workflow_dispatch` runs. It uses `contents: read`, cancels superseded
runs for the same ref, avoids `pull_request_target`, and does not read secrets
or publish packages.

Canonical hosted evidence after PR #31:

- GitHub Actions CI run `30774683751`: passed.
- This confirms the `tests (python 3.11)`, `tests (python 3.12)`,
  `tests (python 3.13)`, `tests (python 3.14)`, `quality`, and `package`
  jobs completed successfully for the PR #31 state.

## CodeQL

The CodeQL workflow is `.github/workflows/codeql.yml`.

- Workflow name: `CodeQL`
- Job id and job name: `codeql`
- Runner: `ubuntu-24.04`
- Language: `python`
- Build mode: `none`
- Query suite: `security-extended`
- Analysis category: `/language:python`
- Triggers: pull requests targeting `main`, pushes to `main`,
  `workflow_dispatch`, and one weekly scheduled scan

The workflow uses `actions/checkout` with `persist-credentials: false`. CodeQL
`init` and `analyze` are pinned to the immutable commit for CodeQL Action
`v4.37.4`, `f205ea1c3313d32999d8d6a48b4f6530d4437b38`.

Permissions are scoped to the CodeQL job:

- `contents: read`
- `actions: read`
- `security-events: write`

`packages: read` is not configured because this Python analysis does not need
package-registry access.

Canonical hosted evidence after PR #31:

- CodeQL run `30774683774`: passed under the stable `codeql` job.
- GitHub CodeQL Default setup initially conflicted with this repository's
  checked-in Advanced setup. A human explicitly disabled Default setup in
  GitHub repository settings, then retried the run successfully.
- The repository keeps Advanced setup as the source-controlled CodeQL contract.
  Default setup must remain disabled unless the Advanced workflow is removed
  through a separately reviewed change.

## Required Checks

These checks are the exact required merge gates for pull requests targeting
`main`:

- `tests (python 3.11)`
- `tests (python 3.12)`
- `tests (python 3.13)`
- `tests (python 3.14)`
- `quality`
- `package`
- `codeql`

Job names must remain stable because branch protection matches required checks
by their reported names. Renaming a required job can block merges until the
branch-protection rule is updated by an approved repository administrator.

GitHub also reports an informational workflow check named `CodeQL`. The active
ruleset required context is not that display check; it is the lowercase CodeQL
job context `codeql`.

Required checks must run on every pull request to `main`. Required workflows
must not use path filtering because a skipped required workflow can leave a
required check pending indefinitely.

## Active Branch Protection

Main branch protection was explicitly approved, activated, and verified through
this ruleset:

- Repository: `cyberDJs/CyberCore`
- Pull request: #32
- Ruleset id: `18986451`
- Ruleset name: `main-branch-protection`
- Target: `branch`
- Target ref: `~DEFAULT_BRANCH`
- Enforcement: `active`
- Bypass actors: none
- `current_user_can_bypass: never`
- Activated: `2026-08-03T10:47:03.259+02:00`

Rules:

- Deletion protection enabled.
- Non-fast-forward protection enabled.
- Pull request required.
- One approving review required.
- Stale approvals dismissed after push.
- Review thread resolution required.
- CODEOWNERS review not required.
- Last-push approval not required.
- Allowed merge methods: merge, squash, rebase.
- Linear history not required.

Required status-check policy:

- `strict_required_status_checks_policy: true`
- `do_not_enforce_on_create: false`

Strict required status checks mean the required checks validate the merge
candidate against current `main`.

## PR #32 Verification

Verification against PR #32:

- Head commit: `c3868e058f42dfbb8c0c4bdf3eabfe094dd91ccf`
- CI run: `30784170890` passed
- CodeQL run: `30784170892` passed
- All seven required contexts passed
- PR mergeable: `MERGEABLE`
- Merge state: `BLOCKED`
- Review decision: `REVIEW_REQUIRED`
- PR remains draft

The merge state is expected: the ruleset is active, all required checks have
passed, and merge remains blocked until the draft PR is marked ready and an
independent approval is present.

## Manual Verification Checklist

Before marking PR #32 ready or merging:

- Confirm `.github/workflows/ci.yml` has completed successfully on PR #32.
  Current canonical evidence: run `30784170890` passed.
- Confirm `.github/workflows/codeql.yml` has completed successfully on PR #32.
  Current canonical evidence: run `30784170892` passed.
- Confirm the required CodeQL context is the stable lowercase job name `codeql`.
- Confirm the informational check named `CodeQL` is not confused with the
  required ruleset context `codeql`.
- Confirm no workflow uses `pull_request_target`.
- Confirm all action refs are immutable 40-character lowercase SHA values.
- Confirm all checkout steps use `persist-credentials: false`.
- Confirm no required workflow uses path filtering.
- Confirm GitHub CodeQL Default setup is disabled so it does not conflict with
  the checked-in Advanced setup.
- Confirm ruleset `18986451` is active with no bypass actors and
  `current_user_can_bypass: never`.
- Confirm PR #32 is independently approved before merge.

## Rollback

If a required check or ruleset configuration breaks after branch protection is
enabled:

1. Inspect the failed check and determine whether the failure is source,
   dependency, runner, cache, or GitHub service related.
2. Disable enforcement only for ruleset `18986451`
   (`main-branch-protection`) through the approved repository-settings
   process.
3. Verify no active `main` enforcement remains.
4. Do not relax unrelated repository settings, secrets, environments, or
   workflows.
5. Revert or repair the workflow or ruleset documentation on a feature branch.
6. Re-run hosted CI and CodeQL.
7. Reactivate ruleset `18986451` only after the hosted run succeeds under the
   same stable required job names.

This runbook intentionally contains no tokens, credentials, API write commands,
or automation that mutates repository settings.
