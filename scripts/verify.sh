#!/bin/sh
set -eu

stage() {
    printf '\n==> %s\n' "$1"
}

PYTHON="${PYTHON:-python}"

stage "Ruff lint"
"$PYTHON" -m ruff check src tests

stage "Ruff format check"
"$PYTHON" -m ruff format --check src tests

stage "Pyright"
"$PYTHON" -m pyright

stage "Pytest"
"$PYTHON" -m pytest -q

stage "Compile sources and tests"
"$PYTHON" -m compileall -q src tests

stage "Build package"
"$PYTHON" -m build
