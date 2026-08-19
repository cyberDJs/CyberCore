# Self-Deployment Effect Verifier v0

Date: 2026-08-19
Work block: `WB-0028`

## Purpose

A deploy command succeeding is not enough. The effect verifier determines whether the intended staging effect actually happened.

## Minimum checks

- staging URL responds successfully;
- deployed version marker matches the source commit;
- production URL/path is not changed;
- no forbidden path is touched;
- rollback mode exists or deployment is blocked;
- receipt records verifier status without secrets.

## Status values

```text
PASS
FAIL
UNKNOWN
NOT_RUN
```

## Outcome mapping

| Runner result | Verifier result | Outcome |
|---|---|---|
| success | PASS | VERIFIED |
| success | UNKNOWN / NOT_RUN | UNVERIFIED |
| success | FAIL | FAILED |
| failure | any | FAILED or ROLLED_BACK |

## Current state

No live effect verifier has been run. First implementation should create a version marker contract before remote staging deployment.