# Self-Deployment Staging Loop Status

Date: 2026-08-19
Work block: `WB-0028`

## Technology status

CyberCore currently has the repository control-plane pieces required for self-development:

- branch creation;
- branch file mutation;
- pull request creation;
- CI and CodeQL gates;
- review thread resolution;
- evidence and project-state updates;
- merge after explicit operator authorization.

CyberCore does not yet have a verified live InterServer deployment path.

## Current stage

`DESIGN_AND_TARGET_CONTRACT`

This stage produces the staging boundary, target registry, runbook, and evidence required before executable deployment automation is added.

## Next technical milestone

`PLAN_ONLY_WORKFLOW`

A safe next slice can add a manually triggered GitHub Actions workflow that creates a deployment manifest and fails closed if the InterServer staging target is not fully configured.

## Blocked until verified

- staging URL;
- staging document root;
- deployment method;
- secret alias storage;
- rollback method;
- effect verifier;
- first remote-write authorization.