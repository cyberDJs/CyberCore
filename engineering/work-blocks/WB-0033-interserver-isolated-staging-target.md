# WB-0033 — InterServer Isolated Staging Target

## Status

`VERIFIED`

Date: 2026-08-22
Provider: InterServer shared hosting
Authoritative DNS: Cloudflare
Parent discovery: `WB-0032 — InterServer Staging Capability Discovery`
Target service: `website_id=1439764`, primary hostname `eimyherrer.com`

## Goal

Create one isolated, explicitly non-production staging target under the existing InterServer shared-hosting service so WB-0032 can resume capability discovery without reading or modifying production application content.

Verified target identity:

- hostname: `staging.eimyherrer.com`
- DirectAdmin owner: existing owner of `eimyherrer.com`
- staging document root: `/home/eimyherr/domains/staging.eimyherrer.com/public_html`
- production document root metadata: `/home/eimyherr/domains/eimyherrer.com/public_html`
- staging/production path equality: false
- staging inside production path: false
- production inside staging path: false
- public origin: `162.250.126.107`
- DNS mode: Cloudflare authoritative, DNS only for staging

## Authorization history

On 2026-08-22 the operator explicitly continued from the WB-0032 staging-identity blocker with `ok, pojd na to` after the proposed next step was stated as creating an isolated InterServer staging target without touching production `eimyherrer.com` application content.

The operator subsequently granted separate explicit authorization for:

- creation of the single Cloudflare DNS A record `staging.eimyherrer.com -> 162.250.126.107` as DNS only;
- creation of a dedicated Cloudflare ACME token for `eimyherrer.com` and storage in DirectAdmin as `CLOUDFLARE_DNS_API_TOKEN`;
- one manual wildcard certificate renewal for `eimyherrer.com` + `*.eimyherrer.com` through DirectAdmin using the configured Cloudflare ACME DNS provider;
- read-only discovery of the production `eimyherrer.com` document-root path metadata, without listing, traversing, statting, or reading production application content;
- standing authorization for future unattended automatic ACME renewals of the existing `eimyherrer.com` + `*.eimyherrer.com` certificate through the existing DirectAdmin -> Cloudflare DNS integration.

The standing ACME authorization is narrowly scoped to certificate renewal through the already configured provider. It does not authorize unrelated DNS changes, additional credential creation/rotation, application deployment, other production mutations, or PR merge.

## Verified evidence

WB-0032 established after a one-time separately authorized API-key rotation:

- InterServer REST `/apiv2/websites`: HTTP 200;
- InterServer MCP `getWebsiteList`: HTTP 200;
- both independently returned exactly one active webhosting service: `website_id=1439764`, `website_hostname=eimyherrer.com`;
- no remote content write was performed during WB-0032 discovery.

WB-0033 subsequently verified:

- DirectAdmin user-level subdomain creation succeeded using `/CMD_SUBDOMAIN`;
- `staging.eimyherrer.com` was absent before creation and present afterward;
- observed staging document root is `/home/eimyherr/domains/staging.eimyherrer.com/public_html`;
- after separate explicit authorization, DirectAdmin `CMD_API_DOMAIN?action=document_root` returned production document-root metadata `/home/eimyherr/domains/eimyherrer.com/public_html` without reading production application content;
- normalized path comparison proves the staging and production roots are distinct and neither contains the other;
- production application content was not listed, traversed, statted, read, or mutated;
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
- the operator has granted standing authorization for future unattended automatic renewals of that same wildcard certificate through the existing DirectAdmin -> Cloudflare ACME path.

A future unattended renewal has not yet been historically observed, but it is now explicitly authorized within the bounded standing scope above.

## Safety boundary

The following remain not authorized by WB-0033:

- modifying, deleting, moving, copying, listing, traversing, statting, or reading application contents from the production document root;
- modifying production application files, databases, mail, WordPress, Nextcloud, unrelated DNS records, apex or `www` production records;
- ordering a new paid InterServer webhosting service;
- deploying CyberCore or any application content into staging;
- creating or rotating additional credentials outside the separately authorized ACME token action;
- using the standing ACME renewal authority for any DNS mutation other than the DNS-01 challenge operations required for renewal of `eimyherrer.com` + `*.eimyherrer.com`;
- creating a temporary/one-time DirectAdmin login key;
- changing ownership, chmod/chown, package/service configuration, PHP configuration, mail routing, billing, VPS state, or registrar settings;
- merging this branch or PR without separate operator approval.

## Preflight result

### VERIFY-A — technical

PASS:

1. `website_id=1439764` is active and maps to `eimyherrer.com`.
2. Control panel is DirectAdmin.
3. DirectAdmin server and user identity were established without secret disclosure.
4. Target-server API behavior was inspected before apply.
5. `staging.eimyherrer.com` was proven absent before creation.
6. Production document-root metadata was later read under separate explicit authorization, and normalized path comparison proves the staging root is outside the production root and vice versa.
7. No paid service order was involved.
8. Deterministic post-create verification and rollback scope were known.

### VERIFY-B — safety / optimization

PASS:

1. Exactly one staging hostname was created.
2. Production application content was not listed, traversed, statted, read, or changed; only the separately authorized document-root path metadata was read.
3. Only the separately authorized staging DNS record was created; unrelated DNS was not changed.
4. No credential values were persisted in GitHub/chat/evidence.
5. No temporary DirectAdmin login key was created.
6. Raw passwords, cookies, API keys, tokens, session URLs, and login keys were not persisted in evidence.
7. Rollback scope remains limited to artifacts created specifically for this staging target.
8. Future unattended wildcard renewals are covered by separate explicit standing authorization and remain limited to the existing certificate and ACME path.

## Applied changes

1. Created DirectAdmin staging identity `staging.eimyherrer.com`.
2. Verified isolated staging document root `/home/eimyherr/domains/staging.eimyherrer.com/public_html`.
3. Created Cloudflare A record `staging.eimyherrer.com -> 162.250.126.107`, DNS only.
4. Verified public DNS resolution.
5. Verified HTTP and HTTPS reachability.
6. Configured DirectAdmin Cloudflare ACME DNS provider with a dedicated zone-scoped token.
7. Performed one explicitly authorized manual wildcard renewal.
8. Verified new Let's Encrypt wildcard certificate and staging HTTPS after renewal.
9. Under separate read-only production-metadata authorization, verified production document-root path `/home/eimyherr/domains/eimyherrer.com/public_html` and proved non-overlap with staging without reading application content.
10. Recorded explicit standing authorization for future unattended automatic renewal of the same wildcard certificate through the existing DirectAdmin -> Cloudflare integration; no additional provider configuration mutation was required for this authorization record.

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
- it has a dedicated document root outside the verified production document root;
- no new paid hosting service was ordered;
- production application content was not accessed beyond separately authorized document-root path metadata and was not mutated;
- the staging hostname resolves through the authoritative Cloudflare zone;
- HTTP and HTTPS are externally reachable;
- wildcard TLS issuance through DirectAdmin + Cloudflare DNS-01 is verified end-to-end;
- future unattended wildcard renewals are explicitly authorized under a narrow standing scope;
- no CyberCore/application deployment has occurred.

## Current terminal state

`VERIFIED`

WB-0033 has established the isolated InterServer staging target, proven staging/production document-root non-overlap using separately authorized path metadata, and verified the external Cloudflare DNS/TLS integration required for WB-0032 to continue capability discovery and for a later separately authorized staging deployment work block to proceed.
