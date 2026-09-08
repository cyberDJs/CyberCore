# WB-0035 A2 — InterServer VPS order + payment

Status: `AUTHORIZED — PAYPAL SELECTED; PRE-ORDER INVENTORY RACE GUARD ADDED; EXACT-HEAD GATES PENDING; ORDER NOT YET PLACED`

Date: 2026-08-23
Work block: `WB-0035 — InterServer VPS + Vikunja ADHD Time-Management MVP`
Provider: InterServer
Target hostname: `tasks.cyberdjs.org`

## Operator authorization

A2 purchase/payment authorization granted at 2026-08-23T22:08:00+02:00:

> Schvaluju A2: objednávku a platbu právě jednoho nového InterServer KVM VPS pro WB-0035, 1 slice, Ubuntu 24, bez control panelu, location 1 New Jersey, hostname tasks.cyberdjs.org, maximálně $3.00/měsíc a $0 neočekávaný jednorázový příplatek. Bez jakékoli jiné změny na InterServeru.

Payment method selection granted at 2026-08-23T22:47:00+02:00:

> Volím paypal pro A2.

## Authorized purchase envelope

```yaml
provider: InterServer
quantity: 1
reuse_decision: new_provisioning
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

A1 already verified this exact candidate at USD 3.00/month with `continue=true` and no validation errors. PRE-A2 verified the provider inventory baseline as exactly one VPS row: `vps_id=3447580`, `vps_status=expired`, with zero active VPS services; the reuse decision is new provisioning.

## Reviewed provider semantics

```text
GET  /apiv2/vps                     -> read current VPS inventory
PUT  /apiv2/vps/order               -> non-mutating validation/quote
POST /apiv2/vps/order               -> create one VPS service + recurring invoice + initial invoice
GET  /apiv2/billing/cart            -> read checkout/payment-method availability
GET  /apiv2/billing/invoices/{id}   -> read invoice detail
GET  /apiv2/vps/{id}/invoices       -> read VPS invoice history
POST /apiv2/billing/pay/{method}/{invoices} -> initiate payment for exactly the named invoice(s)
```

`POST /apiv2/vps/order` is a real provider mutation. It creates pending VPS/invoice state. The payment operation must target only invoice(s) returned for this exact A2 order.

## Payment-method discovery runtime

The first read-only checkout discovery returned `HTTP=200`, but its local temporary artifact was lost before sanitization. No provider mutation occurred.

A read-only recovery discovery was then executed and sanitized atomically:

```text
GET /apiv2/billing/cart
HTTP=200
```

Sanitized result:

```yaml
available_payment_method_ids:
  - paypal
raw_cart_temp_removed: true
```

No card metadata, account profile data, invoice rows, gateway tokens, or unrelated checkout values were retained. No order, invoice creation, payment, or other provider mutation occurred during discovery.

## Explicit funding-method selection

The operator explicitly selected `paypal` for this A2 transaction. Availability and operator selection are both established.

This selection authorizes payment initiation only through `paypal` and only for invoice(s) created by the exact approved A2 order. It does not authorize changing the account default payment method, adding cards, verifying cards, creating prepays, or performing unrelated billing/account mutations.

## Exact-head governance gate before provider mutation

Before the order POST is executed, the current PR head must have:

1. CI success on the exact head;
2. CodeQL success on the exact head;
3. a fresh Codex review targeting that same exact head after CI/CodeQL are green;
4. no unresolved fresh-review finding that weakens the A2 fail-closed boundary.

The PR remains draft. Provider mutation must not start until these gates are satisfied.

## Pre-order inventory race guard

Immediately before the single order POST, A2 requires one fresh read-only `GET /apiv2/vps` as a duplicate-service / TOCTOU guard. This read is part of enforcing the operator's `quantity: 1` authorization; it does not authorize any lifecycle or account mutation.

The order must abort unless the fresh inventory still matches the PRE-A2 baseline exactly:

```yaml
expected_existing_vps_count: 1
expected_only_vps_id: "3447580"
expected_only_vps_status: expired
expected_active_or_pending_vps_count: 0
expected_target_hostname_occurrences: 0
```

Any additional VPS row, any non-expired state for the baseline row, any active/pending VPS, or any existing `tasks.cyberdjs.org` service blocks the POST and requires human reconciliation. No automatic cancellation, deletion, reuse, or second order is permitted.

## Fail-closed execution plan after governance gates

1. Freshly revalidate the exact candidate with `PUT /apiv2/vps/order` using an ephemeral policy-compliant root password. Abort unless `continue=true`, `errors=[]`, exact config matches, recurring price <= USD 3.00/month, and no unexpected one-time surcharge exists.
2. Immediately after the quote, execute the read-only pre-order inventory race guard above. Abort unless the inventory still matches the exact PRE-A2 baseline and the target service does not already exist.
3. If and only if both guards pass, execute exactly one `POST /apiv2/vps/order` using the identical quote payload and the same ephemeral root password.
4. Never automatically retry the POST if the response is missing, ambiguous, timed out after submission, or otherwise uncertain. Inspect provider state read-only instead.
5. Extract only the new service id and invoice id(s). Before payment, verify invoice ownership/amount read-only and bind them to the new VPS.
6. Initiate payment only for those exact invoice(s) via `paypal`. If the provider returns a redirect or form-submission action, surface that action to the operator rather than attempting unrelated billing mutations.
7. Do not change the default account payment method, create/verify a card, add prepay credit, reactivate/cancel another service, or alter account-security settings.
8. Record sanitized evidence only. Never retain the API key, root password, full payment data, gateway tokens, or unrelated account/billing information.
9. Stop after order/payment verification. A3 bootstrap/deploy and A4 DNS remain unauthorized.

## Current state

```yaml
A2_authorized: true
order_authorized: true
payment_authorized: true
exact_quantity: 1
candidate_bound: true
payment_method_discovery_attempts: 2
payment_method_discovery_last_http_status: 200
payment_method_ids_sanitized: true
available_payment_method_ids:
  - paypal
payment_method_selected: true
selected_payment_method: paypal
raw_cart_temp_removed: true
fresh_quote_required_before_order: true
pre_order_inventory_race_guard_required: true
pre_order_inventory_expected_count: 1
pre_order_inventory_expected_vps_id: "3447580"
pre_order_inventory_expected_status: expired
exact_head_ci_required: true
exact_head_codeql_required: true
exact_head_codex_review_required: true
order_performed: false
invoice_created: false
payment_performed: false
provider_mutation_performed_under_A2: false
A3_bootstrap_deploy_authorized: false
A4_dns_authorized: false
```

## Stop line

**Stop before order creation until exact-head CI, CodeQL and fresh Codex review gates are satisfied; then stop again on any pre-order inventory drift.**

Do not change payment-method settings, create/verify cards, add prepays, reactivate/cancel/delete the expired VPS, perform SSH/bootstrap/deploy, or change DNS under A2.
