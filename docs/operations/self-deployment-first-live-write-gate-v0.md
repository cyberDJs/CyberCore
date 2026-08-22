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
- Exact source commit is pinned.
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

The first mutation is planned as a no-overwrite two-file canary under:

```text
cybercore-canary/<run_id>/
```

No staging-root overwrite and no symlink promotion are part of the first cycle.

## Current state

`BLOCKED`

Remaining blockers:

- deployment protocol not yet verified for the first write;
- least-privilege deploy identity/credential scope not yet verified;
- required secret aliases not yet evidenced ready;
- rollback action not runtime-verified;
- effect verifier not yet implemented/dry-run verified;
- exact source commit not yet pinned for the live run;
- fresh first remote-write authorization not granted.

WB-0034 preparation does not authorize `staging_apply`.
