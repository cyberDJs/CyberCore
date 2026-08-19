# Self-Deployment Staging Loop v0

Status: Draft architecture
Work block: `WB-0028`
Date: 2026-08-19
Scope: non-production staging only

## Purpose

CyberCore needs a controlled way to evolve itself without turning autonomous development into unsafe production mutation.

This architecture defines the first staging-only self-deployment loop:

```text
Intent
-> Candidate branch
-> Implementation
-> Tests and security checks
-> Pull request
-> Staging deployment plan
-> Human/operator authorization for remote mutation
-> Staging deploy
-> Effect verification
-> Evidence receipt
-> Learning / next action
```

## Non-goals

- No production deploy.
- No automatic DNS, mail, billing, DirectAdmin, VPS, WordPress, or Nextcloud mutation.
- No plaintext secret storage in repository, chat, Google Drive, Slack, CASER documents, ChatGPT Library, or ordinary evidence logs.
- No bypass of GitHub checks, branch protection, or explicit operator authorization.

## Core components

### 1. Self-Deploy Controller

Responsible for converting an approved candidate change into a staging deployment plan.

Inputs:

- repository and branch identity;
- target staging environment identifier;
- artifact/build output definition;
- deployment mode: `dry_run`, `plan_only`, or `staging_apply`;
- rollback strategy;
- effect-verification contract.

It does not hold secrets. It references secret aliases only.

### 2. Staging Target Registry

A safe registry of non-secret deployment target metadata.

It may contain:

- provider name;
- environment class;
- target identifier;
- permitted deployment mode;
- secret aliases;
- non-secret path placeholders;
- health-check URL placeholder;
- production-boundary warnings.

It must not contain:

- host passwords;
- SSH private keys;
- API tokens;
- TOTP seeds;
- cookies;
- recovery codes;
- production credential values.

### 3. Deployment Manifest

A per-run plan that says what will be deployed and how.

Minimum fields:

- `run_id`;
- repository;
- source branch and commit;
- build artifact identity;
- staging target id;
- expected changed files or artifact paths;
- deploy mode;
- rollback mode;
- verifier command or URL;
- evidence destination.

### 4. Deploy Runner

The execution layer that performs the staging-only remote write after all gates pass.

For InterServer shared hosting this is expected to be one of:

- SSH/rsync, if available;
- SFTP upload, if SSH is not available;
- provider-native deployment mechanism, if later verified.

The actual available method is currently `UNKNOWN` until InterServer capability is verified.

### 5. Effect Verifier

Checks the outcome independently after the deploy runner reports success.

Examples:

- staging URL returns HTTP 200;
- expected version/commit marker is present;
- no production URL was changed;
- no forbidden file path was written;
- rollback artifact exists or previous state is recoverable.

### 6. Evidence Receipt

Records the outcome without secrets.

Receipt fields:

- run id;
- timestamp;
- branch and commit;
- target id;
- deploy mode;
- verifier result;
- rollback readiness;
- changed artifact identity;
- operator authorization reference;
- failure reason, if any.

## InterServer shared-hosting boundary

The first target is InterServer shared hosting, but the live deployment capability is not assumed.

Required verification before any live staging deploy:

1. staging subdomain or isolated staging path exists;
2. staging target is separate from `eimyherrer.com` production content;
3. staging user has least-privilege access to staging path only;
4. all credentials are in approved secret storage;
5. rollback method is known;
6. staging health-check URL is known;
7. operator explicitly authorizes the first remote write.

## Deployment modes

### `plan_only`

Creates a deployment plan and receipt with no remote write.

### `dry_run`

Builds the artifact and validates the target contract but does not mutate the remote target.

### `staging_apply`

Performs the remote staging write. This mode requires explicit operator authorization and all target gates to pass.

## Rollback model

Preferred order:

1. immutable release directory plus `current` symlink, if supported;
2. timestamped backup copy before overwrite;
3. no-overwrite upload to a new staging path;
4. block deployment if no rollback path is available and the change is not trivially reversible.

Shared hosting may not support symlinks or atomic promotion. The runner must detect and record the available rollback mode instead of assuming it.

## Promotion boundary

A successful staging deployment is not production promotion.

Production promotion remains blocked by:

- explicit human approval;
- production MOP;
- backup/restore readiness;
- effect verification;
- separate evidence receipt.

## Version v0 decision

WB-0028 creates the staging-loop architecture and safe target registry first. It does not execute InterServer deployment until the target and secret aliases are verified.