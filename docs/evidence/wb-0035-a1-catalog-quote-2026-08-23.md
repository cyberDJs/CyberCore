# WB-0035 A1 — InterServer VPS catalog + quote

Status: `VERIFIED — AUTHENTICATED CATALOG + NON-MUTATING LIVE QUOTE PASSED`

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

InterServer's reviewed VPS flow is:

```text
GET  /apiv2/vps/order  -> ordering catalog
PUT  /apiv2/vps/order  -> validate configuration and quote; no service/invoice creation
POST /apiv2/vps/order  -> real order; service/invoice creation
```

Authentication uses `X-API-KEY`.

## A1 runtime execution history

### Attempt 1 — isolated ChatGPT execution runtime

No authenticated provider response was obtained. No mutation occurred.

### Attempt 2 — GitHub Actions before credential alias existed

The ephemeral runner failed closed because `INTERSERVER_API_KEY` was absent. No provider call or mutation occurred.

### Attempt 3 — GitHub Actions with credential alias

The secret alias was present, but the GitHub-hosted runner received `HTTP 403`. No catalog/quote evidence was accepted from that runtime. The ephemeral workflow was removed after the safe stop.

### Attempt 4 — operator Mac, authenticated catalog

The operator executed the authenticated catalog request locally using `X-API-KEY`:

```text
GET https://my.interserver.net/apiv2/vps/order
HTTP 200
```

Sanitized catalog evidence:

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

This verified the authenticated catalog portion of A1.

### Attempt 5 — operator Mac, quote validation with non-compliant ephemeral password

The authorized `PUT /apiv2/vps/order` validation endpoint returned `HTTP 200` and USD 3.00 pricing, but `continue=false` because the generated ephemeral root password did not satisfy the provider password policy.

That run established the live response mapping `os=ubuntu24` and `version=ubuntu`, and prompted a fail-closed password-generator correction. No order, invoice, payment or provider mutation occurred.

### Attempt 6 — operator Mac, policy-compliant non-mutating quote

Observed at approximately 2026-08-23 21:23 CEST, the operator repeated the already-authorized quote with a policy-compliant ephemeral password.

Transport result:

```text
HTTP=200
```

Sanitized provider response:

```yaml
continue: true
errors: []
service_cost: 3
original_cost: 3
slice_cost: 3
repeat_slice_cost: 3
repeat_service_cost: 3
monthly_service_cost: 3
os: ubuntu24
version: ubuntu
slices: "1"
platform: kvm
controlpanel: none
period: 1
location: 1
hostname: tasks.cyberdjs.org
```

Interpretation:

- configuration validation passed with `continue=true` and no errors;
- recurring price is USD 3.00/month, exactly at the A1 ceiling;
- initial `service_cost` is USD 3.00 and equals the monthly service cost, therefore the modeled unexpected one-time surcharge is USD 0.00;
- exact intended KVM / 1 slice / Ubuntu 24 / no panel / one month / location 1 / hostname configuration was returned;
- no order, invoice, payment, DNS, SSH, application or account-security mutation occurred;
- no plaintext API key or ephemeral root password was retained in ordinary evidence.

## Parser corrections discovered by live provider behavior

CyberCore now:

- uses `vpsSliceKvmLCost` rather than `vpsNyCost` for KVM price;
- requires exact `templates.kvm.ubuntu.ubuntu24` availability;
- validates the live quote mapping `os=ubuntu24` and `version=ubuntu`;
- generates a quote-only ephemeral root password with lowercase, uppercase, digit and provider-compatible special characters;
- never stores the ephemeral password in ordinary evidence.

## Verified A1 candidate

```yaml
candidate:
  provider: InterServer
  platform: kvm
  slices: 1
  os_distro: ubuntu
  os_version: ubuntu24
  control_panel: none
  period_months: 1
  location_id: 1
  location_name: New Jersey
  public_hostname: tasks.cyberdjs.org
  catalog_price_usd_month: 3.00
  quote_price_usd_month: 3.00
  quote_service_cost_usd: 3.00
  modeled_one_time_surcharge_usd: 0.00
  ram_mib: 2048
  disk_gib: 40
  transfer_gib: 2000
  quantity: 1
```

Location `1` is selected deterministically because all three observed locations reported KVM stock and location 1 is the lowest stable id. This is not a claim that New Jersey is globally optimal.

## Existing-service guard before purchase

InterServer also exposes read-only current VPS inventory through `GET /apiv2/vps` / `getVpsList`.

Before any A2 purchase decision, CyberCore must inspect current VPS inventory and decide **reuse vs new provisioning**. The existing A1 authorization names catalog + quote only, so this evidence does not claim that the inventory call has been authorized or performed.

## A1 completion receipt

```yaml
A1_authorized: true
authenticated_catalog_verified: true
live_quote_verified: true
quote_http_status: 200
quote_continue: true
quote_errors_empty: true
recurring_price_usd_month: 3.00
service_cost_usd: 3.00
modeled_one_time_surcharge_usd: 0.00
platform: kvm
slices: 1
os: ubuntu24
version: ubuntu
controlpanel: none
period: 1
location: 1
hostname: tasks.cyberdjs.org
order_performed: false
payment_performed: false
provider_mutation_performed: false
secret_values_recorded: false
A2_purchase_authorized: false
A2_payment_authorized: false
A3_bootstrap_deploy_authorized: false
A4_dns_authorized: false
```

## Stop line

**A1 is VERIFIED and complete. Stop provider activity here.**

Do not call `POST /apiv2/vps/order`, any invoice/payment operation, `GET /apiv2/vps` inventory, modify InterServer account security, rotate credentials, bootstrap/deploy, or change DNS without the next explicit authorization applicable to that operation.
