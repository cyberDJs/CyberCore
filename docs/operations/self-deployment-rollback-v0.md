# Self-Deployment Rollback v0

Date: 2026-08-19
Work block: `WB-0028`

## Purpose

Define the rollback expectations for future InterServer staging deployment.

## Preferred order

1. Immutable release directories with `current` symlink.
2. Timestamped backup before overwrite.
3. No-overwrite upload to a new staging path.
4. Block deployment for nontrivial change when rollback is unknown.

## Shared-hosting constraint

InterServer shared hosting capabilities are not assumed. Symlink support, SSH support, and backup restore behavior must be verified before selecting rollback mode.

## Receipt requirement

Every future deployment receipt must record:

- selected rollback mode;
- rollback readiness;
- rollback evidence reference;
- whether rollback was actually executed.

## Current state

Rollback mode is `UNKNOWN_UNTIL_VERIFIED`; therefore live staging apply remains blocked.