# WB-0035 A1 — InterServer VPS catalog + quote

Status: `PARTIAL — PUBLIC CATALOG VERIFIED; AUTHENTICATED QUOTE BLOCKED BY CURRENT RUNTIME ACCESS`

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

The current official InterServer REST documentation describes:

```text
GET /apiv2/vps/order
```

as the authenticated VPS ordering catalog, including virtualization platforms, OS templates, location stock, per-slice resources/pricing and billing currency.

It describes:

```text
PUT /apiv2/vps/order
```

as a pure validation/quote operation with no invoice or service creation. The documentation's current example accepts a candidate equivalent to:

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

Provider API reference:

- `https://my.interserver.net/api-docs/redoc.html`

## A1 runtime execution result

A safe `GET https://my.interserver.net/apiv2/vps/order` was attempted from the currently available isolated execution runtime.

Result:

```yaml
runtime_network_result: DNS_RESOLUTION_FAILED
provider_response_observed: false
authenticated_provider_call_performed: false
order_performed: false
payment_performed: false
provider_mutation_performed: false
secret_values_recorded: false
```

The current ChatGPT tool environment also exposes no connected InterServer account connector and no approved InterServer credential is present in the available runtime environment. No old/revoked credential was reused and no credential was requested into chat.

Therefore the account-scoped `GET /apiv2/vps/order` catalog and `PUT /apiv2/vps/order` quote were **not** executed from this runtime.

## Current decision

Public catalog evidence supports the planned 1-slice KVM candidate and the USD 3.00/month ceiling:

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

However A1 does **not** reach `VERIFIED` until an approved CyberCore runtime with an existing secret reference performs the authenticated catalog read and pure quote validation, captures location stock/OS-template availability, and produces a sanitized quote receipt.

No A2 purchase approval packet may be treated as valid until that happens.

## Stop line

Current stop state:

```yaml
A1_authorized: true
public_catalog_verified: true
authenticated_catalog_verified: false
live_quote_verified: false
A2_purchase_authorized: false
A2_payment_authorized: false
A3_bootstrap_deploy_authorized: false
A4_dns_authorized: false
```

Do not call `POST /apiv2/vps/order`, any invoice/payment operation, or any other InterServer mutation under this authorization.
