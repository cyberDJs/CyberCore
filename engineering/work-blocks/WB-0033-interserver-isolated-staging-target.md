# WB-0033 — InterServer Isolated Staging Target

## Status

`VERIFIED`

Date: 2026-08-22
Provider: InterServer shared hosting
Authoritative DNS: Cloudflare
Parent discovery: `WB-0032 — InterServer Staging Capability Discovery`
Target service: `website_id=1439764`, primary hostname `eimyherrer.com`

## Goal

Create one isolated, explicitly non-production staging target under the existing InterServer shared-hosting service so WB-0032 can resume capability discovery without inspecting or modifying production application content.

Verified target identity:

- hostname: `staging.eimyherrer.com`
- DirectAdmin owner: existing owner of `eimyherrer.com`
- staging document root: `/home/eimyherr/domains/staging.eimyherrer.com/public_html`
- production document-root metadata: `/home/eimyherr/domains/eimyherrer.com/public_html`
- normalized path comparison: `same_path=false`, `staging_inside_production=false`, `production_inside_staging=false`
- public origin: `162.250.126.107`
- DNS mode: Cloudflare authoritative, DNS only for staging

## Authorization history

On 2026-08-22 the operator explicitly continued from the WB-0032 staging-identity blocker with `ok, pojd na to` after the proposed next step was stated as creating an isolated InterServer staging target without touching production application content.

The operator subsequently granted separate explicit authorization for:

- creation of the single Cloudflare DNS A record `staging.eimyherrer.com -> 162.250.126.107` as DNS only;
- creation of a dedicated Cloudflare ACME token for `eimyherrer.com` and storage in DirectAdmin as `CLOUDFLARE_DNS_API_TOKEN`;
- one manual wildcard certificate renewal for `eimyherrer.com` + `*.eimyherrer.com` through DirectAdmin using the configured Cloudflare ACME DNS provider;
- a narrowly scoped read-only DirectAdmin document-root metadata read for `eimyherrer.com`, without traversing or reading production application content;
- standing authorization for future unattended automatic renewal of the existing `eimyherrer.com` + `*.eimyherrer.com` certificate through the existing DirectAdmin -> Cloudflare ACME path.

The standing ACME authorization is limited to renewal of that existing certificate using the existing integration. It does not authorize unrelated DNS changes, new certificate identities, provider changes, additional credential mutation, application deployment, or production application-content access/mutation.

The operator separately authorized finalization and merge of PR #54 into `main` after exact-head CI, CodeQL, and Codex review gates pass.

## Verified evidence

WB-0032 established after a one-time separately authorized API-key rotation:

- InterServer REST `/apiv2/websites`: HTTP 200;
- InterServer MCP `getWebsiteList`: HTTP 200;
- both independently returned exactly one active webhosting service: `website_id=1439764`, `website_hostname=eimyherrer.com`;
- no remote content write was performed during WB-0032 discovery.

WB-0033 subsequently verified:

- DirectAdmin user-level subdomain creation succeeded using `/CMD_SUBDOMAIN`;
- `staging.eimyherrer.com` was absent before creation and present afterward;
- staging document root is `/home/eimyherr/domains/staging.eimyherrer.com/public_html`;
- separately authorized production document-root metadata is `/home/eimyherr/domains/eimyherrer.com/public_html`;
- normalized comparison proves staging and production document-root paths are distinct and neither contains the other;
- production application content was not read or mutated;
- no new paid InterServer webhosting service was ordered;
- Cloudflare is authoritative DNS for `eimyherrer.com`;
- the staging A record resolves publicly to `162.250.126.107`;
- staging remains `proxied=false` / DNS only;
- HTTP returns 200 from the InterServer origin;
- HTTPS returns 200 with successful certificate verification;
- DirectAdmin exposes and stores the Cloudflare ACME DNS provider configuration;
- a dedicated zone-scoped Cloudflare DNS token is stored in DirectAdmin without secret-value persistence in evidence;
- one manual wildcard renewal completed successfully through DirectAdmin + Cloudflare DNS-01 + Let's Encrypt;
- renewed certificate covers `eimyherrer.com` and `*.eimyherrer.com` and is valid through 2026-11-20;
- post-renewal `https://staging.eimyherrer.com` remains HTTP 200 with TLS verification success;
- future unattended renewal of the same wildcard certificate is explicitly authorized through the existing DirectAdmin -> Cloudflare ACME path.

## Review closure

Codex first reviewed exact head `fc410957e61c1c62a0fd59d1802c2302d93e2c41` and raised:

- P1: unattended wildcard renewal lacked separate standing authorization;
- P1: production/staging non-overlap lacked canonical production document-root evidence;
- P2: PR handoff text was stale.

All three findings were addressed. A fresh Codex review on exact head `82b90ca2ee7097d3959a2d4bfd0eeb60a2d9729d` reported no major issues.

That reviewed head passed:

- CI #190;
- Python 3.11/3.12/3.13/3.14;
- Ruff lint/format;
- Pyright;
- package build and wheel smoke;
- CodeQL #187;
- Codex re-review with no major issues.

After the operator explicitly authorized finalization and merge, documentation-only reconciliation commits were added to record that authority and align the evidence/work-block terminal state. Those final documentation commits do not broaden provider scope, but they do change the PR head, so exact-head CI, CodeQL, and Codex gates must pass again before the approved merge is executed.

## Safety boundary

The following remain not authorized by WB-0033:

- modifying, deleting, moving, copying, reading application contents from, or traversing the production document root;
- modifying production application files, databases, mail, WordPress, Nextcloud, unrelated DNS records, apex or `www` production records;
- ordering a new paid InterServer webhosting service;
- deploying CyberCore or any application content into staging;
- creating or rotating additional credentials outside the separately authorized ACME token action;
- changing the authorized ACME certificate identity or DNS provider without new approval;
- creating a temporary/one-time DirectAdmin login key;
- changing ownership, chmod/chown, package/service configuration, PHP configuration, mail routing, billing, VPS state, or registrar settings.

The approved merge of PR #54 changes repository state only; it does not broaden any provider or production mutation authority beyond the explicit approvals recorded above.

## Preflight result

### VERIFY-A — technical

PASS:

1. `website_id=1439764` is active and maps to `eimyherrer.com`.
2. Control panel is DirectAdmin.
3. DirectAdmin server and user identity were established without secret disclosure.
4. Target-server API behavior was inspected before apply.
5. `staging.eimyherrer.com` was proven absent before creation.
6. Staging and production document-root metadata were compared under separate explicit read-only authorization and proven non-overlapping.
7. No paid service order was involved.
8. Deterministic post-create verification and rollback scope were known.

### VERIFY-B — safety / optimization

PASS:

1. Exactly one staging hostname was created.
2. Production application content was not inspected or changed.
3. Only the separately authorized staging DNS record was created; unrelated DNS was not changed.
4. No credential values were persisted in GitHub/chat/evidence.
5. No temporary DirectAdmin login key was created.
6. Raw passwords, cookies, API keys, tokens, session URLs, and login keys were not persisted in evidence.
7. Rollback scope remains limited to artifacts created specifically for this staging target and the separately authorized ACME integration if intentionally retired.

## Applied changes

1. Created DirectAdmin staging identity `staging.eimyherrer.com`.
2. Verified isolated staging document root `/home/eimyherr/domains/staging.eimyherrer.com/public_html`.
3. Read production document-root path metadata only, under separate authorization, and proved non-overlap without reading application content.
4. Created Cloudflare A record `staging.eimyherrer.com -> 162.250.126.107`, DNS only.
5. Verified public DNS resolution.
6. Verified HTTP and HTTPS reachability.
7. Configured DirectAdmin Cloudflare ACME DNS provider with a dedicated zone-scoped token.
8. Performed one explicitly authorized manual wildcard renewal.
9. Verified new Let's Encrypt wildcard certificate and staging HTTPS after renewal.
10. Recorded standing authorization for future unattended renewal of that same wildcard certificate through the existing integration.

No CyberCore/application content was deployed.

## Rollback

Rollback trigger:

- wrong hostname;
- document root resolves inside the production public document root;
- unexpected DNS mutation;
- control-panel operation affects an unrelated domain;
- verification cannot prove isolation.

Rollback action:

- remove only the newly created `staging.eimyherrer.com` subdomain and the DNS record created specifically for it;
- do not delete or modify any production domain/path/record;
- separately remove the dedicated ACME provider credential only if the Cloudflare-backed wildcard renewal integration is intentionally retired;
- verify staging artifacts are absent afterward.

If rollback scope is ambiguous, stop and preserve state for manual review rather than deleting anything.

## Success criteria

PASS:

- `staging.eimyherrer.com` exists on the existing InterServer shared-hosting account;
- it has a dedicated document root distinct from and non-overlapping with production;
- no new paid hosting service was ordered;
- production application content was not accessed or mutated;
- the staging hostname resolves through the authoritative Cloudflare zone;
- HTTP and HTTPS are externally reachable;
- wildcard TLS issuance through DirectAdmin + Cloudflare DNS-01 is verified end-to-end;
- future unattended renewal of that same certificate has explicit standing authorization;
- no CyberCore/application deployment has occurred.

## Current terminal state

`VERIFIED — MERGE AUTHORIZED; FINAL EXACT-HEAD GATES PENDING`

WB-0033 has established the isolated InterServer staging target and the external Cloudflare DNS/TLS integration required for WB-0032 to continue capability discovery and for a later separately authorized staging deployment work block to proceed. The repository merge is authorized but remains fail-closed until final exact-head CI, CodeQL, and Codex gates are green.
