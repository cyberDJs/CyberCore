# Security Verification Pipeline

WB-0025 Slice 1 establishes local and hosted verification for the Python package.
CodeQL, branch protection, required-check enforcement, deployment, publishing, and
release automation are deferred to later slices.

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
