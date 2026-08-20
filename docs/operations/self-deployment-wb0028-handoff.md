# WB-0028 Handoff

Date: 2026-08-19
Updated: 2026-08-20

## Current state

The staging-only self-deployment foundation is on `main`. PR #44 carries the ADR-0006 decision reconciliation.

## Review focus

- Staging-only boundary.
- No secrets.
- No production mutation.
- InterServer target contract remains blocked until verified.
- ADR-0006 is Accepted by explicit Jan Kočí authority; acceptance does not authorize remote writes.

## Next slice

Implement the separately authorized plan-only/dry-run manifest validator and optional manually triggered GitHub Actions workflow. The workflow must be disabled/fail-closed for remote execution and must not be capable of `staging_apply` until target identity, deployment capability, secret aliases, rollback, effect verifier, and a fresh explicit remote-write authorization are verified.
