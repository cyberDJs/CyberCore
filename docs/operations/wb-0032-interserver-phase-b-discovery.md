# WB-0032 Phase B — InterServer Read-Only Capability Discovery

Date: 2026-08-22
Status: authorized for read-only/non-mutating discovery; provider capability remains UNKNOWN until observed
Canonical base: `main@304f4234e4f52c2375d904b45d1ed0c4fe31511c`
Work block: `WB-0032 — InterServer Staging Capability Discovery`

## Authority

Jan Kočí explicitly authorized WB-0032 Phase B for **InterServer staging only** and **read-only/non-mutating capability discovery**.

Permitted probe classes:

- InterServer REST API read-only probes;
- InterServer MCP read-only discovery when a compatible authenticated client is available;
- DirectAdmin read-only API probes;
- SSH/SFTP read-only inspection when needed to verify target identity or filesystem capability.

Explicitly prohibited:

- upload or file creation;
- overwrite or file modification;
- deletion;
- `chmod` / `chown`;
- symlink creation or replacement;
- provider configuration changes;
- credential creation, rotation, reset, or replacement;
- staging remote write / `staging_apply`;
- production access or production mutation;
- secret-value persistence in GitHub, chat, Drive, Slack, CASER documents, or ordinary evidence.

Stop immediately if staging-vs-production identity is ambiguous or if the mutability of a proposed probe is unclear.

## Documentation basis

The discovery procedure is based on the current provider and control-panel documentation reviewed on 2026-08-22:

- InterServer REST/OpenAPI documentation: `https://my.interserver.net/api-docs/`
- InterServer OpenAPI specification: `https://my.interserver.net/spec/openapi.yaml`
- InterServer MCP guide: `https://www.interserver.net/tips/kb/interserver-mcp-server-ai-hosting-automation/`
- InterServer private MCP endpoint: `https://my.interserver.net/mcp/private/client`
- DirectAdmin API documentation: `https://docs.directadmin.com/developer/api/`

The InterServer management API currently documents API version `0.9.0`, REST base path `/apiv2`, `X-API-KEY` authentication as the preferred API-key mode, and session authentication as an alternative. The InterServer MCP server also reports version `0.9.0` and supports a private authenticated endpoint with scoped access.

DirectAdmin documents a newer JSON `/api/...` API and a legacy `/CMD_API_...` API. New JSON endpoints should be preferred. Each DirectAdmin server exposes the API shape it actually supports at `/static/swagger.json`.

## Critical safety observation

**HTTP method alone is not a safety boundary.**

InterServer documents multiple `GET` endpoints that can trigger side effects, such as service restart, backup creation, welcome-email resend, logout, or other actions. Therefore WB-0032 uses an explicit semantic allowlist and does **not** assume that every `GET` request is non-mutating.

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

### Step 2 — identify the owned webhosting service

Allowed authenticated operations:

- `GET /apiv2/websites`
- `GET /apiv2/websites/{id}`

Purpose:

- identify the exact InterServer webhosting service ID;
- record service status;
- record provider hostname/IP/control-panel metadata only where non-secret;
- identify the hosting username only if it is required for target verification and safe to retain;
- establish which service corresponds to the intended staging scope.

Do not query unrelated account, billing, mail, domain-registration, VPS, server, or other service records unless a later discovery question requires them.

### Step 3 — optional network identity read

Allowed only if needed:

- `GET /apiv2/websites/{id}/reverse_dns`

Purpose:

- corroborate service IP/host identity without changing DNS.

### Explicit InterServer API denylist for this work block

Do not call:

- any `POST`, `PATCH`, `PUT`, or `DELETE` endpoint;
- `/account/apikey`;
- `/account/password`;
- `/account/sshkey`;
- `/websites/{id}/welcome_email`;
- `/websites/{id}/login` because it creates a one-time authenticated control-panel login capability;
- `/websites/{id}/migration`;
- `/websites/{id}/buy_ip` unless separately reviewed for an exact read-only need;
- `/websites/{id}/backups` unless separately reviewed for metadata-only listing with download disabled;
- any VPS/QuickServer power, backup, restore, password, reinstall, quota, CD, VNC, or lifecycle endpoint;
- any DNS/domain/provider mutation endpoint.

### Step 4 — DirectAdmin capability discovery

Use DirectAdmin only after Step 2 has identified the intended InterServer webhosting service and the target control-panel identity is unambiguous.

Preferred approach:

1. use an existing DirectAdmin credential or already-approved credential alias;
2. read `/static/swagger.json` from the exact DirectAdmin server to discover the API actually supported there;
3. prefer documented `/api/...` JSON endpoints;
4. use legacy `/CMD_API_...` endpoints only where the required read operation is missing from the new API.

Known legacy read fallback:

- `CMD_API_SHOW_DOMAINS` — list domains owned by the current DirectAdmin user.

Do **not** generate a temporary DirectAdmin login key with `da api-url` during WB-0032 Phase B; generating a new access credential is outside the authorized non-mutating discovery scope.

Do not use undocumented GUI-debug endpoints for production automation. If a required capability is absent from the server's Swagger specification and legacy documented API, record it as unavailable/unknown rather than inventing an endpoint.

### Step 5 — staging filesystem identity

If InterServer and DirectAdmin metadata cannot prove the staging document root, perform the minimum SSH/SFTP read-only inspection needed to answer it.

Permitted SSH command classes:

- identity/current-directory inspection, e.g. `id`, `pwd`;
- filesystem metadata inspection, e.g. `stat`;
- path resolution without mutation, e.g. `readlink`;
- existence/type tests that do not create files;
- narrowly scoped directory-name listing when necessary.

Blocked remote command classes:

- file writes/redirection;
- `touch`, `mkdir`, `mv`, `cp`, `rm`;
- `chmod`, `chown`;
- `ln`;
- package/service/configuration operations;
- database writes;
- any shell command whose side effects are not understood.

The goal is to prove a concrete non-production staging path and independently establish that it does not overlap the production document root.

### Step 6 — deployment capability without deployment

Evidence only:

- SSH available: `true|false|unknown`;
- SFTP available: `true|false|unknown`;
- rsync executable/usable in the account context: `true|false|unknown`;
- DirectAdmin file/API capability relevant to future deployment: `true|false|unknown`;
- least-privilege deploy identity scope: `verified|blocked|unknown`.

No upload or synthetic write test is allowed in WB-0032.

### Step 7 — rollback and effect-verifier capability

Determine without mutation whether the hosting environment can support a later safe deployment design.

Record:

- immutable release directories feasible: `true|false|unknown`;
- atomic/current-symlink model feasible: `true|false|unknown`;
- backup-before-overwrite capability: `true|false|unknown`;
- no-overwrite new-path release feasible: `true|false|unknown`;
- staging health URL or equivalent verifier: `verified|blocked|unknown`;
- version/commit marker verification strategy: `verified|blocked|unknown`;
- production non-change verification strategy: `verified|blocked|unknown`.

Do not create a symlink, backup, release directory, marker file, or health endpoint during discovery.

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

Raw API/provider responses must be sanitized before entering ordinary evidence if they contain personal, billing, credential, session, or unrelated account data.

## Stop conditions

Return `BLOCKED` immediately when any of the following occurs:

- the service cannot be tied unambiguously to InterServer staging;
- staging path may equal or overlap a production document root;
- the only available authentication path requires creating/rotating/resetting a credential;
- a proposed endpoint has undocumented or ambiguous side effects;
- an API response exposes secret material that cannot be safely redacted before evidence capture;
- required capability can only be verified by performing a remote write;
- provider behavior conflicts with the reviewed documentation.

## Exit criteria

Phase B reaches `VERIFIED` only after safe evidence establishes:

1. exact non-production staging service identity;
2. exact non-production staging path/document-root identity and production exclusion;
3. actual deployment protocol capabilities;
4. least-privilege credential/identity readiness without disclosure;
5. rollback capability;
6. effect-verifier capability;
7. credential-rotation operational state without rotation;
8. `remote_write_performed: false`;
9. `secret_values_recorded: false`.

A Phase B `VERIFIED` result still grants **no authority for staging write**. Any future `staging_apply` or equivalent remote mutation requires a new work block/procedure and fresh explicit Jan Kočí remote-write authorization.
