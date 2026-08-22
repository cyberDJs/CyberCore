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

The first live write is a static CyberCore canary only, placed in one unique directory directly beneath the verified staging document root:

```text
cybercore-canary-<run_id>/index.html
cybercore-canary-<run_id>/cybercore-version.json
```

No parent canary directory is required and no other files are in scope.

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
5. Canonical staging root resolves exactly to the approved staging root.
6. Candidate destination is a direct child of that canonical staging root.
7. Candidate destination does not exist according to a non-following metadata check.
8. No destination component from the canonical staging root downward is a symlink.
9. The runner is configured no-overwrite/fail-if-exists.
10. The effect verifier is ready.
11. Rollback scope is exactly the created run directory.
12. Fresh explicit operator authorization names the exact commit, run id, protocol, identity scope, destination, artifact list, and rollback permission.

## Planned execution sequence

### Phase A — final preflight, no remote write

- resolve exact `main` source commit;
- generate local two-file canary artifact;
- compute local hashes;
- validate the plan-only manifest;
- validate the WB-0034 readiness artifact with `scripts/validate_wb0034_readiness.py`;
- confirm target URL/path from canonical state;
- confirm deployment protocol and credential scope evidence;
- confirm secret aliases exist without printing values;
- derive `cybercore-canary-<run_id>` from an approved run id;
- resolve the canonical staging root and require exact equality with the approved path;
- inspect the candidate destination without following links and require it to be absent;
- confirm there is no intermediate destination component below the staging root;
- record preflight receipt.

Any failure stops the procedure.

### Phase B — future approved remote write

Only after fresh authorization:

1. connect using the verified deployment protocol and approved staging deploy identity;
2. resolve the target base path to `/home/eimyherr/domains/staging.eimyherrer.com/public_html`;
3. fail if the resolved base differs from the approved canonical staging path;
4. derive exactly one direct-child destination `cybercore-canary-<run_id>/`;
5. perform a non-following metadata check on that destination and fail unless it is absent;
6. reject any symlink encountered from the canonical staging root downward;
7. immediately before creation, re-resolve the parent and require it to remain the canonical staging root;
8. create only that one unique directory with fail-if-exists semantics;
9. upload only `index.html` and `cybercore-version.json` with no-overwrite semantics;
10. disconnect;
11. run effect verification;
12. create a sanitized evidence receipt.

No command may traverse or write the production document root.

## Effect verification

The verifier must independently confirm:

- `https://staging.eimyherrer.com/cybercore-canary-<run_id>/` returns success;
- `https://staging.eimyherrer.com/cybercore-canary-<run_id>/cybercore-version.json` is reachable;
- marker `commit` equals the exact approved source commit;
- marker `environment` equals `interserver-shared-hosting-staging`;
- marker `run_id` equals the approved run id;
- evidence shows only the approved direct-child staging destination was written;
- path-resolution evidence shows the write parent remained the canonical staging root;
- no denied provider/DNS/credential mutation occurred;
- no secret values were logged.

Production safety verification is based on target-path allowlisting and write-scope evidence. This MOP does not authorize reading production application content or fetching production application URLs for comparison.

## Rollback

Rollback is allowed only if the future authorization explicitly includes it.

Rollback operation:

- resolve the exact created run directory without following an unexpected link;
- verify its parent resolves exactly to the canonical staging root;
- verify its basename equals `cybercore-canary-<authorized-run-id>`;
- reject rollback if the destination or any destination component is a symlink;
- delete only that exact run directory;
- verify the canary URLs return not-found afterward;
- record rollback evidence without secrets.

If exact path identity cannot be proven, do not delete anything.

## Stop conditions

Stop before mutation if any of these is true:

- protocol is not verified;
- deployment user/credential scope is ambiguous;
- a production-wide credential would be reused without an explicit risk decision;
- candidate destination already exists;
- any destination component below the canonical staging root is a symlink;
- candidate parent does not resolve exactly to the canonical staging root immediately before creation;
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
