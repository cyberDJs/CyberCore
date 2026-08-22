# WB-0034 — First Staging Deployment MOP (pre-authorization)

Date: 2026-08-22
Status: `PLAN ONLY — REMOTE WRITE BLOCKED`
Target: `interserver-shared-hosting-staging`
Canonical staging URL: `https://staging.eimyherrer.com`
Staging document root: `/home/eimyherr/domains/staging.eimyherrer.com/public_html`

## Purpose

Define the exact first-write Method of Procedure before any staging mutation is authorized.

This MOP is not an execution authorization. It is a bounded approval packet template.

## Planned deployment artifact

The first live write is a static CyberCore canary only:

```text
cybercore-canary/<run_id>/index.html
cybercore-canary/<run_id>/cybercore-version.json
```

No other files are in scope.

`cybercore-version.json` must contain only:

```json
{
  "repository": "cyberDJs/CyberCore",
  "commit": "<exact-approved-commit>",
  "branch": "main",
  "built_at": "<UTC-timestamp>",
  "environment": "interserver-shared-hosting-staging",
  "run_id": "<run-id>"
}
```

## Preconditions

All must be true before an authorization request is considered complete:

1. PR/WB-0034 is merged and exact source commit is pinned.
2. Deployment protocol is verified read-only as SFTP or SSH/SFTP.
3. Deploy identity scope is verified and does not unintentionally permit automated writes to the production document root.
4. Required secret aliases are present in approved secret storage without value disclosure.
5. Destination does not already exist.
6. The runner is configured no-overwrite/fail-if-exists.
7. The effect verifier is ready.
8. Rollback scope is exactly the created run directory.
9. Fresh explicit operator authorization names the exact commit, run id, protocol, identity scope, destination, artifact list, and rollback permission.

## Planned execution sequence

### Phase A — final preflight, no remote write

- resolve exact `main` source commit;
- generate local two-file canary artifact;
- compute local hashes;
- validate the plan-only manifest;
- confirm target URL/path from canonical state;
- confirm deployment protocol and credential scope evidence;
- confirm secret aliases exist without printing values;
- confirm destination run id is unique;
- record preflight receipt.

Any failure stops the procedure.

### Phase B — future approved remote write

Only after fresh authorization:

1. connect using the verified deployment protocol and approved staging deploy identity;
2. resolve the target base path to `/home/eimyherr/domains/staging.eimyherrer.com/public_html`;
3. fail if the resolved base differs from the approved canonical staging path;
4. fail if the destination `cybercore-canary/<run_id>/` already exists;
5. create only that unique directory;
6. upload only `index.html` and `cybercore-version.json` with no-overwrite semantics;
7. disconnect;
8. run effect verification;
9. create a sanitized evidence receipt.

No command may traverse or write the production document root.

## Effect verification

The verifier must independently confirm:

- `https://staging.eimyherrer.com/cybercore-canary/<run_id>/` returns success;
- `https://staging.eimyherrer.com/cybercore-canary/<run_id>/cybercore-version.json` is reachable;
- marker `commit` equals the exact approved source commit;
- marker `environment` equals `interserver-shared-hosting-staging`;
- marker `run_id` equals the approved run id;
- evidence shows only the approved staging run directory was written;
- no DNS, DirectAdmin, Cloudflare, credential, mail, billing, VPS, WordPress, Nextcloud, registrar, PHP, ownership, permission, or production mutation occurred;
- no secret values were logged.

Production safety verification is based on target-path allowlisting and write-scope evidence. This MOP does not authorize reading production application content to compare it.

## Rollback

Rollback is allowed only if the future authorization explicitly includes it.

Rollback operation:

- resolve the exact created run directory;
- verify it begins with the canonical staging path plus `/cybercore-canary/`;
- verify the run id matches the authorized run;
- delete only that run directory;
- do not delete the parent `cybercore-canary` directory unless separately authorized;
- verify the canary URLs return not-found afterward;
- record rollback evidence without secrets.

If exact path identity cannot be proven, do not delete anything.

## Stop conditions

Stop before mutation if any of these is true:

- protocol is not verified;
- deployment user/credential scope is ambiguous;
- a production-wide credential would be reused without an explicit risk decision;
- destination already exists;
- source commit is not exact;
- target path differs from canonical staging path;
- no-overwrite behavior cannot be guaranteed;
- rollback scope is ambiguous;
- secret values would be exposed in logs/evidence;
- any command or endpoint may mutate outside the approved staging run directory.

Stop after mutation and do not broaden scope if verification fails. Use only the separately authorized rollback action or preserve state for manual review.

## Explicitly not authorized by this document

- any remote file write;
- credential creation/rotation;
- production access or mutation;
- staging-root overwrite;
- symlink creation or promotion;
- DNS/TLS/provider changes;
- full CyberCore application deployment;
- recurring/automatic deployment.
