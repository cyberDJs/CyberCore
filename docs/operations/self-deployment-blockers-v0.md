# Self-Deployment Blockers v0

Date: 2026-08-19
Work block: `WB-0028`

## Current blockers for live staging deploy

- InterServer staging URL is not verified.
- InterServer staging document root is not verified.
- Deployment method is not verified.
- Staging-only deploy identity is not verified.
- Secret aliases are not verified in approved storage.
- Rollback mode is not verified.
- Effect verifier is not implemented.
- First remote-write authorization has not been given.

## Not a blocker for this PR

These are not blockers for the current documentation/state foundation:

- no live InterServer credentials;
- no live staging URL;
- no executable deploy workflow;
- no production approval.

## Required next action after this PR

Implement a `plan_only` / `dry_run` workflow or validator that fails closed when blockers remain unresolved.