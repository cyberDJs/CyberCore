# WB-0035 A2 — InterServer VPS order + payment

Status: `AUTHORIZED — PAYMENT-METHOD DISCOVERY MUST BE REPEATED READ-ONLY; ORDER NOT YET PLACED`

Date: 2026-08-23
Work block: `WB-0035 — InterServer VPS + Vikunja ADHD Time-Management MVP`
Provider: InterServer
Target hostname: `tasks.cyberdjs.org`

## Operator authorization

Granted at: 2026-08-23T22:08:00+02:00

> Schvaluju A2: objednávku a platbu právě jednoho nového InterServer KVM VPS pro WB-0035, 1 slice, Ubuntu 24, bez control panelu, location 1 New Jersey, hostname tasks.cyberdjs.org, maximálně $3.00/měsíc a $0 neočekávaný jednorázový příplatek. Bez jakékoli jiné změny na InterServeru.

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

`POST /apiv2/vps/order` is a real provider mutation. It creates a pending VPS service and invoice state; provisioning requires the initial invoice to be paid. The payment operation must target only the invoice returned for this exact A2 order.

## Payment-method discovery runtime

The first read-only checkout discovery executed successfully from the operator Mac:

```text
GET /apiv2/billing/cart
HTTP=200
```

Shape-only inspection confirmed payment-method structures such as `paymentMethods`, `paymentMethodsData`, `paymentMethodsType`, and `pymt_method`. No order, invoice creation, payment, or provider mutation occurred.

The intended local-only sanitization could not run because the shell no longer had the temporary-file variable/file available and returned:

```text
A2_CART_TMP_MISSING
```

Therefore no payment-method identifiers were extracted, and no funding source has been selected. The missing temporary artifact is a local execution-state loss, not a provider-side ambiguity and not an order/payment ambiguity.

## Recovery plan

A second `GET /apiv2/billing/cart` is permitted as a read-only recovery step within the already authorized A2 execution because it does not create an order, invoice, charge, or account mutation. The response must be sanitized in the same shell immediately, retaining only payment method identifiers matching the reviewed `initiatePayment` allowlist, then the temporary raw response must be deleted.

No order POST may occur until a payment method is successfully extracted and explicitly selected by the operator.

## Fail-closed execution plan after method selection

1. Freshly revalidate the exact candidate with `PUT /apiv2/vps/order` immediately before the order. Abort unless `continue=true`, `errors=[]`, exact config matches, recurring price <= USD 3.00/month and no unexpected one-time surcharge exists.
2. Execute exactly one `POST /apiv2/vps/order` using the identical payload and same ephemeral root password used for the fresh validation.
3. Never automatically retry the POST if the response is missing, ambiguous, timed out after submission, or otherwise uncertain. Inspect resulting provider state instead.
4. Extract only the new service id and invoice id(s). Before payment, verify the invoice belongs to the new VPS and the amount is within the approved envelope.
5. Initiate payment only for that exact invoice via the explicitly selected available payment method. Do not change the default account payment method as part of A2.
6. Record sanitized evidence only. Never retain the API key, root password, full payment data, gateway tokens, or unrelated account/billing information.
7. Stop after order/payment verification. A3 bootstrap/deploy and A4 DNS remain unauthorized.

## Current state

```yaml
A2_authorized: true
order_authorized: true
payment_authorized: true
exact_quantity: 1
candidate_bound: true
payment_method_discovery_attempts: 1
payment_method_discovery_last_http_status: 200
payment_method_structures_present: true
payment_method_ids_sanitized: false
payment_method_selected: false
cart_temp_available: false
read_only_cart_rediscovery_required: true
fresh_quote_required_before_order: true
order_performed: false
invoice_created: false
payment_performed: false
provider_mutation_performed_under_A2: false
A3_bootstrap_deploy_authorized: false
A4_dns_authorized: false
```

## Stop line

Do not order until safe available payment method identifiers have been extracted and the operator explicitly selects one. Do not change payment-method settings, create/verify cards, add prepays, reactivate the expired VPS, perform SSH/bootstrap/deploy, or change DNS under A2.
