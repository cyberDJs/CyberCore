# InterServer Staging Self-Deploy v0 Runbook

Status: Draft runbook
Work block: `WB-0028`
Scope: InterServer shared-hosting staging only

## Purpose

Prepare the first safe CyberCore self-deployment path for InterServer shared hosting without touching production and without storing plaintext secrets in ordinary systems.

## Absolute boundaries

Do not perform any of these under this runbook without separate explicit approval:

- production deployment;
- DNS change;
- mail change;
- billing change;
- DirectAdmin mutation;
- VPS mutation;
- WordPress or Nextcloud mutation;
- secret rotation or plaintext secret handling;
- deletion or overwrite of production files.

## Manual preparation checklist

The operator or approved administrator must prepare or verify:

1. non-production staging URL exists;
2. staging document root is separate from the production `eimyherrer.com` document root;
3. staging deploy user is restricted to the staging path;
4. deployment method is known: SSH/rsync, SFTP, or provider-native;
5. secret aliases are created in approved storage;
6. no production credential is reused for staging;
7. rollback method is available;
8. staging health-check URL is known;
9. first remote write is explicitly authorized by Jan Kočí.

## Required secret aliases

These are aliases only, not values:

```text
INTERSERVER_STAGING_HOST
INTERSERVER_STAGING_USER
INTERSERVER_STAGING_PORT
INTERSERVER_STAGING_SSH_KEY_OR_SFTP_PASSWORD
```

Allowed storage:

- OS-backed secret store;
- GitHub Environment secret for `interserver-staging`;
- approved external vault.

Denied storage:

- repository files;
- Google Drive;
- Slack;
- chat;
- CASER documents;
- ChatGPT Library;
- ordinary evidence logs.

## First deployment sequence

### Phase 1 — plan only

1. Resolve source branch and commit.
2. Build or identify deployment artifact.
3. Generate deployment manifest.
4. Validate target contract.
5. Record plan receipt.
6. Do not connect to InterServer.

### Phase 2 — dry run

1. Validate secret aliases exist without reading values.
2. Validate staging URL/path are recorded.
3. Validate rollback strategy.
4. Run build and local packaging checks.
5. Record dry-run receipt.
6. Do not write remote files.

### Phase 3 — staging apply

Allowed only after explicit operator approval.

1. Confirm target id: `interserver-shared-hosting-staging`.
2. Confirm source commit.
3. Confirm rollback mode.
4. Deploy to staging path only.
5. Run effect verifier.
6. Record receipt.
7. If verification fails, roll back or block with failure evidence.

## Effect verification

Minimum verifier:

- staging URL returns success;
- deployed version marker matches source commit;
- production URL is unchanged;
- no denied path is touched;
- receipt is stored without secrets.

## Rollback

Preferred rollback:

1. switch `current` symlink to previous release, if supported;
2. restore timestamped backup;
3. remove no-overwrite staging upload;
4. block if no safe rollback exists.

## Current state

Live staging deployment is blocked until staging target identity, secret aliases, deployment method, rollback mode, and effect verifier are verified.