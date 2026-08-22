# WB-0032 InterServer Documentation Preflight

Date: 2026-08-22
Work block: `WB-0032 — InterServer Staging Capability Discovery`
Canonical base observed before this slice: `main@304f4234e4f52c2375d904b45d1ed0c4fe31511c`

## Purpose

Prepare the authorized WB-0032 Phase B read-only discovery from current provider documentation before making any authenticated provider request.

## Authorization observed

Jan Kočí explicitly authorized:

- InterServer staging only;
- read-only / non-mutating capability discovery;
- read-only SSH, SFTP, DirectAdmin, and provider/API probes as needed.

The authorization explicitly denies upload, overwrite, delete, chmod/chown, symlink creation, provider configuration mutation, credential rotation, staging remote write, production access, and persistence of secret values in ordinary evidence.

## Sources reviewed

Primary provider/control-panel documentation reviewed before execution:

1. InterServer REST/OpenAPI API documentation (`my.interserver.net/api-docs/`).
2. InterServer OpenAPI surface, documented as Management API version `0.9.0` with `/apiv2` live endpoints.
3. InterServer MCP Server guide dated 2026-06-30, documenting server version `0.9.0`, public and authenticated/private endpoints, OAuth/API-key/session authentication, and scoped read-only access.
4. InterServer current Standard Web Hosting technical-details page, documenting DirectAdmin and SSH access as product capabilities; actual account capability remains unverified until observed.
5. DirectAdmin current API documentation, which recommends the newer JSON `/api/...` API, exposes server-specific Swagger at `/static/swagger.json`, supports Basic HTTP authentication for API access, and retains documented legacy `/CMD_API_...` fallbacks.

## Findings

### InterServer management layer

- The modern REST/OpenAPI API should be preferred over legacy SOAP for new CyberCore integration.
- API-key authentication uses the `X-API-KEY` header; session authentication is also documented.
- InterServer now exposes an authenticated MCP interface suitable for AI/tool integration and documents read-only scopes.
- For webhosting discovery, the minimally required documented REST reads are `GET /websites` and `GET /websites/{id}`; `GET /websites/{id}/reverse_dns` is an optional identity corroboration read.

### Important safety finding

HTTP verb is not a sufficient policy classifier.

InterServer documents several `GET` endpoints that can cause side effects, including lifecycle, backup, welcome-email, or session-related operations in different service categories. WB-0032 therefore must use an explicit semantic allowlist instead of `GET == safe` logic.

### DirectAdmin layer

- DirectAdmin recommends new JSON `/api/...` endpoints first.
- The exact API supported by the target server should be discovered from that server's `/static/swagger.json`.
- Legacy API should be a fallback only when a required read capability is absent from the new API.
- A known documented legacy read is `CMD_API_SHOW_DOMAINS`.
- `da api-url` creates a temporary login key and is therefore excluded from this non-mutating discovery; only already-existing approved credentials may be used.

## Resulting Phase B strategy

1. public API reachability/capability metadata;
2. authenticated InterServer webhosting service identification;
3. DirectAdmin server API-shape discovery and domain identity;
4. minimal SSH/SFTP metadata inspection only if necessary to prove the staging document root;
5. record deployment-protocol, least-privilege identity, rollback, and effect-verifier capability without any remote write.

## Current evidence state

- InterServer documentation: reviewed.
- Phase B authority: granted.
- Live authenticated provider capability: `UNKNOWN_UNTIL_VERIFIED`.
- Exact staging target identity: `UNKNOWN_UNTIL_VERIFIED`.
- Exact staging document root: `UNKNOWN_UNTIL_VERIFIED`.
- Secret readiness: `UNKNOWN_UNTIL_VERIFIED`.
- Remote write performed: `false`.
- Secret values recorded: `false`.

No authenticated InterServer, DirectAdmin, SSH, or SFTP provider probe was performed as part of this documentation-preflight artifact.
