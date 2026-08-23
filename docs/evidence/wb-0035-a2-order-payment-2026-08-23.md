# WB-0035 A2 — InterServer VPS order + payment

Status: `AUTHORIZED — PAYPAL EXPLICITLY SELECTED; EXACT-HEAD GATES PENDING; ORDER NOT YET PLACED`

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

A1 already verified this exact candidate at USD 3.00/month with `continue=true` and no validation errors. PRE-A2 verified zero active VPS services and recommended new provisioning.

## Reviewed provider semantics

```text
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

The operator explicitly selected `paypal` for this A2 transaction. Availability and operator selection are now both established.

This selection authorizes payment initiation only through `paypal` and only for the invoice(s) created by the exact approved A2 order. It does not authorize changing the account default payment method, adding cards, verifying cards, creating prepays, or performing unrelated billing/account mutations.

## Exact-head governance gate before provider mutation

Before the order POST is executed, the current PR head must have:

1. CI success on the exact head;
2. CodeQL success on the exact head;
3. a fresh Codex review targeting that same exact head after CI/CodeQL are green.

The PR remains draft. Provider mutation must not start until these gates are satisfied.

## Fail-closed execution plan after governance gates

1. Freshly revalidate the exact candidate with `PUT /apiv2/vps/order` immediately before the order. Abort unless `continue=true`, `errors=[]`, exact config matches, recurring price <= USD 3.00/month, and no unexpected one-time surcharge exists.
2. Execute exactly one `POST /apiv2/vps/order` using the identical payload and same ephemeral root password used for the fresh validation.
3. Never automatically retry the POST if the response is missing, ambiguous, timed out after submission, or otherwise uncertain. Inspect resulting provider state instead.
4. Extract only the new service id and invoice id(s). Before payment, verify invoice ownership/amount read-only and bind them to the new VPS.
5. Initiate payment only for those exact invoice(s) via `paypal`. If the provider returns a redirect or form-submission action, surface that action to the operator rather than attempting unrelated billing mutations.
6. Do not change the default account payment method, create/verify a card, add prepay credit, reactivate/cancel another service, or alter account-security settings.
7. Record sanitized evidence only. Never retain the API key, root password, full payment data, gateway tokens, or unrelated account/billing information.
8. Stop after order/payment verification. A3 bootstrap/deploy and A4 DNS remain unauthorized.

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

**Stop before order creation until the exact-head CI, CodeQL, and fresh Codex review gates are satisfied.**

Do not change payment-method settings, create/verify cards, add prepays, reactivate the expired VPS, perform SSH/bootstrap/deploy, or change DNS under A2.
