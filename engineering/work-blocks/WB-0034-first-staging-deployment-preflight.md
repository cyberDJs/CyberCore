# WB-0034 — First Staging Deployment Preflight

## Status

`PREPARED — REMOTE WRITE NOT AUTHORIZED`

Date: 2026-08-22
Parent baseline: `WB-0033 — InterServer Isolated Staging Target`
Canonical base: `main@d74497eb0730a0d112cbf7957593f23cb35b5e71`
Target: `staging.eimyherrer.com`
Target document root: `/home/eimyherr/domains/staging.eimyherrer.com/public_html`
Production document root: `/home/eimyherr/domains/eimyherrer.com/public_html`

## Goal

Prepare the first real CyberCore staging write up to, but not across, the final human approval gate.

This work block is repository-only and read-only with respect to InterServer unless a later step is separately authorized. It must not perform `staging_apply`, upload files, create remote directories, change credentials, change DirectAdmin/Cloudflare/provider settings, or touch production application content.

## Post-merge reconciliation

PR #54 / WB-0033 was squash-merged into `main` as:

```text
d74497eb0730a0d112cbf7957593f23cb35b5e71
```

WB-0033 is now the canonical verified runtime baseline for:

- InterServer shared-hosting service `website_id=1439764`;
- staging hostname `staging.eimyherrer.com`;
- isolated staging document root;
- production/staging path non-overlap proven by bounded metadata-only read;
- Cloudflare authoritative DNS and DNS-only staging A record;
- HTTPS/TLS reachability;
- DirectAdmin -> Cloudflare ACME DNS-01 integration;
- standing unattended renewal authority for the existing `eimyherrer.com` + `*.eimyherrer.com` certificate.

WB-0033 did not deploy CyberCore/application content.

## First-write design

The first staging mutation should be the smallest independently verifiable CyberCore canary, not a full application rollout.

Planned artifact:

```text
cybercore-canary/<run_id>/index.html
cybercore-canary/<run_id>/cybercore-version.json
```

Planned public verifier path:

```text
https://staging.eimyherrer.com/cybercore-canary/<run_id>/
https://staging.eimyherrer.com/cybercore-canary/<run_id>/cybercore-version.json
```

The version marker must contain only non-secret deployment identity:

- repository;
- exact source commit;
- source branch;
- build timestamp;
- environment id `interserver-shared-hosting-staging`;
- run id.

The first write must be **no-overwrite**. It must not replace the staging document-root index, an existing release, or any production path.

## Exact future mutation scope

A later explicit first-write authorization may allow only:

1. create one unique directory below `.../public_html/cybercore-canary/<run_id>/`;
2. upload exactly `index.html` and `cybercore-version.json` into that directory;
3. perform no overwrite outside that unique directory;
4. perform no chmod/chown, symlink, package/service, PHP, DNS, mail, billing, DirectAdmin, Cloudflare, VPS, WordPress, Nextcloud, registrar, or production mutation;
5. if rollback is explicitly included in the same authorization, remove only the directory created for that run after verifying its exact path.

If path resolution, credential scope, protocol behavior, or rollback scope is ambiguous, abort before the first remote write.

## Required gates before authorization request

### G1 — target identity

`VERIFIED`

- staging URL: `https://staging.eimyherrer.com`;
- staging document root: `/home/eimyherr/domains/staging.eimyherrer.com/public_html`;
- production document root: `/home/eimyherr/domains/eimyherrer.com/public_html`;
- same path: false;
- staging inside production: false;
- production inside staging: false.

### G2 — deployment protocol

`PENDING_READ_ONLY_VERIFICATION`

The first write may use only a protocol whose behavior is verified before approval. Preferred candidates are SFTP or SSH/SFTP. FTP, provider-native mutation, or an undocumented path must not be assumed.

### G3 — least-privilege deploy identity

`BLOCKED_PENDING_VERIFICATION`

The deploy identity must not be a production-wide writer if a staging-scoped identity can be created or already exists. Reuse of a credential with write access to the production document root is not acceptable for an automated first-write runner without a separate risk decision and explicit authorization.

No credential creation/rotation is authorized by WB-0034.

### G4 — secret alias readiness

`PENDING`

Required aliases remain:

- `INTERSERVER_STAGING_HOST`;
- `INTERSERVER_STAGING_USER`;
- `INTERSERVER_STAGING_PORT`;
- `INTERSERVER_STAGING_SSH_KEY_OR_SFTP_PASSWORD`.

Only alias presence/readiness may be recorded. Secret values remain outside repository, chat, Drive, Slack, CASER documents, and ordinary evidence.

### G5 — rollback

`PLAN_DEFINED; RUNTIME_VERIFICATION_PENDING`

Primary first-write rollback is intentionally simple: because the deployment is no-overwrite into a unique directory, rollback is deletion of only that exact run directory if and only if deletion is included in the future authorization.

No symlink promotion is used in the first cycle. This avoids assuming shared-hosting symlink semantics before they are verified.

### G6 — effect verifier

`PLAN_DEFINED; IMPLEMENTATION/DRY_RUN_PENDING`

Required checks:

- staging canary URL returns HTTP success;
- `cybercore-version.json` exists and its commit equals the approved manifest commit;
- runner/evidence proves writes were constrained to the unique staging canary directory;
- production path was never opened for write;
- no denied provider/DNS/credential mutation occurred;
- receipt contains no secret values.

The production no-change check is path/effect-boundary based; WB-0034 does not grant production application-content reads merely to compare content.

### G7 — exact source commit

`PENDING_AFTER_WB0034_MERGE`

The first live manifest must pin an exact `main` commit. `TBD`, branch-only identity, or moving refs are not acceptable for `staging_apply`.

### G8 — explicit first remote-write authorization

`NOT_GRANTED`

WB-0034 preparation does not authorize the remote write. A later approval must name the exact source commit, run id, protocol, deploy identity/scope, target path, two-file artifact, and rollback scope.

## Plan-only artifact

WB-0034 adds a plan-only manifest and current readiness evidence. Existing validators must continue to reject `staging_apply` in this PR.

No change in this work block may weaken the current invariant:

```text
remote_write_requested: false
remote_write_allowed: false
production_write_allowed: false
```

## Approval packet to produce

Before requesting the first staging-write authorization, the handoff must contain:

- exact source commit;
- exact run id;
- verified deployment protocol;
- deploy identity safe reference and scope result;
- secret-alias readiness result without values;
- exact destination directory;
- exact two-file artifact list;
- verifier commands/URLs;
- rollback action limited to that run directory;
- expected evidence receipt fields;
- explicit stop conditions.

## Out of scope

- executing the first remote write;
- deploying the full CyberCore service/application stack;
- production deployment or production application-content access;
- creating or rotating deployment credentials;
- changing DNS/TLS/provider configuration;
- enabling automatic staging deployment;
- changing GitHub secret/environment governance;
- broadening the existing ACME standing authority.

## Exit criteria

WB-0034 preflight is complete when:

- PR #54 is reconciled as merged into canonical state;
- the target registry reflects the verified WB-0033 staging identity;
- a plan-only first-write manifest exists;
- current readiness evidence records verified target identity and all remaining blockers without overclaim;
- exact mutation and rollback scope are documented;
- CI and CodeQL pass;
- fresh Codex review finds no valid unresolved issue;
- remote write remains blocked.

A subsequent execution step may proceed only after the remaining runtime gates are verified and Jan Kočí grants fresh explicit first staging remote-write authorization.
