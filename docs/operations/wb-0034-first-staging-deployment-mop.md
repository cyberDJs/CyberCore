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

The marker schema is exact: missing fields, additional fields, duplicate JSON keys, invalid JSON, a non-UTC `built_at`, or any value that does not match the final packet keeps the gate BLOCKED.

## Preconditions

All must be true before an authorization request is considered complete:

1. PR/WB-0034 is merged, the trusted `main` ref has been refreshed, and the deployment runner's checked-out `HEAD` equals that exact `main` commit.
2. Deployment protocol is verified read-only as SFTP or SSH/SFTP.
3. Deploy identity scope is verified and does not unintentionally permit automated writes to the production document root.
4. Required secret aliases are present in approved secret storage without value disclosure.
5. Canonical staging root resolves exactly to the approved staging root.
6. Candidate destination is a direct child of that canonical staging root.
7. Candidate destination does not exist according to a non-following metadata check.
8. No destination component from the canonical staging root downward is a symlink.
9. The runner is configured no-overwrite/fail-if-exists.
10. The effect verifier is ready.
11. Rollback scope is exactly the created run directory and rollback permission is explicit.
12. Fresh explicit operator authorization names the exact commit, run id, protocol, deploy-identity scope reference, destination, artifact list, and rollback permission.
13. A sanitized WB-0034 evidence bundle exists, is bound into readiness by SHA-256, and contains the same source commit, run id, destination, exact artifact hashes, protocol/scope evidence, verifier evidence, and authorization binding.
14. The final manifest, readiness document, evidence bundle, trusted `main` commit, checked-out repository `HEAD`, and exact local deployment artifacts all agree; the manifest/evidence authorization, run id, destination, artifact set, protocol, deploy-identity scope, and rollback permission also match.
15. The local artifact directory is traversed component-by-component without following symlinks, contains exactly the two approved files, and both files are opened relative to that pinned directory without following links.
16. The exact bytes of `cybercore-version.json` that are hashed for deployment pass strict marker-schema validation and bind repository, trusted-main commit, branch, UTC build time, environment, and run id to the final packet.

## Machine-artifact disclosure rule

WB-0034 manifest, readiness, and evidence YAML are deterministic machine artifacts and are intentionally comment-free. Their raw text is scanned before YAML parsing. The validators reject YAML comments, credential-like assignments, the broader PEM/private-key header family including EC/DSA/PGP/encrypted key forms, and credential-bearing URLs such as `scheme://user:password@host`.

This is stricter than ordinary YAML authoring by design: approval-packet data must not contain hidden comment-only credentials or secret-bearing URL/key forms.

## Planned execution sequence

### Phase A — final preflight, no remote write

- refresh/resolve the trusted `main` ref and require checked-out repository `HEAD` to equal that exact commit;
- generate the local two-file canary artifact in a dedicated artifact directory;
- open the local artifact directory from the filesystem root one component at a time using no-follow directory semantics; reject any symlinked/missing/invalid ancestor or final directory component;
- require that artifact directory to contain exactly `index.html` and `cybercore-version.json` and no additional entries;
- open both artifact files relative to the already-open directory descriptor with no-follow semantics and require regular files;
- compute SHA-256 from the exact bytes read through those file descriptors;
- parse those exact `cybercore-version.json` bytes as strict UTF-8 JSON with duplicate-key rejection;
- require the marker's exact six-field schema and require `repository=cyberDJs/CyberCore`, `commit=<trusted-main-HEAD>`, `branch=main`, `environment=interserver-shared-hosting-staging`, `run_id=<approved-run-id>`, and a valid UTC `built_at` timestamp;
- choose the concrete run id and direct-child destination `cybercore-canary-<run_id>/`;
- populate a runtime copy of the WB-0034 manifest with the concrete run id, destination, exact source commit, and fresh authorization reference;
- populate the readiness document only from the collected evidence;
- create the sanitized WB-0034 evidence bundle and bind it into readiness with its exact SHA-256 digest;
- bind the authorization record to the same protocol and deploy-identity scope reference carried by deployment evidence;
- validate the legacy staging target contract with `scripts/validate_staging_plan.py`;
- validate the WB-0034 plan/template boundary with `scripts/validate_wb0034_manifest.py`;
- validate the WB-0034 readiness component with `scripts/validate_wb0034_readiness.py`;
- run the authoritative combined final gate with `scripts/validate_wb0034_packet.py --repo-root <checked-out-main> --artifact-dir <exact-two-file-artifact-dir>`;
- require the combined gate to prove that `HEAD` equals the trusted `main` commit and that manifest/readiness/evidence source commits equal that same commit;
- require the evidence bundle digest to match readiness and its internal authorization to bind source commit, run id, destination, artifact set, protocol, deploy-identity scope, and rollback permission;
- require each evidence artifact SHA-256 to match the exact no-follow-read local bytes that the deployment runner will upload;
- require marker semantics to match the same final packet, not merely its recorded digest;
- require manifest, readiness, and evidence authorization references to match;
- confirm target URL/path from canonical state;
- confirm deployment protocol and credential scope evidence;
- confirm secret aliases exist without printing values;
- resolve the canonical staging root and require exact equality with the approved path;
- inspect the candidate destination without following links and require it to be absent;
- confirm there is no intermediate destination component below the staging root;
- record the sanitized preflight receipt.

The legacy target validator and the standalone manifest/readiness validators are necessary component checks but are not sufficient for a final first-write authorization packet. The combined WB-0034 packet validator is the authoritative final preflight gate because it binds the packet to trusted `main`, the checked-out source commit, the exact no-follow-read local artifact bytes, strict version-marker semantics, and the hash-bound evidence bundle.

Any failure stops the procedure.

### Phase B — future approved remote write

Only after fresh authorization and a passing final packet:

1. connect using the verified deployment protocol and approved staging deploy identity;
2. resolve the target base path to `/home/eimyherr/domains/staging.eimyherrer.com/public_html`;
3. fail if the resolved base differs from the approved canonical staging path;
4. derive exactly one direct-child destination `cybercore-canary-<run_id>/`;
5. perform a non-following metadata check on that destination and fail unless it is absent;
6. reject any symlink encountered from the canonical staging root downward;
7. immediately before creation, re-resolve the parent and require it to remain the canonical staging root;
8. create only that one unique directory with fail-if-exists semantics;
9. upload only the already-validated `index.html` and `cybercore-version.json` bytes with no-overwrite semantics;
10. disconnect;
11. run effect verification;
12. create a sanitized evidence receipt.

No command may traverse or write the production document root.

## Effect verification

The verifier must independently confirm:

- `https://staging.eimyherrer.com/cybercore-canary-<run_id>/` returns success;
- `https://staging.eimyherrer.com/cybercore-canary-<run_id>/cybercore-version.json` is reachable;
- marker `repository` equals `cyberDJs/CyberCore`;
- marker `commit` equals the exact approved source commit;
- marker `branch` equals `main`;
- marker `built_at` is a valid UTC timestamp;
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
- authorization protocol or deploy-identity scope differs from deployment evidence;
- a production-wide credential would be reused without an explicit risk decision;
- candidate destination already exists;
- any destination component below the canonical staging root is a symlink;
- candidate parent does not resolve exactly to the canonical staging root immediately before creation;
- checked-out `HEAD` differs from the trusted `main` commit;
- source commit is not exact or differs anywhere in manifest/readiness/evidence/checked-out `HEAD`;
- run id, destination, artifact set, authorization reference, protocol, deploy-identity scope, or rollback permission differ across the final packet;
- evidence-bundle SHA-256 does not match the readiness binding;
- any evidence artifact digest differs from the exact local file bytes that would be uploaded;
- any local artifact-directory component is a symlink or cannot be opened with no-follow directory semantics;
- the local artifact directory contains anything other than the exact two approved files;
- either local deployment artifact is missing, substituted, symlinked, non-regular, or cannot be opened relative to the pinned artifact directory without following links;
- `cybercore-version.json` is invalid/ambiguous JSON, has missing or additional keys, contains a non-UTC build timestamp, or disagrees with the final packet on repository/commit/branch/environment/run id;
- target path differs from canonical staging path;
- no-overwrite behavior cannot be guaranteed;
- rollback scope is ambiguous;
- secret values would be exposed in machine artifacts, comments, URLs, private-key blocks, logs, or evidence;
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
