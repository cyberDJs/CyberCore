# WB-0035 — InterServer VPS + Vikunja ADHD Time-Management MVP

## Status

`ACTIVE — A1 VERIFIED; PRE-A2 VERIFIED / ONE EXPIRED VPS / NEW RECOMMENDED; PURCHASE NOT AUTHORIZED`

Date: 2026-08-23
Canonical base: `main@2bea07db4e0a5d2a062c96ef1642a6f2a0927f0a`
Predecessor/parallel work: `WB-0034 — First Staging Deployment Preflight`
Provider: InterServer
Target workload: Vikunja-based attention-friendly task management MVP
Budget ceiling: USD 3.00/month unless separately approved

## Goal

Prepare a fail-closed path for CyberCore to discover the current InterServer VPS catalog, produce a non-mutating live quote, stop for explicit human approval before purchase/payment, and only later—under separate authority gates—provision at most one VPS, harden it, deploy Vikunja, publish DNS, and verify persistence/backup/restore.

A1 catalog + quote is verified. PRE-A2 read-only existing-VPS inventory is now verified and complete: the account contains one VPS record, it is `expired`, and there are no active VPS services available for immediate reuse. The current recommendation is therefore **new provisioning**, subject to separate A2 authorization. A2 purchase/payment, A3 bootstrap/deploy, and A4 DNS remain not granted.

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
GET  /apiv2/vps              -> existing VPS inventory on the authenticated account
GET  /apiv2/vps/order        -> current catalog / resources / stock / pricing inputs
PUT  /apiv2/vps/order        -> validate configuration and calculate quote without provisioning
POST /apiv2/vps/order        -> create the VPS order and invoice/service state
GET  /apiv2/vps/{id}         -> read service state after ordering
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

Verified live result from the operator Mac:

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

The authenticated catalog also showed KVM stock in New Jersey, Los Angeles and Dallas and the exact Ubuntu 24 template. `vpsSliceKvmLCost=3` is the KVM slice price; `vpsNyCost=1` is a distinct field and is not used as KVM price.

Live behavior established that submitted `osVersion=ubuntu24` is returned as `os=ubuntu24`, while submitted `osDistro=ubuntu` is returned as `version=ubuntu`. CyberCore fixtures/tests and parser logic have been corrected accordingly. Quote-only root-password generation now guarantees the provider-required character categories while keeping the value ephemeral and out of ordinary evidence.

Evidence: `docs/evidence/wb-0035-a1-catalog-quote-2026-08-23.md`.

A1 provider activity is complete. No further A1 provider calls are required.

### PRE-A2 — existing VPS inventory / reuse decision

`VERIFIED — COMPLETE; ONE EXPIRED VPS FOUND; NEW PROVISIONING RECOMMENDED`

Operator authorization granted on 2026-08-23 at 21:39 CEST:

> Schvaluju PRE-A2: read-only inventuru existujících InterServer VPS přes GET /apiv2/vps pro WB-0035. Bez jakékoli změny, restartu, resize, reinstallu, zrušení, objednávky nebo platby.

The single authorized `GET /apiv2/vps` executed from the operator Mac and returned `HTTP 200`. Shape-only sanitization reported an array containing exactly one VPS row. The local-only second pass extracted the authorized safe fields and then deleted the raw mode-0600 temporary response.

Sanitized result:

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

Interpretation and decision:

- no active VPS exists that can be reused as-is;
- the sole provider record is expired;
- `repeat_invoices_cost=3.00` is a provider field on the expired record and does not by itself prove current recurring billing;
- no SSH/application inspection was authorized or performed, so no claim is made about preserved data or recoverability on the expired VPS;
- reactivation/renewal of the expired VPS would itself require a separate provider-side authorization and was not evaluated under PRE-A2;
- the current WB-0035 recommendation is **new provisioning** using the A1-verified one-slice KVM candidate;
- according to the verified inventory, such a new VPS would not duplicate an active VPS service.

Evidence: `docs/evidence/wb-0035-pre-a2-inventory-2026-08-23.md`.

Still prohibited:

- purchase/payment;
- reactivation/renewal of the expired VPS;
- reboot/start/stop/shutdown;
- resize/reinstall/migrate;
- cancel/delete;
- credential or account-security mutation;
- SSH/application access;
- DNS mutation;
- any other provider mutation.

### A2 — purchase + payment

`NOT_GRANTED`

Requires a separate explicit approval after A1 and PRE-A2 are verified.

Current A2 candidate basis:

```yaml
reuse_decision: new_provisioning_recommended
active_existing_vps_count: 0
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
recurring_price_usd_month: 3.00
modeled_one_time_surcharge_usd: 0.00
quantity: 1
```

A2 must bind exact provider configuration, recurring price, one-time cost, payment action, hostname, OS/platform/location, quantity exactly one, and the explicit new-provisioning decision. Ambiguous order responses must never be blindly retried.

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

## Verified A1 candidate

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

This is verified quote and PRE-A2 planning evidence, **not purchase authorization**.

## Later phases

Phase 3 purchase/provisioning remains blocked until A2. Phase 4 hardening and Phase 5 Vikunja deployment remain blocked until A3. DNS publication remains blocked until A4.

Planned deployment invariants remain: pinned image digests, Vikunja loopback-only behind Caddy, persistent `/srv/vikunja` data, no plaintext secrets in Git/chat/ordinary evidence, tested backup/restore before durable use.

Initial task workflow remains intentionally small:

```text
INBOX
TODAY
THIS WEEK
LATER
```

## Stop conditions

Stop on purchase price > USD 3.00/month, unexpected one-time charge, ambiguous provider behavior, credential exposure risk, unrelated infrastructure impact, or any step requiring authority beyond the current gate.

Deleting/canceling/reactivating an expired or paid VPS is itself a provider mutation and is never inferred from a failed deployment.
