# WB-0035 — InterServer VPS + Vikunja ADHD Time-Management MVP

## Status

`ACTIVE — A1 VERIFIED; PRE-A2 VERIFIED; A2 AUTHORIZED / PAYPAL SELECTED / PRE-ORDER INVENTORY RACE GUARD REQUIRED / EXACT-HEAD GATES PENDING; A3/A4 NOT AUTHORIZED`

Date: 2026-08-23
Canonical base: `main@2bea07db4e0a5d2a062c96ef1642a6f2a0927f0a`
Predecessor/parallel work: `WB-0034 — First Staging Deployment Preflight`
Provider: InterServer
Target workload: Vikunja-based attention-friendly task management MVP
Budget ceiling: USD 3.00/month unless separately approved

## Goal

Prepare and execute a fail-closed path for CyberCore to discover the current InterServer VPS catalog, quote an exact one-slice candidate, inspect existing inventory, execute an explicitly authorized bounded purchase/payment, and only later—under separate gates—harden the resulting VPS, deploy Vikunja, publish DNS, and verify persistence/backup/restore.

A1 catalog + quote is verified. PRE-A2 inventory is verified: the account contained exactly one VPS record, `vps_id=3447580`, and it was `expired`; active VPS count was zero. A2 authorizes purchase/payment of exactly one new VPS matching the verified candidate. Payment-method discovery exposed only `paypal`, and the operator explicitly selected `paypal` at 2026-08-23T22:47:00+02:00. No order has yet been placed. A3 bootstrap/deploy and A4 DNS remain not granted.

## Client direction

CyberFlow is **iPhone-first**. Responsive web/PWA is the fallback; macOS may follow; Android is out of MVP scope.

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

Planned baseline: Ubuntu 24.04 LTS, KVM, one slice, no control panel, Docker Engine + Compose, Caddy, Vikunja + SQLite, hostname `tasks.cyberdjs.org`.

## InterServer API basis

Reviewed provider flow:

```text
GET  /apiv2/vps                         -> current VPS inventory
GET  /apiv2/vps/order                   -> current catalog / stock / pricing inputs
PUT  /apiv2/vps/order                   -> validate configuration and calculate quote
POST /apiv2/vps/order                   -> create VPS order + invoice/service state
GET  /apiv2/billing/cart                -> read checkout state / available payment methods
GET  /apiv2/billing/invoices/{id}       -> read invoice detail
GET  /apiv2/vps/{id}/invoices           -> read per-VPS invoice history
POST /apiv2/billing/pay/{method}/{invoices} -> initiate payment for named invoice(s)
GET  /apiv2/vps/{id}                    -> read service state after ordering
```

HTTP method alone is not a safety boundary. Authority is bound to the exact reviewed operation semantics.

## Authority model

### A0 — repository planning

`AUTHORIZED_BY_CURRENT_WORK`

Documentation, schemas, tests, synthetic fixtures and validators are allowed. Provider contact, billing mutation, purchase/payment, DNS, SSH, credential mutation and deployment are not allowed by A0 alone.

### A1 — live VPS catalog + quote

`VERIFIED — COMPLETE`

Operator authorization:

> Schvaluju A1: InterServer VPS catalog + quote pro WB-0035, maximálně $3/měsíc, pouze zjištění nabídky a ceny. Bez objednávky, platby nebo jiné změny na InterServeru.

Verified result:

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

The authenticated catalog showed KVM stock in New Jersey, Los Angeles and Dallas and the exact Ubuntu 24 template. `vpsSliceKvmLCost=3` is the KVM slice price; `vpsNyCost=1` is a separate field and is not used as KVM price.

Evidence: `docs/evidence/wb-0035-a1-catalog-quote-2026-08-23.md`.

### PRE-A2 — existing VPS inventory / reuse decision

`VERIFIED — COMPLETE; ONE EXPIRED VPS FOUND; NEW PROVISIONING RECOMMENDED`

Operator authorization:

> Schvaluju PRE-A2: read-only inventuru existujících InterServer VPS přes GET /apiv2/vps pro WB-0035. Bez jakékoli změny, restartu, resize, reinstallu, zrušení, objednávky nebo platby.

Verified sanitized baseline:

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

Decision: **new provisioning**. No active VPS existed that could be reused as-is. No SSH/application inspection was performed and no claim is made about preserved data or recoverability of the expired VPS.

Evidence: `docs/evidence/wb-0035-pre-a2-inventory-2026-08-23.md`.

### A2 — purchase + payment

`AUTHORIZED — EXACT ONE-VPS PURCHASE/PAYMENT; PAYPAL EXPLICITLY SELECTED; EXECUTION BLOCKED ON EXACT-HEAD GATES`

Purchase/payment authorization:

> Schvaluju A2: objednávku a platbu právě jednoho nového InterServer KVM VPS pro WB-0035, 1 slice, Ubuntu 24, bez control panelu, location 1 New Jersey, hostname tasks.cyberdjs.org, maximálně $3.00/měsíc a $0 neočekávaný jednorázový příplatek. Bez jakékoli jiné změny na InterServeru.

Payment-method selection:

> Volím paypal pro A2.

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
payment_method: paypal
```

Payment-method discovery completed read-only and returned:

```yaml
available_payment_method_ids:
  - paypal
payment_method_selected: true
selected_payment_method: paypal
raw_cart_temp_removed: true
```

No order, invoice creation, payment or provider mutation occurred during payment-method discovery.

#### Exact-head governance gate

Before any provider mutation under A2, the exact current PR head must have successful CI and CodeQL and then a fresh Codex review on that same head. Any fresh review finding that weakens A2 safety must be addressed first.

#### Pre-order inventory race guard

Immediately before the single order POST, execute one fresh read-only `GET /apiv2/vps` and abort unless the inventory still matches the PRE-A2 baseline exactly:

```yaml
expected_existing_vps_count: 1
expected_only_vps_id: "3447580"
expected_only_vps_status: expired
expected_active_or_pending_vps_count: 0
expected_target_hostname_occurrences: 0
```

Any additional VPS row, any baseline-state drift, any active/pending VPS, or any existing `tasks.cyberdjs.org` service blocks the POST. No automatic cancel/delete/reuse/second order is authorized.

#### A2 execution invariants

- fresh `PUT /apiv2/vps/order` using the exact candidate and one ephemeral policy-compliant root password;
- abort unless `continue=true`, `errors=[]`, exact config matches, recurring cost <= USD 3.00/month and unexpected one-time surcharge is USD 0.00;
- after the quote, run the pre-order inventory race guard immediately before mutation;
- only if both guards pass, execute **exactly one** `POST /apiv2/vps/order` with the identical payload and same ephemeral root password;
- never automatically retry an ambiguous/timed-out POST; inspect provider state read-only first;
- extract only the new service id and invoice id(s), verify invoice ownership/amount read-only, and bind payment to that exact new VPS;
- initiate payment only through `paypal` and only for the exact A2 invoice(s);
- if PayPal requires redirect/form submission, surface that next action to the operator;
- do not create/verify cards, add prepay credit, change the account default payment method, alter account security, or mutate unrelated services;
- retain only sanitized evidence; never store API keys, root passwords, full payment data or gateway tokens;
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
payment_method: paypal
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

Stop on exact-head gate failure, pre-order inventory drift, unavailable/ambiguous payment method, purchase price > USD 3.00/month, unexpected one-time charge, exact-config mismatch, ambiguous order response, unrelated invoice, credential/payment-data exposure risk, unrelated infrastructure impact, or any operation outside A2.

Deleting/canceling/reactivating any VPS is a separate provider mutation and is never inferred from A2.
