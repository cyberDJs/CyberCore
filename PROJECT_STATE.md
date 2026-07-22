# CyberCore Project State

_Last updated: 2026-07-22 15:55 CEST_

## Source of truth

- Repository: `cyberDJs/CyberCore`
- Stable branch: `main`
- Active branch: `feat/interactive-demo-framework`
- Pull request: `#18 feat: introduce interactive demo and learning framework`
- Governance rule: no production mutation without explicit human approval
- CI policy: local or self-hosted verification; GitHub Actions are not required

## Current milestone

Interactive Demo Framework (`WB-0013`) and introductory learning flow.

## Implemented

- Shared Rich-based terminal presentation layer
- `cybercore demo` with deterministic `uc-001` scenario
- `cybercore learn` with introductory Evidence First lesson
- Demo recording helper for asciinema
- README merge-artifact cleanup
- Restored complete CLI after accidental truncation
- Added `rich` runtime dependency

## Verification evidence

Verified locally on macOS with Python `3.14.6`:

- Editable installation completed successfully
- `cybercore --help` exposes all expected commands
- `pytest -v`: **10 passed**
- `cybercore demo --delay 0`: passed
- `cybercore learn --non-interactive`: passed
- `cybercore doctor`: passed with one non-blocking Exchange Agent warning
- `python -m compileall -q src demos`: passed
- Working tree was clean at verification time

## Current non-blocking warning

`cybercore-exchange-agent` is not present at:

```text
~/.local/bin/cybercore-exchange-agent
```

This does not block the interactive demo framework.

## Current decision

PR #18 is technically verified and can proceed toward review and merge after the project-memory checkpoint files are committed.

## Next planned work block

Create an independent `cybercore checkpoint` capability that can collect repository state, tests, commits, decisions, and next actions into the canonical project-memory files.
