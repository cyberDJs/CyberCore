# WB-0029 — Disabled Manual Staging Workflow + Manifest Validator

Status: Active candidate
Date: 2026-08-19
Canonical repository: `cyberDJs/CyberCore`
Target branch: `feat/wb-0029-staging-workflow-validator`

## Goal

Create the first executable self-deployment safety layer without granting remote-write authority.

This work block adds:

- a fail-closed staging target and manifest validator;
- an example plan-only deployment manifest;
- a manual GitHub Actions dry-run workflow;
- tests proving that live staging apply is blocked in this slice;
- documentation for the next implementation step.

## In scope

- Local validation logic.
- Unit tests.
- Manual `workflow_dispatch` dry-run workflow.
- Plan-only receipt artifact.
- Documentation and project state transition.

## Out of scope

- Live InterServer remote write.
- Reading or storing secret values.
- Production deployment.
- DNS, mail, billing, DirectAdmin, VPS, WordPress, or Nextcloud mutation.
- Accepting ADR-0005.

## Safety model

The validator allows only:

```text
plan_only
dry_run
```

It blocks `staging_apply` until a later approved work block verifies staging URL, staging path, deployment method, rollback, effect verifier, secret aliases, and explicit first remote-write authorization.

## Exit criteria

- Tests pass.
- CI and CodeQL pass.
- The manual workflow cannot write to InterServer.
- The receipt states no remote write, no production write, and no secrets read.
- PR is ready for merge with explicit operator authorization.
