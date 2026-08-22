# First Live Staging Write Gate v0

Date: 2026-08-22
Work block: `WB-0034`

## Purpose

Define the gate that must be passed before CyberCore performs its first remote write to InterServer staging.

## Gate checklist

- Target id is `interserver-shared-hosting-staging`.
- Staging URL is verified.
- Staging document root is verified and not production.
- Deploy protocol is verified for the intended first-write path.
- Deploy identity/credential scope is verified and does not silently grant automated production writes.
- Secret aliases are present in approved storage without value disclosure.
- Rollback mode is selected and scoped.
- Effect verifier is implemented and dry-run ready.
- Exact source commit and local artifact hashes are pinned.
- Candidate destination is a unique direct child of the canonical staging root.
- Existing/symlink destination checks and canonical-parent revalidation pass.
- Plan receipt exists.
- Jan Kočí explicitly authorizes the first remote write.

## Result values

```text
AUTHORIZED
BLOCKED
FAILED_PREFLIGHT
```

## Verified now

- target id;
- staging URL `https://staging.eimyherrer.com`;
- staging document root `/home/eimyherr/domains/staging.eimyherrer.com/public_html`;
- production document root metadata `/home/eimyherr/domains/eimyherrer.com/public_html`;
- staging/production path non-overlap;
- Cloudflare authoritative DNS;
- staging HTTP/HTTPS reachability.

## First-write shape

The first mutation is planned as a no-overwrite two-file canary in one unique directory directly beneath the staging root:

```text
cybercore-canary-<run_id>/
```

This avoids a separate `cybercore-canary` parent-directory mutation. No staging-root overwrite and no symlink promotion are part of the first cycle.

Production safety is checked through the already-verified path boundary, destination allowlisting, non-following path checks, and write-scope evidence. The gate does not require a production application URL/content read.

## Machine validation

The WB-0034 readiness snapshot is validated by:

```text
scripts/validate_wb0034_readiness.py
```

It is intentionally separate from the legacy WB-0029 readiness schema. The current artifact must be schema-valid while remaining blocked until every first-write runtime gate and fresh operator authorization is satisfied.

## Current state

`BLOCKED`

Remaining blockers:

- deployment protocol not yet verified for the first write;
- least-privilege deploy identity/credential scope not yet verified;
- required secret aliases not yet evidenced ready;
- rollback action not runtime-verified;
- effect verifier not yet implemented/dry-run verified;
- exact source commit and artifact hashes not yet pinned for the live run;
- fresh first remote-write authorization not granted.

WB-0034 preparation does not authorize `staging_apply`.
