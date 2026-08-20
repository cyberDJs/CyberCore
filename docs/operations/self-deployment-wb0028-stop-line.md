# WB-0028 Stop Line

Date: 2026-08-19
Updated: 2026-08-20

## Stop line

Stop before any action that would:

- connect to InterServer;
- write remote files;
- read secret values;
- modify provider configuration;
- alter production;
- execute `staging_apply` without a fresh explicit operator authorization and all runtime gates passing.

## ADR state

ADR-0006 was explicitly accepted by Jan Kočí on 2026-08-20. Acceptance changes the architecture lifecycle only; it does not authorize any remote mutation.

## Current slice

The next authorized slice may add disabled/manual workflow, manifest, validator, tests, and evidence. It must remain local/plan-only/dry-run and fail closed before any remote write.
