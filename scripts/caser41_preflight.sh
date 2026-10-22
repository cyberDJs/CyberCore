#!/usr/bin/env bash
# CASER v4.1 optional developer preflight, no repository mutations.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

PYTHON="${CASER_PYTHON:-python3}"
if [[ -x "$ROOT/.venv/bin/python" && -z "${CASER_PYTHON:-}" ]]; then
  PYTHON="$ROOT/.venv/bin/python"
fi

echo "CASER preflight: read-only format/lint and targeted tests"
"$PYTHON" -m ruff format --check src tests
"$PYTHON" -m ruff check src tests
"$PYTHON" -m pytest -q \
  tests/test_action_kernel_sqlite_replay.py \
  tests/test_action_kernel_sqlite_audit.py \
  tests/test_action_kernel_audit_checkpoint.py
echo "Local preflight PASS (not a substitute for CI / CodeQL / independent review)"
