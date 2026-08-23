# WB-0035 A1 — InterServer VPS catalog + quote

Status: `PARTIAL — PUBLIC CATALOG VERIFIED; AUTHENTICATED A1 BLOCKED BY PROVIDER HTTP 403`

Date: 2026-08-23
Work block: `WB-0035 — InterServer VPS + Vikunja ADHD Time-Management MVP`
Provider: InterServer
Target hostname candidate: `tasks.cyberdjs.org`

## Operator authorization

Issuer: Jan Kočí
Granted at: 2026-08-23T12:08:00+02:00

Explicit authorization text:

> Schvaluju A1: InterServer VPS catalog + quote pro WB-0035, maximálně $3/měsíc, pouze zjištění nabídky a ceny. Bez objednávky, platby nebo jiné změny na InterServeru.

Authorized scope:

- current InterServer VPS catalog and availability/pricing discovery;
- a semantically non-mutating VPS configuration validation/quote;
- recurring-price ceiling: USD 3.00/month;
- no VPS order;
- no invoice/payment action;
- no provider configuration change;
- no DNS, SSH, credential, host, application, mail, shared-hosting, Nextcloud or unrelated-resource mutation;
- no plaintext secrets in repository/chat/ordinary evidence.

A2 purchase/payment, A3 bootstrap/deploy, and A4 DNS remain **not granted**.

## Public provider catalog observation

Official InterServer public VPS pages were checked on 2026-08-23 before attempting authenticated A1 execution.

Current public Linux/KVM starting point observed from InterServer:

```yaml
platform: KVM
slices: 1
price_usd_month: 3.00
cpu_cores: 1
ram_mib: 2048
ssd_gib: 40
transfer_tb: 2
root_access: true
```

The official Ubuntu Cloud Compute page also currently advertises the same one-slice starting point at USD 3.00/month with 1 core, 2 GB RAM, 40 GB SSD and 2 TB transfer.

Provider references:

- `https://www.interserver.net/vps/`
- `https://www.interserver.net/vps/cheap-vps.html`
- `https://www.interserver.net/vps/ubuntu-vps.html`

These public pages are useful catalog evidence but are **not** treated as an account-scoped purchase quote or stock proof.

## API contract review

Current official InterServer REST documentation describes:

```text
GET /apiv2/vps/order
```

as the authenticated VPS ordering catalog, including virtualization platforms, OS templates, location stock, per-slice resources/pricing and billing currency.

It describes:

```text
PUT /apiv2/vps/order
```

as validation/quote without invoice or service creation. The current documentation example accepts a candidate equivalent to:

```yaml
vpsPlatform: kvm
osDistro: ubuntu
osVersion: ubuntu24
slices: 1
controlpanel: none
period: 1
location: 1
```

and shows a USD 3.00 one-slice validation result. That example confirms API semantics and expected shape only; it is **not** accepted as the live account quote required by WB-0035.

Authentication is documented as API key in the `X-API-KEY` header. The provider documentation generally describes missing/invalid authentication on authenticated API operations as `401 Unauthorized`.

The same documentation also describes account-wide Web/API IP restrictions. Once an IP allow-list exists, `/apiv2` access can be restricted by source IP. This is a plausible explanation for an HTTP 403 from a GitHub-hosted runner, but it is **not proven** by the current A1 evidence.

Provider API reference:

- `https://my.interserver.net/api-docs/redoc.html`

## A1 runtime execution history

### Attempt 1 — isolated ChatGPT execution runtime

A safe provider request could not be completed because that isolated runtime did not have usable provider network/credential access.

```yaml
provider_response_observed: false
authenticated_provider_call_performed: false
order_performed: false
payment_performed: false
provider_mutation_performed: false
secret_values_recorded: false
```

### Attempt 2 — GitHub Actions before credential alias existed

The ephemeral A1 runner failed closed because `INTERSERVER_API_KEY` was not configured.

```yaml
credential_alias_available: false
authenticated_provider_call_performed: false
order_performed: false
payment_performed: false
provider_mutation_performed: false
secret_values_recorded: false
```

### Attempt 3 — GitHub Actions after operator configured the secret alias

Exact A1 diagnostic head:

```text
60462829e8f7531ab9cc5edd33e6f279d60c458f
```

The runtime confirmed that the credential alias was present, then the bounded A1 provider probe stopped on:

```text
InterServer returned HTTP 403
```

No sanitized live catalog or quote was produced, therefore A1 remains unverified.

Safety receipt:

```yaml
credential_alias_available: true
provider_response_observed: true
provider_http_status: 403
authenticated_catalog_verified: false
live_quote_verified: false
order_performed: false
payment_performed: false
provider_mutation_performed: false
secret_values_recorded: false
```

The ephemeral GitHub Actions runner was removed after the safe stop so the repository's normal fixed workflow set remains unchanged.

## Interpretation

The `INTERSERVER_API_KEY` secret is now reaching the A1 runtime. The current blocker is provider access, not a missing GitHub secret.

Because the documented authenticated endpoints normally use `401` for missing/invalid authentication while InterServer also supports source-IP restrictions, HTTP 403 is **consistent with** an account/provider access-policy or upstream protection decision. The current evidence does not prove whether the exact cause is:

- an InterServer account IP allow-list;
- another provider security policy / WAF gate affecting GitHub-hosted runners;
- a credential/account policy not described by the endpoint schema;
- another provider-side authorization condition.

Do not bypass provider security controls by adding undocumented headers or changing InterServer account security under A1. Any IP allow-list change, API-key rotation, or other account-security mutation requires separate explicit authorization.

## Current candidate

Public catalog evidence still supports:

```yaml
candidate:
  platform: kvm
  slices: 1
  os_distro: ubuntu
  os_version_candidate: ubuntu24
  control_panel: none
  public_hostname_candidate: tasks.cyberdjs.org
  public_price_evidence_usd_month: 3.00
  public_resources:
    cpu_cores: 1
    ram_mib: 2048
    disk_gib: 40
    transfer_tb: 2
```

This is **not** yet an account-scoped live quote and must not be used as A2 purchase evidence.

## Stop line

```yaml
A1_authorized: true
public_catalog_verified: true
credential_alias_available: true
authenticated_catalog_verified: false
live_quote_verified: false
latest_provider_result: HTTP_403
A2_purchase_authorized: false
A2_payment_authorized: false
A3_bootstrap_deploy_authorized: false
A4_dns_authorized: false
```

Do not call `POST /apiv2/vps/order`, any invoice/payment operation, modify InterServer account security, rotate credentials, or perform any other InterServer mutation under this authorization.
