# WB-0035 A2 — InterServer VPS order + payment

Status: `AUTHORIZED — PAYMENT-METHOD DISCOVERY EXECUTED; SAFE METHOD IDS PENDING LOCAL EXTRACTION; ORDER NOT YET PLACED`

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

The reviewed InterServer contract is:

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

The operator executed the planned read-only checkout discovery from the Mac:

```text
GET /apiv2/billing/cart
HTTP=200
```

Shape-only inspection reported an object containing, among other checkout fields:

```yaml
payment_method_related_fields:
  - paymentMethods
  - paymentMethodsData
  - paymentMethodsType
  - pymt_method
nested_related_key_observed:
  - REPEAT_BILLING_METHOD
raw_cart_temp_retained: true
```

Interpretation:

- authenticated billing-cart access succeeded;
- the response exposes the expected payment-method structures;
- no payment-method values, card details, funding-source data, or unrelated billing values have yet been retained in evidence;
- the raw response remains only in the operator Mac temporary file for one local sanitization pass;
- no order, invoice creation, payment or provider mutation occurred in this discovery step;
- no second `/billing/cart` request is needed.

## Next local-only step

Extract only payment method identifiers that match the reviewed `initiatePayment` method allowlist from the already-retained cart response. Do not retain card metadata, account profile data, invoice rows, gateway tokens or unrelated checkout fields. Then remove the raw cart temporary file.

After safe method identifiers are known, the operator must explicitly select which available funding source to use. CyberCore must not guess.

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
payment_method_discovery_executed: true
payment_method_discovery_http_status: 200
payment_method_structures_present: true
payment_method_ids_sanitized: false
payment_method_selected: false
fresh_quote_required_before_order: true
order_performed: false
invoice_created: false
payment_performed: false
provider_mutation_performed_under_A2: false
raw_cart_temp_retained_on_operator_mac: true
A3_bootstrap_deploy_authorized: false
A4_dns_authorized: false
```

## Stop line

Do not order until safe available payment method identifiers have been extracted locally and the operator explicitly selects one. Do not change payment-method settings, create/verify cards, add prepays, reactivate the expired VPS, perform SSH/bootstrap/deploy, or change DNS under A2.
