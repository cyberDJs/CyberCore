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

The first write uses one unique directory directly beneath the verified staging document root so there is no separate parent-directory mutation:

```text
cybercore-canary-<run_id>/index.html
cybercore-canary-<run_id>/cybercore-version.json
```

Planned public verifier paths:

```text
https://staging.eimyherrer.com/cybercore-canary-<run_id>/
https://staging.eimyherrer.com/cybercore-canary-<run_id>/cybercore-version.json
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

1. create one direct-child directory `.../public_html/cybercore-canary-<run_id>/`;
2. upload exactly `index.html` and `cybercore-version.json` into that directory;
3. perform no overwrite outside that unique directory;
4. reject an existing or symlinked destination and re-verify that its parent resolves to the canonical staging root immediately before creation;
5. perform no chmod/chown, symlink, package/service, PHP, DNS, mail, billing, DirectAdmin, Cloudflare, VPS, WordPress, Nextcloud, registrar, or production mutation;
6. if rollback is explicitly included in the same authorization, remove only the directory created for that run after verifying its exact path.

If path resolution, credential scope, protocol behavior, source identity, artifact identity, or rollback scope is ambiguous, abort before the first remote write.

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

Primary first-write rollback is intentionally simple: because the deployment is no-overwrite into a unique direct-child directory, rollback is deletion of only that exact run directory if and only if deletion is included in the future authorization.

No symlink promotion is used in the first cycle. This avoids assuming shared-hosting symlink semantics before they are verified.

### G6 — effect verifier

`PLAN_DEFINED; IMPLEMENTATION/DRY_RUN_PENDING`

Required checks:

- staging canary URL returns HTTP success;
- `cybercore-version.json` exists and its commit equals the approved manifest commit;
- path-resolution and runner evidence prove writes were constrained to the exact approved staging destination;
- no denied path was touched;
- no denied provider/DNS/credential mutation occurred;
- receipt contains no secret values.

Production safety is proven by the verified staging/production path boundary plus destination allowlisting and write-scope evidence. WB-0034 does not grant production application-content reads or production URL fetches merely to compare state.

### G7 — exact trusted-main source commit

`PENDING_AFTER_WB0034_MERGE`

The final runtime manifest, readiness artifact, sanitized evidence bundle, deployment runner checkout, and trusted `main` ref must all bind to one exact commit. The combined final gate prefers fetched `origin/main` and falls back only to local `main` when no remote-tracking ref exists. `HEAD` must equal that trusted main commit.

`TBD`, branch-only identity, arbitrary 40-hex strings, feature-branch `HEAD`, mismatched commit values, or moving refs are not acceptable for the final packet.

### G8 — explicit first remote-write authorization

`NOT_GRANTED`

WB-0034 preparation does not authorize the remote write. A later approval must name the exact source commit, run id, protocol, deploy identity/scope, target path, two-file artifact, and rollback scope.

The authorization record inside the evidence bundle must repeat the approved protocol and deploy-identity scope reference and must match deployment evidence exactly.

### G9 — hash-bound supporting evidence

`DESIGN_IMPLEMENTED; RUNTIME_EVIDENCE_PENDING`

Readiness status labels are not sufficient evidence. A final READY decision requires a sanitized evidence bundle whose SHA-256 is recorded in the readiness artifact. The bundle must bind the exact source commit, run id, destination, two artifact hashes, deployment protocol, capability/scope references, verifier evidence, authorization reference, and rollback permission.

The combined packet validator must prove the evidence digest and cross-document bindings before it can return READY.

### G10 — exact local artifact bytes

`DESIGN_IMPLEMENTED; RUNTIME_ARTIFACTS_PENDING`

The two SHA-256 values in evidence are not accepted merely because they are syntactically valid. The combined final packet gate requires an explicit local artifact directory, rejects symlinked artifact paths, hashes the exact `index.html` and `cybercore-version.json` bytes that would be uploaded, and requires those digests to equal the evidence bundle.

A fabricated digest, substituted file, missing file, or symlinked local artifact keeps the packet BLOCKED.

## Machine-validatable first-write contract

WB-0034 uses dedicated validators so the first-write gate does not silently overload the legacy WB-0029 staging readiness contract.

Canonical implementation files include:

- `.cybercore/deploy/readiness/interserver-staging-readiness.wb0034.yaml`;
- `.cybercore/deploy/manifests/interserver-staging-wb0034-plan.yaml`;
- `src/cybercore/first_write.py`;
- `src/cybercore/first_write_manifest.py`;
- `src/cybercore/first_write_evidence.py`;
- `src/cybercore/first_write_packet.py`;
- `src/cybercore/first_write_security.py`;
- `scripts/validate_wb0034_readiness.py`;
- `scripts/validate_wb0034_manifest.py`;
- `scripts/validate_wb0034_packet.py`;
- regression tests under `tests/test_wb0034_*.py`.

The current repository artifacts remain plan-only and BLOCKED. The readiness validator may become READY only when its status fields are supported by a valid hash-bound evidence bundle. The final remote-write authorization packet has a stricter combined gate: populated manifest/readiness data, the hash-bound evidence bundle, trusted `main`, checked-out repository `HEAD`, and exact local artifact bytes must agree. Run id, destination, artifact set, artifact digests, authorization reference, protocol, deploy-identity scope, and rollback permission must remain consistently bound.

The WB-0034 machine YAML artifacts are intentionally comment-free and raw-text scanned before parsing. Credential-like assignments, credential-bearing URLs, YAML comments, duplicate keys, unsupported structures, secret values, and the broader private-key PEM/header family including EC, DSA, PGP, encrypted, OpenSSH, RSA, and generic private-key forms fail closed.

`remote_write_requested`, `remote_write_allowed`, and `production_write_allowed` remain false even when a final approval packet becomes complete; execution remains a separate authority boundary.

No change in this work block may weaken the invariant:

```text
remote_write_requested: false
remote_write_allowed: false
production_write_allowed: false
```

## Approval packet to produce

Before requesting the first staging-write authorization, the handoff must contain:

- exact trusted-`main` source commit and proof checked-out `HEAD` equals it;
- exact run id;
- verified deployment protocol;
- deploy identity safe reference and scope result;
- secret-alias readiness result without values;
- exact direct-child destination directory;
- exact two-file artifact list and SHA-256 values computed from the local files to be uploaded;
- sanitized hash-bound evidence bundle reference and digest;
- verifier commands/URLs;
- rollback action limited to that run directory;
- fresh authorization reference bound to commit/run/destination/artifacts/protocol/deploy-scope/rollback;
- expected evidence receipt fields;
- explicit stop conditions;
- passing `validate_wb0034_packet.py --artifact-dir <exact-artifact-dir>` result from the exact checked-out trusted-main source commit.

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
- dedicated WB-0034 manifest, readiness, evidence, raw-secret, and combined packet validators are internally consistent and regression-tested;
- arbitrary status labels, arbitrary evidence references, mismatched/nonexistent source SHAs, feature-branch HEAD, cross-document commit/run/destination/artifact mismatches, fabricated artifact digests, protocol/scope authorization mismatches, broader private-key headers, and secret-bearing comments/credential URLs fail closed;
- current readiness evidence records verified target identity and all remaining runtime blockers without overclaim;
- exact mutation and rollback scope are documented;
- symlink/ancestor escape and parent-directory ambiguity are eliminated from the first-write design;
- CI and CodeQL pass on the exact PR head;
- fresh Codex review finds no valid unresolved issue;
- remote write remains blocked.

A subsequent execution step may proceed only after the remaining runtime gates are verified and the operator grants fresh explicit first staging remote-write authorization.
