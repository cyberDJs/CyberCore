# WB-0035 A2 — InterServer VPS order + payment

Status: `AUTHORIZED — ORDER/PAYMENT PENDING EXECUTION; PAYMENT METHOD DISCOVERY REQUIRED`

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

## Fail-closed execution plan

1. Discover available payment methods read-only before creating order state. Do not mutate the account payment-method configuration.
2. Freshly revalidate the exact candidate with `PUT /apiv2/vps/order` immediately before the order. Abort unless `continue=true`, `errors=[]`, exact config matches, recurring price <= USD 3.00/month and no unexpected one-time surcharge exists.
3. Execute exactly one `POST /apiv2/vps/order` using the identical payload and same ephemeral root password used for the fresh validation.
4. Never automatically retry the POST if the response is missing, ambiguous, timed out after submission, or otherwise uncertain. Inspect resulting provider state instead.
5. Extract only the new service id and invoice id(s). Before payment, verify the invoice belongs to the new VPS and the amount is within the approved envelope.
6. Initiate payment only for that exact invoice via one explicitly selected available payment method. Do not change the default account payment method as part of A2.
7. Record sanitized evidence only. Never retain the API key, root password, full payment data, gateway tokens, or unrelated account/billing information.
8. Stop after order/payment verification. A3 bootstrap/deploy and A4 DNS remain unauthorized.

## Unresolved execution input

The user authorized payment but did not choose a gateway/method. InterServer requires `method` explicitly for `initiatePayment`; supported methods include `cc`, `paypal`, `prepay` and other gateways. CyberCore must not guess which funding source to charge.

Therefore the next provider action is read-only payment-method discovery through `/billing/cart`. It must reveal only the available method identifiers needed to continue.

## Current state

```yaml
A2_authorized: true
order_authorized: true
payment_authorized: true
exact_quantity: 1
candidate_bound: true
fresh_quote_required_before_order: true
payment_method_selected: false
order_performed: false
invoice_created: false
payment_performed: false
provider_mutation_performed_under_A2: false
A3_bootstrap_deploy_authorized: false
A4_dns_authorized: false
```

## Stop line

Do not order until the available payment methods are discovered and the chosen method is explicit. Do not change payment-method settings, create/verify cards, add prepays, reactivate the expired VPS, perform SSH/bootstrap/deploy, or change DNS under A2.
