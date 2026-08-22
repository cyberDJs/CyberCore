# Self-Deployment Target Registry v0

Date: 2026-08-22
Work block: `WB-0034`

## Purpose

The target registry stores non-secret deployment target metadata for CyberCore self-deployment.

## Current target

```text
interserver-shared-hosting-staging
```

Verified WB-0033 identity:

- staging URL: `https://staging.eimyherrer.com`;
- staging document root: `/home/eimyherr/domains/staging.eimyherrer.com/public_html`;
- production document root metadata: `/home/eimyherr/domains/eimyherrer.com/public_html`;
- staging/production non-overlap: verified;
- public origin: `162.250.126.107`;
- authoritative DNS: Cloudflare;
- staging DNS mode: DNS only;
- HTTP/HTTPS reachability: verified.

## Allowed fields

- target id;
- provider;
- environment class;
- non-secret URL/path identity;
- deployment method status;
- secret aliases;
- preflight requirements;
- rollback mode;
- evidence requirements.

## Denied fields

- passwords;
- API tokens;
- SSH private keys;
- TOTP seeds;
- cookies;
- recovery codes;
- production credential values.

## Lifecycle

```text
DRAFT
-> TARGET_IDENTIFIED
-> CAPABILITY_VERIFIED
-> SECRETS_ALIASED
-> ROLLBACK_VERIFIED
-> READY_FOR_DRY_RUN
-> READY_FOR_STAGING_APPLY
```

## Current lifecycle state

`TARGET_IDENTIFIED`

WB-0033 moved the target out of `DRAFT` by verifying the real staging hostname, document root, production-path exclusion, DNS, and TLS.

WB-0034 must not advance to `CAPABILITY_VERIFIED` until the actual first-write deployment protocol and target write behavior are verified without performing the write.

The first-write candidate is intentionally one unique direct-child directory:

```text
cybercore-canary-<run_id>/
```

This avoids a separate canary parent-directory mutation. The future runner must reject an existing or symlink destination and re-verify that the destination parent resolves exactly to the canonical staging root immediately before creation.

Remaining blockers:

- SFTP/SSH deployment protocol verification;
- least-privilege deploy identity/credential scope;
- secret-alias readiness without value disclosure;
- rollback execution semantics;
- effect verifier implementation/dry run;
- exact deploy source commit and artifact hashes;
- fresh explicit operator authorization for the first remote write.

The target remains fail-closed for `staging_apply`.
