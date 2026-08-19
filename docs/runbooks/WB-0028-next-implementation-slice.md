# WB-0028 Next Implementation Slice

Status: Planning note
Date: 2026-08-19

## Purpose

This note records what should happen after the current WB-0028 documentation and state foundation lands.

## Candidate implementation slice

Add a staging-only, manually triggered GitHub Actions workflow that can run in two safe modes first:

1. `plan_only`
2. `dry_run`

The workflow must fail closed until all required secret aliases and target identifiers are configured.

## Required before adding live `staging_apply`

- InterServer staging URL is known.
- Staging document root is verified as non-production.
- Deployment method is confirmed.
- Staging-only deploy identity exists.
- Secret aliases are configured in approved storage.
- Rollback mode is verified.
- Effect verifier is implemented.
- Jan Kočí explicitly authorizes the first remote write.

## Non-goal

This note is not deployment authority and does not execute or authorize remote mutation.