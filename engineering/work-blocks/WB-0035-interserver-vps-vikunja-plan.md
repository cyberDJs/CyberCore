# WB-0035 — InterServer VPS + Vikunja ADHD Time-Management MVP

## Status

`ACTIVE — A1 AUTHORIZED; AUTHENTICATED CATALOG VERIFIED; LIVE QUOTE VALIDATION BLOCKED BY PASSWORD POLICY; PURCHASE NOT AUTHORIZED`

Date: 2026-08-23
Canonical base: `main@2bea07db4e0a5d2a062c96ef1642a6f2a0927f0a`
Predecessor/parallel work: `WB-0034 — First Staging Deployment Preflight`
Provider: InterServer
Target workload: Vikunja-based attention-friendly task management MVP
Budget ceiling: USD 3.00/month unless separately approved

## Goal

Prepare a fail-closed path for CyberCore to discover the current InterServer VPS catalog, produce a non-mutating live quote, stop for explicit human approval before purchase/payment, and only later—under separate authority gates—provision at most one VPS, harden it, deploy Vikunja, publish DNS, and verify persistence/backup/restore.

The work-block definition alone does not authorize provider contact, VPS purchase, billing/payment, DNS mutation, credential mutation, SSH mutation, or application deployment. A separate operator authorization granted A1 catalog + quote on 2026-08-23; A2 purchase/payment, A3 bootstrap/deploy, and A4 DNS remain not granted.

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

Current provider contract reviewed for WB-0035:

```text
GET  /apiv2/vps              -> existing VPS inventory on the authenticated account
GET  /apiv2/vps/order        -> current catalog / resources / stock / pricing inputs
PUT  /apiv2/vps/order        -> validate configuration and calculate quote without provisioning
POST /apiv2/vps/order        -> create the VPS order and invoice/service state
GET  /apiv2/vps/{id}         -> read service state after ordering
```

HTTP method alone is not treated as a safety boundary because some provider endpoints may be side-effecting despite GET semantics. A1 allows only the explicitly reviewed catalog GET and quote PUT.

## Authority model

### A0 — repository planning

`AUTHORIZED_BY_CURRENT_WORK`

Documentation, schemas, tests, synthetic fixtures and validators are allowed. Provider contact, billing inspection, purchase/payment, DNS, SSH, credential mutation and deployment are not allowed by A0 alone.

### A1 — live VPS catalog + quote

`AUTHORIZED — CATALOG VERIFIED; QUOTE VALIDATION BLOCKED BY ROOT-PASSWORD POLICY`

Operator authorization:

> Schvaluju A1: InterServer VPS catalog + quote pro WB-0035, maximálně $3/měsíc, pouze zjištění nabídky a ceny. Bez objednávky, platby nebo jiné změny na InterServeru.

Allowed:

- `GET /apiv2/vps/order`;
- documented non-mutating `PUT /apiv2/vps/order` validation/quote;
- recurring price ceiling USD 3.00/month;
- sanitized non-secret evidence only.

Still prohibited:

- VPS order;
- invoice/payment;
- provider/account configuration mutation;
- API-key rotation;
- IP allow-list mutation;
- DNS, SSH or application mutation;
- secret values in ordinary evidence.

### Live A1 evidence

Authenticated catalog from the operator Mac returned HTTP 200 and verified:

```yaml
currency: USD
platform: kvm
kvm_slice_price_field: vpsSliceKvmLCost
kvm_slice_price_usd_month: 3.00
ram_per_slice_mib: 2048
disk_per_slice_gib: 40
transfer_per_slice_gib: 2000
ubuntu24_template: ubuntu24
locations:
  1: New Jersey
  2: Los Angeles
  3: Dallas, TX
```

All three locations reported KVM stock. `vpsNyCost=1` was also observed but is a distinct catalog field and is not used as the KVM slice price.

The authorized non-mutating quote PUT then returned HTTP 200 with:

```yaml
continue: false
service_cost: 3
original_cost: 3
slice_cost: 3
repeat_slice_cost: 3
repeat_service_cost: 3
monthly_service_cost: 3
os: ubuntu24
version: ubuntu
slices: "1"
platform: kvm
controlpanel: none
period: 1
location: 1
hostname: tasks.cyberdjs.org
```

The only returned validation error was the provider root-password policy. No order, invoice, payment or provider mutation occurred.

Live response behavior also established that submitted `osVersion=ubuntu24` is returned as `os=ubuntu24`, while submitted `osDistro=ubuntu` is returned as `version=ubuntu`.

CyberCore has been corrected to:

- use `vpsSliceKvmLCost` instead of `vpsNyCost` for the selected KVM price;
- require exact `templates.kvm.ubuntu.ubuntu24` availability;
- validate the observed live quote `os`/`version` field mapping;
- generate an ephemeral quote-only root password guaranteed to contain lowercase, uppercase, digit and provider-compatible special characters;
- keep the secret out of ordinary evidence.

Evidence: `docs/evidence/wb-0035-a1-catalog-quote-2026-08-23.md`.

A1 reaches `VERIFIED` only after a policy-compliant retry returns `continue=true` and the sanitized quote passes all budget/configuration gates.

### A2 — purchase + payment

`NOT_GRANTED`

Requires a separate explicit approval after A1 is verified. Before any A2 decision, CyberCore must also inspect current account VPS inventory (`GET /apiv2/vps` / `getVpsList`) under separate explicit read-only authorization and decide **reuse vs new provisioning**.

A2 must bind exact provider configuration, recurring price, one-time cost, payment action, hostname, OS/platform/location and quantity exactly one. Ambiguous order responses must never be blindly retried.

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

## Phase 2 — current live A1 candidate

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
quote_price_usd_month_observed: 3.00
ram_mib: 2048
disk_gib: 40
transfer_gib: 2000
quantity: 1
```

Quote passes only when `continue=true`, errors are empty, the exact candidate matches, recurring price is <= USD 3.00/month, one-time cost stays within the explicit ceiling, and no order/payment occurred.

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

Stop on quote > USD 3.00/month, validation error, unexpected one-time charge, ambiguous provider behavior, credential exposure risk, duplicate/new-service ambiguity, unrelated infrastructure impact, or any step requiring authority beyond the current gate.

Deleting/canceling a paid VPS is itself a provider mutation and is never inferred from a failed deployment.
