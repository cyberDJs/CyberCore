# WB-0035 PRE-A2 — InterServer existing VPS inventory

Status: `VERIFIED — READ-ONLY INVENTORY COMPLETE; ONE EXPIRED VPS FOUND; NEW PROVISIONING RECOMMENDED`

Date: 2026-08-23
Work block: `WB-0035 — InterServer VPS + Vikunja ADHD Time-Management MVP`
Provider: InterServer
Operation: `GET /apiv2/vps`

## Operator authorization

Granted at: 2026-08-23T21:39:00+02:00

Explicit authorization text:

> Schvaluju PRE-A2: read-only inventuru existujících InterServer VPS přes GET /apiv2/vps pro WB-0035. Bez jakékoli změny, restartu, resize, reinstallu, zrušení, objednávky nebo platby.

## Authorized scope

Allowed:

- exactly one read-only authenticated inventory request to `GET /apiv2/vps` for WB-0035;
- local processing of the returned inventory into a sanitized summary;
- determining how many VPS services exist, which are active, their safe non-secret identifying/configuration facts, monthly cost where returned, and whether reuse is plausible;
- evidence sufficient to make the PRE-A2 reuse-vs-new decision.

Not authorized:

- `POST /apiv2/vps/order` or any VPS order;
- invoice or payment action;
- reboot, shutdown, start, reinstall, resize, migrate, cancel or delete;
- password or credential change/rotation;
- account-security or IP-limit mutation;
- SSH or application access to an existing VPS;
- DNS mutation;
- any other provider mutation.

## Runtime execution

The operator executed the single authorized inventory request from the Mac.

Transport result:

```text
HTTP=200
```

Shape-only sanitization of the raw response reported:

```yaml
shape: array
count: 1
first_item_keys:
  - repeat_invoices_cost
  - services_name
  - vps_comment
  - vps_hostname
  - vps_id
  - vps_ip
  - vps_name
  - vps_status
raw_temp_retained: true
```

The second pass was local-only against the already-retrieved mode-0600 temporary file. It did not contact InterServer again. `vps_comment` was intentionally excluded.

Sanitized inventory:

```yaml
existing_vps_count: 1
vps:
  - vps_id: "3447580"
    vps_name: "KVM540"
    vps_hostname: "vps3447580"
    vps_ip: "162.35.163.231"
    vps_status: "expired"
    services_name: "KVM Linux VPS Slice"
    repeat_invoices_cost: "3.00"
```

After sanitization the raw temporary response was deleted successfully:

```text
RAW_TEMP_REMOVED=yes
```

## Interpretation

- exactly one VPS record exists in the authenticated account inventory;
- its provider status is `expired`, so the inventory contains **zero active VPS services** available for immediate reuse;
- the provider lists `repeat_invoices_cost=3.00` for the expired service, but PRE-A2 does not prove that this expired record is currently billing USD 3.00/month;
- the hostname is the provider-style generic `vps3447580`, not the WB-0035 target `tasks.cyberdjs.org`;
- no SSH/application inspection was authorized or performed, so no claim is made about preserved data or recoverability on the expired service;
- the raw provider response was removed from the operator Mac after sanitization;
- no provider mutation occurred.

## Reuse-vs-new decision

**Recommendation: NEW PROVISIONING for WB-0035, subject to a separate A2 purchase/payment authorization.**

Reasoning:

1. There is no active VPS in the current inventory that can be reused as-is.
2. The sole record is expired and therefore cannot host the task-management MVP without a provider-side reactivation/renewal action, which was not evaluated or authorized in PRE-A2.
3. A new one-slice KVM candidate is already A1-verified at USD 3.00/month with the intended Ubuntu 24 configuration.
4. According to the current inventory, a new VPS would not duplicate an active VPS service. The expired record remains an account-history/service record and must not be canceled, reactivated or otherwise changed without separate authorization.

If preservation or recovery of data from VPS `3447580` becomes important, stop before A2 and obtain a separate narrowly-scoped read-only authorization to inspect only the information required to assess recoverability. PRE-A2 itself does not authorize such inspection.

## Completion receipt

```yaml
PRE_A2_authorized: true
inventory_endpoint: GET /apiv2/vps
inventory_executed: true
inventory_http_status: 200
inventory_shape: array
existing_vps_count: 1
active_vps_count: 0
expired_vps_count: 1
inventory_values_sanitized: true
inventory_verified: true
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
