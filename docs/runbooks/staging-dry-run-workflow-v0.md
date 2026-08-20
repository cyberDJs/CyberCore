# Staging Dry-Run Workflow v0

Date: 2026-08-19
Work block: `WB-0029`

## Purpose

Run the first executable CyberCore self-deployment validation path without writing to InterServer.

## Workflow

```text
.github/workflows/staging-dry-run.yml
```

## Required input

The workflow only runs when the operator types:

```text
DRY_RUN_ONLY
```

Any other input prevents the job from running.

## What it does

- checks out the repository;
- installs the package;
- validates the non-secret staging target contract;
- validates the plan-only manifest;
- writes a receipt artifact.

## What it does not do

- no InterServer connection;
- no SFTP, SSH, rsync, DirectAdmin, provider API, DNS, mail, billing, VPS, WordPress, or Nextcloud action;
- no secret read;
- no production write;
- no staging write.

## Receipt semantics

The uploaded receipt is valid only for plan validation. It is not a deployment receipt and must not be treated as proof that staging changed.

## Promotion boundary

This workflow is a prerequisite for a future dry-run/apply workflow. It does not authorize `staging_apply`.
