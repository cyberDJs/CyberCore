# WB-0032 Phase B — InterServer Read-Only Capability Discovery

Date: 2026-08-22
Status: authorized for read-only/non-mutating discovery; provider capability remains UNKNOWN until observed
Canonical base: `main@304f4234e4f52c2375d904b45d1ed0c4fe31511c`
Work block: `WB-0032 — InterServer Staging Capability Discovery`

## Authority

Jan Kočí explicitly authorized WB-0032 Phase B for **InterServer staging only** and **read-only/non-mutating capability discovery**.

Permitted probe classes:

- InterServer REST API read-only probes;
- InterServer MCP read-only discovery only after the exact exposed tool schema and read-only scope are inspected;
- DirectAdmin read-only API probes only after each exact endpoint passes the semantic mutability and response-sensitivity review defined below and is explicitly added to the allowlist;
- SSH/SFTP read-only inspection when needed to verify staging target identity or staging filesystem capability.

Explicitly prohibited:

- upload or file creation;
- overwrite or file modification;
- deletion;
- `chmod` / `chown`;
- symlink creation or replacement;
- provider configuration changes;
- credential creation, rotation, reset, or replacement;
- staging remote write / `staging_apply`;
- production access or production mutation, including production filesystem metadata inspection;
- secret-value persistence in GitHub, chat, Drive, Slack, CASER documents, or ordinary evidence.

Stop immediately if staging-vs-production identity is ambiguous or if the mutability or response sensitivity of a proposed probe is unclear.

## Documentation basis

The discovery procedure is based on the current provider and control-panel documentation reviewed on 2026-08-22:

- InterServer REST/OpenAPI documentation: `https://my.interserver.net/api-docs/`
- InterServer OpenAPI specification: `https://my.interserver.net/spec/openapi.yaml`
- InterServer MCP guide: `https://www.interserver.net/tips/kb/interserver-mcp-server-ai-hosting-automation/`
- InterServer private MCP endpoint: `https://my.interserver.net/mcp/private/client`
- DirectAdmin API documentation: `https://docs.directadmin.com/developer/api/`

The InterServer management API currently documents API version `0.9.0`, REST base path `/apiv2`, `X-API-KEY` authentication as the preferred API-key mode, and session authentication as an alternative. The InterServer MCP server also reports version `0.9.0` and supports a private authenticated endpoint with scoped access.

DirectAdmin documents a newer JSON `/api/...` API and a legacy `/CMD_API_...` API. New JSON endpoints should be preferred only after exact endpoint review. Each DirectAdmin server exposes the API shape it actually supports at `/static/swagger.json`.

## Critical safety observation

**HTTP method alone is not a safety boundary.**

InterServer documents multiple `GET` endpoints that can trigger side effects, such as service restart, backup creation, welcome-email resend, logout, or other actions. Therefore WB-0032 uses an explicit semantic allowlist and does **not** assume that every `GET` request is non-mutating.

Response sensitivity is a separate gate from mutability. A non-mutating endpoint remains blocked when its response may expose credential, session, private account, or unrelated production material and the response surface cannot be bounded before invocation.

Any endpoint not explicitly allowed below is blocked until separately reviewed and added to this document.

## Discovery sequence

### Step 0 — credential handling

Use an already-existing credential from an approved runtime secret source.

Allowed evidence:

- credential alias/reference;
- authentication mechanism name;
- readiness status;
- safe fingerprint/hash where appropriate.

Blocked:

- displaying or logging API keys, passwords, private keys, session cookies, bearer tokens, login URLs containing credentials, TOTP seeds, recovery codes, or other secret values;
- creating or rotating a credential to make discovery work.

If no already-approved credential is available, record `credential_readiness: BLOCKED` and stop authenticated discovery.

### Step 1 — public InterServer API availability

Allowed operations:

- `GET /apiv2/ping`
- `GET /apiv2/info`

Purpose:

- prove that the documented API surface is reachable;
- confirm that the webhosting module/API category exists;
- capture only non-account-specific capability metadata.

No authentication is required for these probes according to the current API documentation.

### Step 2 — identify candidate owned webhosting service

Initial allowed authenticated operation:

- `GET /apiv2/websites`

Purpose:

- enumerate only the caller's webhosting services;
- identify candidate InterServer webhosting service IDs;
- record only the minimum non-secret service status, hostname/IP/control-panel metadata required to select the intended staging service;
- avoid unrelated account, billing, mail, domain-registration, VPS, server, or other service records.

The current InterServer documentation describes `GET /apiv2/websites/{id}` as returning **full configuration and status detail**. Because that response surface has not yet been proven free of credential, session, auto-login, or other secret-like material, the detail endpoint is **not** part of the initial allowlist.

`GET /apiv2/websites/{id}` may be added later only after an independent schema/response-surface review proves that the required fields can be read without exposing secret/session material. If that cannot be proven, record the detail capability as `BLOCKED` and continue with safer provider/DirectAdmin/staging-only SSH metadata sources where possible.

### Step 3 — optional network identity read

Allowed only after Step 2 identifies an unambiguous candidate staging service ID:

- `GET /apiv2/websites/{id}/reverse_dns`

Purpose:

- corroborate service IP/host identity without changing DNS.

### Explicit InterServer API denylist for this work block

Do not call:

- any `POST`, `PATCH`, `PUT`, or `DELETE` endpoint;
- `/account/apikey`;
- `/account/password`;
- `/account/sshkey`;
- `/websites/{id}` until its full response surface is independently proven safe for this work block;
- `/websites/{id}/welcome_email`;
- `/websites/{id}/login` because it creates a one-time authenticated control-panel login capability;
- `/websites/{id}/migration`;
- `/websites/{id}/buy_ip` unless separately reviewed for an exact read-only need;
- `/websites/{id}/backups` unless separately reviewed for metadata-only listing with download disabled;
- any VPS/QuickServer power, backup, restore, password, reinstall, quota, CD, VNC, or lifecycle endpoint;
- any DNS/domain/provider mutation endpoint.

### Step 4 — DirectAdmin capability discovery

Use DirectAdmin only after Step 2 has identified the intended InterServer webhosting service and the target control-panel identity is unambiguous.

Initial DirectAdmin allowlist:

- `GET /static/swagger.json` on the exact target DirectAdmin server, solely to discover the API shape exposed by that server.

No other DirectAdmin endpoint is initially authorized merely because it is present in Swagger, uses `GET`, or appears in provider documentation.

For every additional DirectAdmin operation required by Phase B:

1. identify the exact method and path from the target server's `/static/swagger.json` or, only if necessary, the documented legacy API;
2. review that exact operation for side effects/mutability;
3. review its documented response fields for credential, session, personal, production, or unrelated account data;
4. define the minimum fields that may enter sanitized evidence;
5. add the exact method/path to this semantic allowlist before invoking it;
6. if either mutability or response sensitivity remains ambiguous, record the capability `BLOCKED` or `UNKNOWN` and do not call it.

A documented legacy candidate such as `CMD_API_SHOW_DOMAINS` is **not automatically allowed**. It may be used only after the same per-endpoint review and explicit allowlist addition. Legacy `/CMD_API_...` endpoints remain fallback-only when the required read capability is absent from the reviewed new `/api/...` surface.

Do **not** generate a temporary DirectAdmin login key with `da api-url` during WB-0032 Phase B; generating a new access credential is outside the authorized non-mutating discovery scope.

Do not use undocumented GUI-debug endpoints. If a required capability is absent from the server's Swagger specification and documented legacy API, record it as unavailable/unknown rather than inventing an endpoint.

### Step 5 — staging filesystem identity

If InterServer and already-allowed DirectAdmin metadata cannot prove the staging document root, perform the minimum SSH/SFTP read-only inspection needed on the **staging scope only**.

Permitted SSH command classes, scoped only to staging identity/path discovery:

- identity/current-directory inspection, e.g. `id`, `pwd`;
- staging filesystem metadata inspection, e.g. `stat` on an already identified staging candidate path;
- staging path resolution without mutation, e.g. `readlink` on an already identified staging candidate path;
- existence/type tests on staging paths that do not create files;
- narrowly scoped staging directory-name listing when necessary.

Blocked remote command classes:

- file writes/redirection;
- `touch`, `mkdir`, `mv`, `cp`, `rm`;
- `chmod`, `chown`;
- `ln`;
- package/service/configuration operations;
- database writes;
- any shell command whose side effects are not understood;
- `stat`, `readlink`, listing, traversal, content read, or any other inspection of a production path.

The goal is to prove a concrete non-production staging path. Production exclusion must be established only by comparing the observed staging identity/path against **previously approved canonical production-path evidence** that already exists outside this Phase B probe. Phase B must not inspect production to manufacture that evidence.

If sufficiently authoritative pre-existing production-path evidence is unavailable, stale, or ambiguous, set `production_overlap_excluded: blocked` and stop the relevant exit criterion. Do not access production. Resolving that gap would require a separate production-read scope and explicit authorization.

### Step 6 — deployment capability without deployment

Evidence only:

- SSH available: `true|false|unknown`;
- SFTP available: `true|false|unknown`;
- rsync executable/usable in the staging account context: `true|false|unknown`;
- DirectAdmin file/API capability relevant to future staging deployment: `true|false|unknown`;
- least-privilege deploy identity scope: `verified|blocked|unknown`.

No upload or synthetic write test is allowed in WB-0032.

### Step 7 — rollback and effect-verifier capability

Determine without mutation whether the **staging environment** can support a later safe deployment design.

Record:

- immutable release directories feasible: `true|false|unknown`;
- atomic/current-symlink model feasible: `true|false|unknown`;
- backup-before-overwrite capability: `true|false|unknown`;
- no-overwrite new-path release feasible: `true|false|unknown`;
- staging health URL or equivalent verifier: `verified|blocked|unknown`;
- version/commit marker verification strategy: `verified|blocked|unknown`;
- production non-change verification strategy: `verified|blocked|unknown`, but only when it can rely on previously approved evidence or external non-production observations without production access.

Do not create a symlink, backup, release directory, marker file, or health endpoint during discovery. Do not inspect production to construct or test the production non-change verifier during WB-0032.

## Evidence schema

Each discovery receipt must record at minimum:

```yaml
work_block: WB-0032
phase: B
provider: InterServer
target_scope: staging_only
authorization:
  issuer: Jan Kočí
  granted_at: 2026-08-22T04:41:00+02:00
  mode: read_only_non_mutating
credential:
  alias: <safe-reference-or-unknown>
  readiness: <verified|blocked|unknown>
provider_api:
  rest_version: <observed-or-unknown>
  mcp_version: <observed-or-unknown>
webhosting_service:
  id: <safe-id-or-unknown>
  status: <observed-or-unknown>
  host: <sanitized-observed-or-unknown>
staging:
  domain: <observed-or-unknown>
  document_root: <observed-or-unknown>
  production_overlap_excluded: <verified|blocked|unknown>
capabilities:
  ssh: <true|false|unknown>
  sftp: <true|false|unknown>
  rsync: <true|false|unknown>
  directadmin_api: <true|false|unknown>
rollback: <verified|blocked|unknown>
effect_verifier: <verified|blocked|unknown>
credential_rotation_state: <verified|unknown>
remote_write_performed: false
secret_values_recorded: false
```

Raw API/provider responses must be sanitized before entering ordinary evidence if they contain personal, billing, credential, session, or unrelated account data. If a response surface cannot be safely bounded before invocation, that endpoint remains blocked rather than relying on post-hoc redaction.

## Stop conditions

Return `BLOCKED` immediately when any of the following occurs:

- the service cannot be tied unambiguously to InterServer staging;
- staging path may equal or overlap a production document root and this cannot be excluded from pre-existing approved production-path evidence;
- proving production exclusion would require new production access;
- the only available authentication path requires creating/rotating/resetting a credential;
- a proposed endpoint has undocumented or ambiguous side effects;
- a proposed endpoint may return secret/session material and its response surface cannot be bounded before invocation;
- an API response exposes secret material that cannot be safely redacted before evidence capture;
- required capability can only be verified by performing a remote write;
- provider behavior conflicts with the reviewed documentation.

## Exit criteria

Phase B reaches `VERIFIED` only after safe evidence establishes:

1. exact non-production staging service identity;
2. exact non-production staging path/document-root identity and production exclusion using pre-existing approved production-path evidence, without new production access;
3. actual deployment protocol capabilities;
4. least-privilege credential/identity readiness without disclosure;
5. rollback capability;
6. effect-verifier capability;
7. credential-rotation operational state without rotation;
8. `remote_write_performed: false`;
9. `secret_values_recorded: false`.

A Phase B `VERIFIED` result still grants **no authority for staging write**. Any future `staging_apply` or equivalent remote mutation requires a new work block/procedure and fresh explicit Jan Kočí remote-write authorization.
