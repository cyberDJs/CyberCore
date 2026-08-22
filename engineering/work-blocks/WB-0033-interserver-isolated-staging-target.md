# WB-0033 — InterServer Isolated Staging Target

## Status

`AUTHORIZED_FOR_PREP_AND_BOUNDED_APPLY`

Date: 2026-08-22
Provider: InterServer shared hosting
Parent discovery: `WB-0032 — InterServer Staging Capability Discovery`
Target service: `website_id=1439764`, primary hostname `eimyherrer.com`

## Goal

Create one isolated, explicitly non-production staging target under the existing InterServer shared-hosting service so WB-0032 can resume capability discovery without inspecting or modifying the production document root.

Preferred target identity:

- hostname: `staging.eimyherrer.com`
- DirectAdmin owner: the existing user that owns `eimyherrer.com`
- document root: a dedicated directory below the account's `~/domains/` tree and outside the production `eimyherrer.com/public_html` tree, preferably the DirectAdmin default for new subdomains (`~/domains/staging.eimyherrer.com/public_html`) when the target server supports it

## Authorization

On 2026-08-22 the operator explicitly continued from the WB-0032 staging-identity blocker with: `ok, pojd na to` after the proposed next step was stated as creating an isolated InterServer staging target without touching production `eimyherrer.com`.

This work block interprets that authorization narrowly as permission to:

- inspect the minimum existing webhosting / DirectAdmin metadata required to identify the correct account and API surface;
- create exactly one staging subdomain/virtual-host identity `staging.eimyherrer.com` on the existing `website_id=1439764` service;
- create only the minimum corresponding DNS record when DirectAdmin/provider behavior requires it for that staging hostname;
- create the staging document-root directory only as a direct consequence of the DirectAdmin subdomain-creation operation;
- verify the new staging target non-destructively.

Not authorized:

- modifying, deleting, moving, copying, reading application contents from, or traversing the production document root;
- modifying production application files, databases, mail, WordPress, Nextcloud, DNS records unrelated to the new staging hostname, or the apex/www production records;
- ordering a new paid InterServer webhosting service;
- deploying CyberCore or any application content into staging;
- creating or rotating persistent credentials;
- creating a temporary/one-time DirectAdmin login key unless separately and explicitly authorized;
- changing ownership, chmod/chown, package/service configuration, PHP configuration, SSL policy, mail routing, billing, VPS state, or registrar settings;
- merging this branch or any PR into `main` without a separate operator approval.

## Current evidence

WB-0032 established after a one-time separately authorized API-key rotation:

- InterServer REST `/apiv2/websites`: HTTP 200;
- InterServer MCP `getWebsiteList`: HTTP 200;
- both independently returned exactly one active webhosting service: `website_id=1439764`, `website_hostname=eimyherrer.com`;
- no remote content write was performed during WB-0032 discovery.

The InterServer MCP capability inventory shows that `addWebsite` would place a new paid webhosting order and generate invoices. WB-0033 therefore explicitly forbids using `addWebsite`.

DirectAdmin documentation identifies user-level subdomain creation as the appropriate operation on an existing hosting account. The server-specific `/static/swagger.json` MUST be inspected before selecting a new JSON `/api/...` endpoint. If no suitable new API operation exists, documented legacy `CMD_API_SUBDOMAINS` / `CMD_SUBDOMAIN` may be considered only after exact target-server capability review.

## Preflight

### VERIFY-A — technical

Before mutation, prove all of the following:

1. `website_id=1439764` is active and maps to `eimyherrer.com`.
2. The control panel type is DirectAdmin.
3. The exact DirectAdmin server/port and user identity are known without exposing a password or session token.
4. The target server's `/static/swagger.json` has been fetched and the exact subdomain-create operation selected, or the documented legacy endpoint has been selected only because the new API lacks the capability.
5. `staging.eimyherrer.com` does not already exist in the DirectAdmin account.
6. The proposed document root is outside the production `eimyherrer.com/public_html` tree.
7. No paid service order is involved.
8. A deterministic post-create verification and rollback operation are known.

### VERIFY-B — safety / optimization

Before mutation, prove all of the following:

1. The change is exactly one staging hostname.
2. No production path content will be inspected or changed.
3. No unrelated DNS record will be changed.
4. No persistent credential will be created, rotated, reset, or disclosed.
5. If the only available DirectAdmin access path requires creating a temporary login key, stop with `BLOCKED` and request a separate bounded authorization.
6. Raw provider payloads, session URLs, passwords, cookies, API keys, and login keys are not persisted in GitHub/chat/evidence.
7. Rollback is limited to deleting the new staging subdomain/DNS artifacts created by this work block; production artifacts are never rollback targets.

Both VERIFY-A and VERIFY-B must be `PASS` before apply.

## Apply plan

Preferred apply sequence:

1. Read InterServer service metadata for `website_id=1439764`; sanitize evidence.
2. Fetch target DirectAdmin `/static/swagger.json` read-only.
3. Read the existing subdomain list for `eimyherrer.com` and assert `staging` absent.
4. Resolve an already-existing approved DirectAdmin authentication path. If none exists, stop `BLOCKED`; do not manufacture credentials.
5. Create `staging.eimyherrer.com` using the server-supported user-level DirectAdmin API.
6. Ensure the resulting document root is isolated from `eimyherrer.com/public_html`; prefer DirectAdmin's current separate-subdomain default path when available.
7. Verify the subdomain exists and resolve only the new staging hostname's DNS/HTTP metadata needed for effect verification.
8. Record receipt with `production_content_accessed=false` and `application_deploy_performed=false`.

## Rollback

Rollback trigger:

- wrong hostname;
- document root resolves inside the production public document root;
- unexpected DNS mutation;
- control-panel operation affects any unrelated domain;
- verification cannot prove isolation.

Rollback action:

- remove only the newly created `staging.eimyherrer.com` subdomain and any DNS record created specifically for it;
- do not delete or modify any production domain/path/record;
- verify the staging artifacts are absent afterward.

If rollback scope is ambiguous, stop and preserve state for manual review rather than deleting anything.

## Success criteria

WB-0033 reaches `VERIFIED` only when evidence proves:

- `staging.eimyherrer.com` exists on the existing InterServer shared-hosting account;
- it has a dedicated document root outside `eimyherrer.com/public_html`;
- no new paid hosting service was ordered;
- production application content was not accessed or mutated;
- no persistent credential was created or rotated;
- the staging hostname can be identified independently enough for WB-0032 to resume read-only capability discovery;
- no CyberCore/application deployment has occurred.

## Current terminal state

`ACTIVE — PREP/READ-ONLY PREFLIGHT`
