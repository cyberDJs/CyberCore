# WB-0035 A1 — InterServer VPS catalog + quote

Status: `PARTIAL — AUTHENTICATED CATALOG VERIFIED; LIVE QUOTE PENDING`

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

## API contract review

InterServer's current client API exposes the VPS flow as:

```text
GET  /apiv2/vps/order  -> ordering catalog
PUT  /apiv2/vps/order  -> validate configuration and quote; no service/invoice creation
POST /apiv2/vps/order  -> real order; service/invoice creation
```

Authentication uses `X-API-KEY`. The private InterServer MCP discovery independently describes `getNewVps` as the catalog operation, `putVps` as the dry-run quote operation, and `addVps` as the real-money order operation.

## A1 runtime execution history

### Attempt 1 — isolated ChatGPT execution runtime

No authenticated provider response was obtained. No mutation occurred.

### Attempt 2 — GitHub Actions before credential alias existed

The ephemeral runner failed closed because `INTERSERVER_API_KEY` was absent. No provider call or mutation occurred.

### Attempt 3 — GitHub Actions with credential alias

The secret alias was present, but the GitHub-hosted runner received:

```text
HTTP 403
```

No catalog/quote evidence was accepted from that runtime. The ephemeral workflow was removed after the safe stop.

### Attempt 4 — operator Mac, same API-key contract

The operator executed the authenticated catalog request locally using the `X-API-KEY` header:

```text
GET https://my.interserver.net/apiv2/vps/order
HTTP 200
```

Only non-secret catalog fields were retained for this evidence. The authenticated catalog reported:

```yaml
currency: USD
platform: kvm
platform_name: KVM
kvm_slice_price_field: vpsSliceKvmLCost
kvm_slice_price_usd_month: 3.00
vpsNyCost_observed: 1
ram_per_slice_mib: 2048
disk_per_slice_gib: 40
bandwidth_per_slice_gib: 2000
ubuntu24_template: ubuntu24
ubuntu24_template_label: "24.04"
locations:
  1:
    name: New Jersey
    kvm_stock: true
  2:
    name: Los Angeles
    kvm_stock: true
  3:
    name: Dallas, TX
    kvm_stock: true
```

This proves the authenticated catalog portion of A1 from the operator Mac. It does **not** yet prove the final `PUT` quote response.

## Parser correction discovered by live catalog

The original A1 parser incorrectly treated `vpsNyCost` as the KVM slice price. The live catalog demonstrates that the selected KVM platform's explicit per-slice price is:

```text
vpsSliceKvmLCost = 3
```

while:

```text
vpsNyCost = 1
```

is a distinct catalog field and must not be used as the selected KVM platform price.

CyberCore was corrected to:

- bind the KVM candidate to `vpsSliceKvmLCost`;
- reject non-positive or > USD 3.00 KVM slice pricing;
- require the exact `templates.kvm.ubuntu.ubuntu24` template;
- mirror the live 2 GiB / 40 GiB / 2000 GiB-per-slice catalog shape in the synthetic fixture;
- keep `vpsNyCost=1` in the fixture as a regression trap so it cannot silently become the KVM price again.

## Current candidate

Authenticated catalog evidence now supports:

```yaml
candidate:
  platform: kvm
  slices: 1
  os_distro: ubuntu
  os_version: ubuntu24
  control_panel: none
  location_id: 1
  location_name: New Jersey
  public_hostname: tasks.cyberdjs.org
  catalog_price_usd_month: 3.00
  ram_mib: 2048
  disk_gib: 40
  transfer_gib: 2000
```

Location `1` is currently selected deterministically because all three reported KVM stock and it is the lowest stable location id. This is not a statement that New Jersey is globally optimal; it is the deterministic current WB-0035 candidate.

## Existing-service guard before purchase

The private API/MCP contract also exposes a read-only VPS inventory operation (`GET /apiv2/vps` / `getVpsList`) that lists existing VPS services, their status, hostname, primary IP, plan and monthly cost.

Before any A2 purchase can be considered, CyberCore must inspect current VPS inventory and decide **reuse vs new provisioning**. The original A1 authorization names catalog + quote; this evidence does not claim that an inventory call has already been authorized or performed.

## Stop line

```yaml
A1_authorized: true
authenticated_catalog_verified: true
live_quote_verified: false
catalog_runtime: operator_mac
catalog_http_status: 200
catalog_kvm_price_usd_month: 3.00
order_performed: false
payment_performed: false
provider_mutation_performed: false
secret_values_recorded: false
A2_purchase_authorized: false
A2_payment_authorized: false
A3_bootstrap_deploy_authorized: false
A4_dns_authorized: false
```

Do not call `POST /apiv2/vps/order`, any invoice/payment operation, modify InterServer account security, rotate credentials, or perform any other InterServer mutation under this authorization.
