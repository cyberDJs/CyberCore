# WB-0035 PRE-A2 — InterServer existing VPS inventory

Status: `PARTIAL — READ-ONLY INVENTORY EXECUTED; ONE VPS FOUND; SANITIZED VALUES PENDING`

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

Interpretation:

- exactly one existing VPS service is present in the authenticated account inventory response;
- the provider returned the expected small read-only service summary shape;
- no values beyond field names/count were exposed during the first sanitization pass;
- the raw response remains only in the operator Mac mode-0600 temporary file for local sanitization;
- no second provider request is needed or authorized for this PRE-A2 inventory step;
- no provider mutation occurred.

## Next local-only sanitization

Use the existing temporary file only. Retain at most these safe fields from the one inventory row:

- `vps_id`
- `vps_name`
- `vps_hostname`
- `vps_ip`
- `vps_status`
- `services_name`
- `repeat_invoices_cost`

Do not retain `vps_comment` unless it is independently reviewed and clearly needed.

After sanitized values are recorded, delete the raw temporary file and decide reuse-vs-new.

## Current state

```yaml
PRE_A2_authorized: true
inventory_endpoint: GET /apiv2/vps
inventory_executed: true
inventory_http_status: 200
inventory_shape: array
existing_vps_count: 1
inventory_values_sanitized: false
inventory_verified: partial
reuse_vs_new_decision: pending
raw_temp_retained_on_operator_mac: true
provider_mutation_performed: false
A2_purchase_authorized: false
A2_payment_authorized: false
A3_bootstrap_deploy_authorized: false
A4_dns_authorized: false
```

## Stop line

Do not perform another provider inventory request. Complete only local sanitization of the already-retrieved response, remove the raw temporary file, record the reuse-vs-new decision, then stop for a separate A2 decision.
