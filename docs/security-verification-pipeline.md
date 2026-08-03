# Security Verification Pipeline

WB-0025 Slice 1 established local and hosted verification for the Python
package. Slice 2 adds reproducible CodeQL analysis for Python and defines the
merge-gate contract proposed for `main`.

Repository settings are not changed by this slice. The hosted CI and Advanced
CodeQL workflows have now passed after PR #31, but branch protection is still
not enabled. Activation requires explicit human approval and a separate
repository-settings action.

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

## Proposed Required Checks

These checks are the exact proposed merge gates for pull requests targeting
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

Required checks must run on every pull request to `main`. Required workflows
must not use path filtering because a skipped required workflow can leave a
required check pending indefinitely.

## Proposed Branch Protection

Branch protection is not yet enabled. After explicit human approval, configure
`main` branch protection as follows:

- Require a pull request before merging.
- Require the seven checks listed in "Proposed Required Checks".
- Require branches to be up to date before merging.
- Require conversation resolution before merging.
- Require linear history if that matches the repository's existing merge policy.
- Restrict direct pushes to `main`; no direct pushes by automation.
- Keep administrators subject to the rule unless an emergency process is
  explicitly approved.

Strict branch-up-to-date behavior is recommended so the required checks validate
the exact merge candidate against current `main`.

## Manual Verification Checklist

Before activating settings:

- Confirm `.github/workflows/ci.yml` has completed successfully on the branch.
  Current canonical evidence: run `30774683751` passed after PR #31.
- Confirm `.github/workflows/codeql.yml` has completed successfully on GitHub
  Actions. Current canonical evidence: run `30774683774` passed after PR #31.
- Confirm the CodeQL run reports under the stable check name `codeql`.
- Confirm no workflow uses `pull_request_target`.
- Confirm all action refs are immutable 40-character lowercase SHA values.
- Confirm all checkout steps use `persist-credentials: false`.
- Confirm no required workflow uses path filtering.
- Confirm GitHub CodeQL Default setup is disabled so it does not conflict with
  the checked-in Advanced setup.
- Confirm no repository settings, rulesets, secrets, or environments were
  changed by repository automation.

## Rollback

If a required check breaks after branch protection is enabled:

1. Inspect the failed check and determine whether the failure is source,
   dependency, runner, cache, or GitHub service related.
2. If the check is invalid or cannot run, remove only that broken required check
   from branch protection through the approved repository-settings process.
3. Do not relax unrelated checks.
4. Revert or repair the workflow on a feature branch.
5. Re-run hosted CI and CodeQL.
6. Restore the required check only after the hosted run succeeds under the same
   stable job name.

To disable a broken required check safely, first remove it from the branch
protection required-check list, then merge or revert the workflow change through
normal review. Removing or renaming the workflow while it is still required can
leave pull requests blocked by a permanently pending check.

This runbook intentionally contains no tokens, credentials, API write commands,
or automation that mutates repository settings.
