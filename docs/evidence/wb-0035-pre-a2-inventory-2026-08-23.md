# WB-0035 PRE-A2 — InterServer existing VPS inventory

Status: `VERIFIED — READ-ONLY INVENTORY COMPLETE; ONE EXPIRED VPS FOUND; NEW PROVISIONING RECOMMENDED`

Date: 2026-08-23
Work block: `WB-0035 — InterServer VPS + Vikunja ADHD Time-Management MVP`
Provider: InterServer
Operation: `GET /apiv2/vps`

## Operator authorization

Granted at: 2026-08-23T21:39:00+02:00

> Schvaluju PRE-A2: read-only inventuru existujících InterServer VPS přes GET /apiv2/vps pro WB-0035. Bez jakékoli změny, restartu, resize, reinstallu, zrušení, objednávky nebo platby.

## Verified runtime result

The single authorized inventory request executed from the operator Mac and returned `HTTP=200`. The provider response was an array with exactly one VPS row. A local-only sanitization pass extracted the approved non-secret fields and then deleted the raw mode-0600 temporary response.

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

`vps_comment` was intentionally excluded from retained evidence.

## Interpretation

- exactly one VPS record exists in the authenticated inventory;
- the sole record is `expired`, so there are zero active VPS services available for immediate reuse;
- `repeat_invoices_cost=3.00` is a field on the expired service record and does not prove a current recurring charge;
- no SSH/application inspection was authorized or performed, so no claim is made about preserved data or recoverability;
- reactivation/renewal of the expired service would itself require separate authorization;
- according to this inventory, a new VPS would not duplicate an active VPS service.

## Reuse-vs-new decision

**Recommendation: NEW PROVISIONING for WB-0035, subject to separate A2 purchase/payment authorization.**

The A1-verified new candidate remains one KVM slice, Ubuntu 24, no control panel, location 1 / New Jersey, hostname `tasks.cyberdjs.org`, recurring price USD 3.00/month, quantity 1.

## Completion receipt

```yaml
PRE_A2_authorized: true
inventory_endpoint: GET /apiv2/vps
inventory_executed: true
inventory_http_status: 200
inventory_verified: true
existing_vps_count: 1
active_vps_count: 0
expired_vps_count: 1
raw_temp_removed: true
reuse_viable_as_is: false
reuse_vs_new_decision: new_recommended
provider_mutation_performed: false
order_performed: false
payment_performed: false
A2_purchase_authorized: false
A2_payment_authorized: false
A3_bootstrap_deploy_authorized: false
A4_dns_authorized: false
```

## Stop line

**PRE-A2 is VERIFIED and complete. Stop provider activity here.**

Do not perform another inventory request, reactivate/renew the expired VPS, call `POST /apiv2/vps/order`, purchase/pay, reboot, resize, reinstall, cancel, change credentials/account security, access the VPS over SSH, deploy applications, or change DNS without the applicable next explicit authorization.
