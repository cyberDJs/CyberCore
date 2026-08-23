# WB-0035 — InterServer VPS + Vikunja ADHD Time-Management MVP

## Status

`ACTIVE — A1 VERIFIED; PRE-A2 VERIFIED; A2 AUTHORIZED / PAYPAL ONLY DISCOVERED / EXPLICIT METHOD SELECTION PENDING; A3/A4 NOT AUTHORIZED`

Date: 2026-08-23
Canonical base: `main@2bea07db4e0a5d2a062c96ef1642a6f2a0927f0a`
Predecessor/parallel work: `WB-0034 — First Staging Deployment Preflight`
Provider: InterServer
Target workload: Vikunja-based attention-friendly task management MVP
Budget ceiling: USD 3.00/month unless separately approved

## Goal

Prepare a fail-closed path for CyberCore to discover the current InterServer VPS catalog, produce a non-mutating live quote, inspect existing VPS inventory, execute an explicitly authorized bounded purchase/payment, and only later—under separate authority gates—harden the resulting VPS, deploy Vikunja, publish DNS, and verify persistence/backup/restore.

A1 catalog + quote is verified. PRE-A2 existing-VPS inventory is verified and complete: one provider VPS record exists, it is `expired`, and there are zero active VPS services available for immediate reuse. A2 explicitly authorizes purchase/payment of exactly one new VPS matching the verified candidate. Payment-method discovery is complete and the only currently exposed reviewed method is `paypal`; the operator has not yet explicitly selected it. No order has been placed. A3 bootstrap/deploy and A4 DNS remain not granted.

## Client direction

CyberFlow is **iPhone-first**. Responsive web/PWA is the fallback; macOS may follow; Android is explicitly out of MVP scope.

See `docs/product/cyberflow-iphone-first-client.md`.

## Proposed MVP topology

```text
User / browser
      |
    HTTPS
      |
  Caddy reverse proxy
      |
    Vikunja
      |
    SQLite
```

Persistent host data:

```text
/srv/vikunja/files
/srv/vikunja/db
/srv/vikunja/backups
```

Planned baseline: Ubuntu 24.04 LTS, KVM, one slice, no control panel, Docker Engine + Compose, Caddy, Vikunja + SQLite, hostname candidate `tasks.cyberdjs.org`.

## InterServer API basis

Reviewed provider flow:

```text
GET  /apiv2/vps                         -> existing VPS inventory
GET  /apiv2/vps/order                   -> current catalog / stock / pricing inputs
PUT  /apiv2/vps/order                   -> validate configuration and calculate quote
POST /apiv2/vps/order                   -> create VPS order + invoice/service state
GET  /apiv2/billing/cart                -> read checkout state / available payment methods
GET  /apiv2/billing/invoices/{id}       -> read invoice detail
GET  /apiv2/vps/{id}/invoices           -> read per-VPS invoice history
POST /apiv2/billing/pay/{method}/{invoices} -> initiate payment for named invoice(s)
GET  /apiv2/vps/{id}                    -> read service state after ordering
```

HTTP method alone is not treated as a safety boundary. Authority is bound to exact reviewed operations and semantics.

## Authority model

### A0 — repository planning

`AUTHORIZED_BY_CURRENT_WORK`

Documentation, schemas, tests, synthetic fixtures and validators are allowed. Provider contact, billing inspection, purchase/payment, DNS, SSH, credential mutation and deployment are not allowed by A0 alone.

### A1 — live VPS catalog + quote

`VERIFIED — COMPLETE`

Operator authorization:

> Schvaluju A1: InterServer VPS catalog + quote pro WB-0035, maximálně $3/měsíc, pouze zjištění nabídky a ceny. Bez objednávky, platby nebo jiné změny na InterServeru.

Verified live result:

```yaml
provider: InterServer
catalog_http_status: 200
quote_http_status: 200
quote_continue: true
quote_errors: []
platform: kvm
slices: 1
os: ubuntu24
version: ubuntu
controlpanel: none
period: 1
location: 1
location_name: New Jersey
hostname: tasks.cyberdjs.org
currency: USD
catalog_price_usd_month: 3.00
service_cost_usd: 3.00
monthly_service_cost_usd: 3.00
modeled_one_time_surcharge_usd: 0.00
ram_mib: 2048
disk_gib: 40
transfer_gib: 2000
order_performed: false
payment_performed: false
provider_mutation_performed: false
secret_values_recorded: false
```

The authenticated catalog showed KVM stock in New Jersey, Los Angeles and Dallas and the exact Ubuntu 24 template. `vpsSliceKvmLCost=3` is the KVM slice price; `vpsNyCost=1` is a distinct field and is not used as KVM price.

Evidence: `docs/evidence/wb-0035-a1-catalog-quote-2026-08-23.md`.

### PRE-A2 — existing VPS inventory / reuse decision

`VERIFIED — COMPLETE; ONE EXPIRED VPS FOUND; NEW PROVISIONING RECOMMENDED`

Operator authorization granted on 2026-08-23 at 21:39 CEST:

> Schvaluju PRE-A2: read-only inventuru existujících InterServer VPS přes GET /apiv2/vps pro WB-0035. Bez jakékoli změny, restartu, resize, reinstallu, zrušení, objednávky nebo platby.

Sanitized verified result:

```yaml
existing_vps_count: 1
active_vps_count: 0
expired_vps_count: 1
vps:
  - vps_id: "3447580"
    vps_name: "KVM540"
    vps_hostname: "vps3447580"
    vps_ip: "162.35.163.231"
    vps_status: "expired"
    services_name: "KVM Linux VPS Slice"
    repeat_invoices_cost: "3.00"
raw_temp_removed: true
```

Decision: **new provisioning**. No active VPS exists that can be reused as-is, and a new VPS would not duplicate an active service. No SSH/application inspection was performed and no claim is made about recoverability of the expired VPS.

Evidence: `docs/evidence/wb-0035-pre-a2-inventory-2026-08-23.md`.

### A2 — purchase + payment

`AUTHORIZED — EXACT ONE-VPS PURCHASE/PAYMENT; PAYPAL ONLY DISCOVERED; EXPLICIT METHOD SELECTION PENDING`

Operator authorization granted on 2026-08-23 at 22:08 CEST:

> Schvaluju A2: objednávku a platbu právě jednoho nového InterServer KVM VPS pro WB-0035, 1 slice, Ubuntu 24, bez control panelu, location 1 New Jersey, hostname tasks.cyberdjs.org, maximálně $3.00/měsíc a $0 neočekávaný jednorázový příplatek. Bez jakékoli jiné změny na InterServeru.

Bound purchase envelope:

```yaml
reuse_decision: new_provisioning
provider: InterServer
quantity: 1
platform: kvm
slices: 1
os_distro: ubuntu
os_version: ubuntu24
control_panel: none
period_months: 1
location_id: 1
location_name: New Jersey
hostname: tasks.cyberdjs.org
max_recurring_usd_month: 3.00
max_unexpected_one_time_surcharge_usd: 0.00
```

Payment-method discovery completed read-only. The first discovery returned HTTP 200 but its local temporary artifact was lost before sanitization. A second read-only discovery was sanitized atomically and returned:

```yaml
available_payment_method_ids:
  - paypal
raw_cart_temp_removed: true
```

No order, invoice creation, payment or provider mutation occurred during payment-method discovery. Availability of `paypal` is not treated as operator selection; an explicit method selection is still required before order creation.

Execution invariants after explicit `paypal` selection:

- perform a fresh `PUT /apiv2/vps/order` immediately before the order using the exact candidate and an ephemeral policy-compliant root password;
- abort unless `continue=true`, `errors=[]`, configuration matches exactly, recurring cost <= USD 3.00/month and no unexpected one-time surcharge appears;
- if the fresh quote passes, execute **exactly one** `POST /apiv2/vps/order` with the identical payload and same ephemeral root password;
- never automatically retry an ambiguous POST response;
- extract only the new service id and invoice id(s), then verify invoice ownership/amount read-only before charging;
- initiate payment only for the exact invoice created by this order and only via explicitly selected `paypal`;
- if PayPal requires a redirect or form submission, surface that next action to the operator instead of performing unrelated billing mutations;
- do not create/verify cards, add prepay credit or change account payment-method settings as part of A2;
- retain only sanitized order/payment evidence; never store API keys, root passwords, full payment data or gateway tokens;
- stop after order/payment verification. A3 and A4 remain separate gates.

Evidence: `docs/evidence/wb-0035-a2-order-payment-2026-08-23.md`.

### A3 — bootstrap + application deployment

`NOT_GRANTED`

Requires explicit approval after the intended VPS identity/IP/status/access method is verified. Scope must remain limited to that VPS.

### A4 — DNS publication

`NOT_GRANTED`

Requires separate approval for exactly:

```text
tasks.cyberdjs.org -> <approved VPS public IP>
```

No apex, `www`, MX, mail or unrelated DNS mutation is implied.

## Verified purchase candidate

```yaml
provider: InterServer
platform: kvm
slices: 1
os_distro: ubuntu
os_version: ubuntu24
control_panel: none
period_months: 1
location_id: 1
location_name: New Jersey
hostname: tasks.cyberdjs.org
catalog_price_usd_month: 3.00
quote_price_usd_month: 3.00
modeled_one_time_surcharge_usd: 0.00
ram_mib: 2048
disk_gib: 40
transfer_gib: 2000
quantity: 1
```

This candidate is authorized for A2 purchase/payment, but no order or payment is claimed until runtime evidence verifies it.

## Later phases

A3 hardening/application deployment remains blocked until explicit authorization after the purchased VPS identity/status/access method is verified. DNS publication remains blocked until A4.

Planned deployment invariants remain: pinned image digests, Vikunja loopback-only behind Caddy, persistent `/srv/vikunja` data, no plaintext secrets in Git/chat/ordinary evidence, tested backup/restore before durable use.

Initial task workflow remains intentionally small:

```text
INBOX
TODAY
THIS WEEK
LATER
```

## Stop conditions

Stop on unavailable/ambiguous payment method, purchase price > USD 3.00/month, unexpected one-time charge, exact-config mismatch, ambiguous order response, unrelated invoice, credential/payment-data exposure risk, unrelated infrastructure impact, or any step requiring authority beyond A2.

Deleting/canceling/reactivating any VPS is a separate provider mutation and is never inferred from A2.
