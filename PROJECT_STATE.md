# CyberCore Project State

_Last updated: 2026-08-22 15:00 CEST_

## Source of truth

- Repository: `cyberDJs/CyberCore`
- Stable branch: `main`
- Canonical product state: GitHub `main`
- Evidence/archive/collaboration layer: Google Drive `CyberCore/CASER-E`
- Active branch: `wb-0034-first-staging-deployment-preflight`
- Active pull request: #55 — WB-0034 first InterServer staging deployment preflight
- Active artifact: `WB-0034 — First Staging Deployment Preflight`
- Active work block: `WB-0034 — First Staging Deployment Preflight`
- Last verified `main`: `d74497eb0730a0d112cbf7957593f23cb35b5e71`
- Governance rule: provider mutation, secret mutation, staging apply, and production mutation authority remains reserved to explicit operator authorization
- CI policy: GitHub Actions verification is required before merge
- CodeQL policy: Advanced setup is verified; GitHub Default setup is disabled to avoid conflicting scans

## Current milestone

PR #54 / WB-0033 was squash-merged into canonical `main` as:

```text
d74497eb0730a0d112cbf7957593f23cb35b5e71
```

That merge establishes the verified InterServer staging runtime baseline:

- InterServer shared-hosting service `website_id=1439764`;
- staging hostname `staging.eimyherrer.com`;
- staging document root `/home/eimyherr/domains/staging.eimyherrer.com/public_html`;
- production document-root metadata `/home/eimyherr/domains/eimyherrer.com/public_html`;
- verified non-overlap between staging and production document roots;
- Cloudflare authoritative DNS and DNS-only staging A record;
- HTTP/HTTPS reachability;
- DirectAdmin -> Cloudflare DNS-01 -> Let's Encrypt wildcard renewal path;
- standing unattended renewal authority for the existing `eimyherrer.com` + `*.eimyherrer.com` certificate only.

PR #54 did **not** deploy CyberCore/application content to staging and did not grant staging application remote-write authority.

The active slice is PR #55 / WB-0034. It prepares the first real CyberCore staging write up to the final human approval gate while keeping all remote writes blocked.

## Active objective

Prepare a minimal, fail-closed first staging deployment:

1. preserve ADR-0006 staging-only boundary;
2. treat WB-0033 as the canonical verified staging target baseline;
3. use one unique direct-child no-overwrite canary directory beneath the staging root;
4. deploy only two future canary files: `index.html` and `cybercore-version.json`;
5. verify the real deployment protocol before any write;
6. verify least-privilege deploy identity/credential scope before any write;
7. verify secret-alias readiness without reading or recording values;
8. validate rollback and effect-verifier semantics without production application reads;
9. pin an exact source commit and artifact hashes after WB-0034 merge;
10. obtain fresh explicit first staging remote-write authorization before `staging_apply`.

## Current status

- Work block: `WB-0034` active; repository-only preflight
- Branch: `wb-0034-first-staging-deployment-preflight`
- Pull request: #55, draft
- PR #54 / WB-0033: merged as `d74497eb0730a0d112cbf7957593f23cb35b5e71`
- PR #54 verification: CI #211 PASS, CodeQL #208 PASS, clean fresh Codex exact-head review, all review threads resolved
- Staging target identity: VERIFIED
- Staging URL: `https://staging.eimyherrer.com`
- Staging document root: `/home/eimyherr/domains/staging.eimyherrer.com/public_html`
- Production document-root metadata: `/home/eimyherr/domains/eimyherrer.com/public_html`
- Production/staging non-overlap: VERIFIED
- Production application content read: false
- Cloudflare authoritative DNS: VERIFIED
- Staging DNS record: VERIFIED, DNS only
- Staging HTTP/HTTPS: VERIFIED
- DirectAdmin Cloudflare ACME path: VERIFIED
- Wildcard manual renewal: VERIFIED
- Standing unattended renewal authority: existing wildcard/existing integration only
- First-write artifact plan: static two-file canary
- First-write destination: one direct-child `cybercore-canary-<run_id>/` directory
- First-write overwrite: forbidden
- Existing/symlink destination: reject
- First-write symlink promotion: forbidden
- WB-0034 dedicated readiness schema/validator: IMPLEMENTED
- Deployment protocol for first write: UNKNOWN / read-only verification required
- Deploy identity scope: UNKNOWN / must be verified before first write
- Secret-alias readiness: UNKNOWN
- Rollback runtime readiness: UNKNOWN
- Effect verifier runtime readiness: UNKNOWN
- Exact live source commit and artifact hashes: pending after WB-0034 merge
- First staging remote-write authorization: NOT GRANTED
- `remote_write_requested`: false
- `remote_write_allowed`: false
- `production_write_allowed`: false
- Secret values stored in ordinary evidence: none

## First-write design

The first live staging write is intentionally smaller than a full CyberCore application deployment.

Planned destination:

```text
/home/eimyherr/domains/staging.eimyherrer.com/public_html/cybercore-canary-<run_id>/
```

Planned public URLs:

```text
https://staging.eimyherrer.com/cybercore-canary-<run_id>/
https://staging.eimyherrer.com/cybercore-canary-<run_id>/cybercore-version.json
```

Planned artifacts:

```text
index.html
cybercore-version.json
```

The destination is directly beneath the canonical staging root; no separate canary parent directory is created. The live operation, if later authorized, must fail if the destination exists or is a symlink, re-verify that the destination parent resolves to the canonical staging root immediately before creation, and must not overwrite the staging root, create a promotion symlink, or touch production.

Production safety verification uses the already-verified production/staging path boundary plus destination allowlisting and write-scope evidence. WB-0034 does not authorize production application content reads or production URL fetches for comparison.

## Secret-handling boundary

Plaintext secrets remain denied in:

- GitHub;
- Google Drive;
- ChatGPT Library;
- Slack;
- chat;
- CASER documents;
- ordinary evidence logs.

Required deployment secret aliases remain:

- `INTERSERVER_STAGING_HOST`;
- `INTERSERVER_STAGING_USER`;
- `INTERSERVER_STAGING_PORT`;
- `INTERSERVER_STAGING_SSH_KEY_OR_SFTP_PASSWORD`.

WB-0034 may record only alias presence/readiness and safe scope metadata. It does not authorize credential creation, rotation, reset, or disclosure.

A production-wide write credential is not preapproved for an automated first-write runner. The actual deploy identity/credential scope must be verified before the final authorization request.

## Self-deployment boundary

Allowed in PR #55 / WB-0034 without further provider authorization:

- repository documentation and state reconciliation;
- plan-only manifest creation;
- non-secret target-registry reconciliation;
- repository validator/test implementation;
- local/dry-run validation;
- read-only planning and review;
- recording known target identity and remaining unknowns.

Still blocked:

- `staging_apply`;
- remote mkdir/upload/overwrite/delete/chmod/chown/symlink operations;
- creating or rotating deployment credentials;
- production application-content traversal/read/write;
- DNS, mail, billing, DirectAdmin, Cloudflare, VPS, WordPress, Nextcloud, registrar, PHP, ownership, permission, package, or service mutation;
- recurring or automatic deployment.

The standing ACME authority does not broaden into staging application deployment authority.

## Recent completed state changes

### PR #51 — WB-0031 staging runtime gate preflight

Merged as `d4ac1c0fa8139cf5fb6a45e81d16a83c912bf684` with CI, CodeQL, and Codex gates green. It established the runtime preflight contract while preserving no-remote-write semantics.

### PR #52 — WB-0032 definition and kickoff

Merged as `304f4234e4f52c2375d904b45d1ed0c4fe31511c`. It defined the two-phase InterServer staging capability discovery model and separate read-only authority gate.

### PR #53 — WB-0032 Phase B documentation/preflight

Merged as `70346d63ba2b17df17085797e963bb9dbd692282`. It provided the bounded provider discovery procedure without staging application write authority.

### PR #54 — WB-0033 isolated InterServer staging target

Merged as `d74497eb0730a0d112cbf7957593f23cb35b5e71` after exact-head CI #211, CodeQL #208, clean fresh Codex review, and resolved review threads.

Delivered/verified:

- isolated DirectAdmin staging target;
- production/staging document-root non-overlap;
- Cloudflare DNS-only staging record;
- external HTTP/HTTPS;
- DirectAdmin Cloudflare ACME provider;
- successful wildcard renewal;
- bounded standing wildcard unattended-renewal authority;
- no CyberCore/application deployment.

Earlier merged artifact history remains canonical in Git history and the structured `.cybercore/project.yaml` completed register.

## Current work block

### WB-0034 — First Staging Deployment Preflight

PR #55 prepares the first remote staging write without performing it.

The intended first-write scope is one unique no-overwrite `cybercore-canary-<run_id>/` direct-child directory containing only two non-secret files. The design deliberately avoids a full application rollout, a separate canary parent-directory mutation, and symlink promotion during the first cycle.

A dedicated WB-0034 readiness validator now models the actual first-write blockers and replaces the incompatible assumption that a production URL must be fetched after deployment.

Before the final approval request, WB-0034 must establish:

- actual SFTP or SSH/SFTP deployment protocol;
- deploy identity/credential scope;
- secret-alias readiness;
- rollback semantics;
- effect verifier readiness;
- exact source commit, artifact hashes, and run id.

If any of these cannot be verified safely, the first write remains blocked.

## Security follow-up

- Six high-severity transitive `npm audit` findings remain deferred security debt in the isolated visual documentation toolchain.
- The dedicated Cloudflare ACME token must remain least-privilege and zone-scoped.
- Future unattended wildcard renewal should be recorded as observed operational behavior only after an actual scheduled renewal cycle occurs.
- First-write deployment credentials require scope verification before use; production-wide credential reuse is not implicitly authorized.
- Production deployment remains outside WB-0034 and requires a separate production MOP plus explicit approval.

## Next action

1. Complete exact-head CI, CodeQL, and fresh Codex re-review after the WB-0034 hardening changes.
2. Repair any remaining valid repository finding.
3. Obtain separate authority before any live InterServer read-only deployment-protocol/identity-scope probe required by this work block.
4. Verify secret aliases without exposing values.
5. Dry-run the two-file canary build/manifest/verifier locally.
6. Merge WB-0034 only after separate merge approval.
7. Pin the resulting exact `main` commit and assemble the final first-write authorization packet.
8. Do not execute the remote write until the operator explicitly authorizes that exact packet.

<!-- CYBERCORE:CHECKPOINT:START -->
<!-- CYBERCORE:PROJECT-STATE-CHECKPOINT:pr55-wb0034-first-staging-deployment-preflight -->
## Manual repository checkpoint

- Generated: `2026-08-22T15:00:00+02:00`
- Branch: `wb-0034-first-staging-deployment-preflight`
- Pull request: #55
- Active artifact: `WB-0034`
- Active work block: `WB-0034 — First Staging Deployment Preflight`
- Last verified main: `d74497eb0730a0d112cbf7957593f23cb35b5e71`
- WB-0033 / PR #54: merged and canonical
- Staging target identity: VERIFIED
- First-write artifact plan: static two-file direct-child canary
- WB-0034 readiness schema/validator: IMPLEMENTED
- First-write deployment protocol: UNKNOWN
- Deploy identity scope: UNKNOWN
- Secret-alias readiness: UNKNOWN
- Remote write requested: false
- Remote write allowed: false
- Production write allowed: false
- First remote-write authorization: NOT GRANTED
- Secret values recorded: false
- Project Kernel: present
- Project State: WB-0034 repository-only preflight active; first live staging write remains blocked
<!-- CYBERCORE:CHECKPOINT:END -->
