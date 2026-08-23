# WB-0035 — InterServer VPS + Vikunja ADHD Time-Management MVP

## Status

`ACTIVE — A1 AUTHORIZED; AUTHENTICATED CATALOG VERIFIED; LIVE QUOTE PENDING; PURCHASE NOT AUTHORIZED`

Date: 2026-08-23
Canonical base: `main@2bea07db4e0a5d2a062c96ef1642a6f2a0927f0a`
Predecessor/parallel work: `WB-0034 — First Staging Deployment Preflight`
Provider: InterServer
Target workload: Vikunja-based attention-friendly task management MVP
Budget ceiling: USD 3.00/month unless separately approved

## Goal

Prepare a fail-closed path for CyberCore to:

1. discover the current InterServer VPS catalog without mutation;
2. produce a price/resource quote for the smallest suitable Linux VPS;
3. stop for explicit human approval before any purchase or billing action;
4. order and provision exactly one VPS only after that approval;
5. bootstrap a hardened Linux host;
6. deploy a minimal Vikunja stack;
7. expose the service through HTTPS only after a separately approved DNS step;
8. verify application health, persistence, backup readiness, and rollback;
9. bootstrap a minimal attention-friendly workflow through the Vikunja API;
10. record an evidence receipt without secrets.

The work-block definition alone does not authorize provider contact, VPS purchase, billing/payment, DNS mutation, credential mutation, SSH mutation, or application deployment. A separate operator authorization granted A1 catalog + quote on 2026-08-23; A2 purchase/payment, A3 bootstrap/deploy, and A4 DNS remain not granted.

## Client direction

CyberFlow is **iPhone-first**.

- primary client target: iPhone;
- responsive web/PWA: operational fallback;
- macOS integration: later where useful;
- Android: explicitly out of MVP scope and must not influence first-client architecture or UX.

See `docs/product/cyberflow-iphone-first-client.md`.

## Why Vikunja for the MVP

Vikunja is the selected MVP candidate because it is:

- open source and self-hostable;
- designed for tasks/projects rather than heavyweight enterprise project management;
- collaborative for multiple users/teams;
- available as a single bundled application container;
- suitable for a low-resource Docker deployment;
- exposed through a documented REST API suitable for a future CyberCore adapter;
- available in Czech localization;
- capable of list, table, Kanban and Gantt views without requiring those views in the minimal workflow.

The exact deployed version and container digest must be pinned during implementation preflight. No floating `latest` tag is permitted for a reproducible production deployment.

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

Persistent host data:
  /srv/vikunja/files
  /srv/vikunja/db
  /srv/vikunja/backups
```

MVP choices:

- OS: Ubuntu 24.04 LTS if present in the live InterServer catalog;
- platform: KVM;
- size: 1 slice if the live quote remains <= USD 3.00/month and resources are adequate;
- control panel: none;
- application runtime: Docker Engine + Compose plugin;
- reverse proxy: Caddy;
- database: SQLite for the first small-team MVP;
- application: Vikunja;
- public hostname candidate: `tasks.cyberdjs.org`;
- public DNS remains approval-gated and is not authorized by this work block.

If the live provider catalog, pricing, stock, or OS availability differs, the plan must be regenerated rather than silently substituting another configuration.

## InterServer API basis

Current official InterServer API documentation reviewed on 2026-08-23 exposes this VPS flow:

```text
GET  /apiv2/vps              -> existing VPS inventory on the authenticated account
GET  /apiv2/vps/order        -> current catalog / resources / stock / pricing inputs
PUT  /apiv2/vps/order        -> validate configuration and calculate quote without provisioning
POST /apiv2/vps/order        -> create the VPS order and invoice/service state
GET  /apiv2/vps/{id}         -> read service state after ordering
```

Billing/payment endpoints may use HTTP GET while still causing side effects. HTTP method is therefore not treated as a safety boundary. Any payment action is a mutation and requires explicit approval.

Authentication is documented through `X-API-KEY`. InterServer also documents account-wide Web/API source-IP restrictions. No provider security restriction may be bypassed or mutated under A1.

Official documentation references:

- `https://my.interserver.net/api-docs/redoc.html`
- `https://my.interserver.net/api-docs/`

## Authority model

### A0 — repository planning

`AUTHORIZED_BY_CURRENT_WORK`

Allowed:

- documentation;
- code/tests that cannot contact InterServer;
- manifest/schema design;
- synthetic fixtures;
- validators;
- dry-run logic that does not use provider credentials or network access.

Not allowed by A0 alone:

- provider API contact;
- billing/account inspection;
- VPS order/payment;
- provider mutation;
- DNS mutation;
- secret creation/rotation;
- SSH connection;
- remote package/container/application mutation.

### A1 — live VPS catalog + quote

`AUTHORIZED — AUTHENTICATED CATALOG VERIFIED; LIVE QUOTE PENDING`

Operator authorization granted on 2026-08-23:

> Schvaluju A1: InterServer VPS catalog + quote pro WB-0035, maximálně $3/měsíc, pouze zjištění nabídky a ceny. Bez objednávky, platby nebo jiné změny na InterServeru.

Allowed:

- provider: InterServer;
- scope: VPS catalog and quote only;
- `GET /apiv2/vps/order`;
- documented non-mutating `PUT /apiv2/vps/order` validation/quote operation;
- recurring price ceiling: USD 3.00/month;
- sanitized non-secret evidence only.

Still prohibited:

- VPS order;
- invoice/payment action;
- provider/account configuration mutation;
- API-key rotation;
- IP allow-list mutation;
- DNS, SSH or application mutation;
- any attempt to bypass provider security controls;
- secret values in ordinary evidence.

Execution history:

- initial isolated runtime: no usable authenticated provider call;
- first GitHub Actions attempt: blocked because `INTERSERVER_API_KEY` alias was absent;
- after operator configured the GitHub Actions secret: credential alias was present, but the bounded provider probe returned `HTTP 403`;
- operator Mac then performed the same authenticated `GET /apiv2/vps/order` contract and received `HTTP 200`;
- the live catalog verified USD currency, KVM stock in New Jersey / Los Angeles / Dallas, Ubuntu 24.04 availability, 2048 MiB RAM, 40 GiB disk and 2000 GiB transfer per slice;
- the selected KVM per-slice catalog price is `vpsSliceKvmLCost=3`; `vpsNyCost=1` is a distinct field and must not be used as the KVM price;
- no quote, order, payment or provider mutation occurred in the local catalog step.

Evidence: `docs/evidence/wb-0035-a1-catalog-quote-2026-08-23.md`.

A1 reaches `VERIFIED` only after the authorized quote validation succeeds and produces a sanitized approval packet containing only non-secret configuration, price, resource and availability facts.

### A2 — purchase + payment

`NOT_GRANTED`

Requires a separate explicit approval after A1 produces a valid quote.

Before any A2 decision, CyberCore must also inspect the current account VPS inventory (`GET /apiv2/vps` / `getVpsList`) and decide **reuse vs new provisioning**. This read-only inventory step is not retroactively claimed by the existing A1 catalog+quote authorization; it requires explicit operator approval before execution.

The approval packet must bind:

- exact provider configuration;
- exact quoted recurring price;
- exact one-time cost if any;
- expected invoice/payment action;
- maximum charge;
- hostname;
- OS/platform/location;
- quantity: exactly one VPS;
- current VPS inventory/reuse decision;
- rollback/cancellation assumptions known at that time.

No retry may create a second service. The implementation must use an idempotency or duplicate-service guard based on provider/account state before retrying an ambiguous order response.

### A3 — bootstrap + application deployment

`NOT_GRANTED`

Requires explicit approval after the new VPS identity, IP, status and access method are verified.

Mutation scope is limited to the newly provisioned VPS. It does not authorize shared-hosting, mail, existing VPS, production website, Nextcloud, registrar or unrelated provider changes.

### A4 — DNS publication

`NOT_GRANTED`

Requires a separate DNS approval for exactly one hostname after the application is healthy on the VPS and the intended public hostname is confirmed.

Candidate only:

```text
tasks.cyberdjs.org -> <new VPS public IP>
```

No apex, `www`, MX, mail, staging or unrelated record mutation is implied.

## Phase 1 — repository implementation

Deliverables before provider mutation:

1. VPS plan schema with fail-closed default state;
2. sanitized InterServer catalog fixture;
3. quote validator with hard budget ceiling;
4. order approval-packet schema;
5. duplicate-service/idempotency guard design;
6. bootstrap MOP;
7. deployment compose template using placeholders/secret aliases only;
8. health/effect verifier;
9. rollback/restore checklist;
10. evidence-receipt schema;
11. tests proving no provider mutation can occur in plan-only mode.

## Phase 2 — live read-only catalog and quote

A1 is authorized. The authenticated catalog read is verified from the operator Mac; the remaining A1 operation is the documented non-mutating `PUT /apiv2/vps/order` quote.

Current authenticated catalog candidate:

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
budget_ceiling_usd_month: 3.00
catalog_price_usd_month: 3.00
ram_mib: 2048
disk_gib: 40
transfer_gib: 2000
quantity: 1
```

Live quote passes only when:

- configuration validates;
- quoted recurring amount is <= USD 3.00/month;
- no unexpected one-time charge exceeds the separately approved amount;
- response matches KVM / 1 slice / Ubuntu 24 / no control panel / one month / location 1;
- response is sanitized before evidence storage;
- no order or payment occurred.

If any requirement fails, return `BLOCKED` with evidence and do not auto-upsize or spend more.

## Phase 3 — purchase and provisioning

Blocked until A2.

Safety invariants:

```text
max_new_vps_count: 1
max_recurring_cost_usd_month: 3.00
provider_order_allowed: false until explicit approval
billing_payment_allowed: false until explicit approval
unrelated_provider_mutation_allowed: false
```

Before any purchase request, run the separately authorized read-only current-VPS inventory check and stop for reuse review if an existing VPS is potentially suitable.

After purchase, poll only the newly created service until one of:

- `active` -> continue to verification;
- terminal failure -> stop;
- timeout -> stop and preserve state for review.

An ambiguous provider response must not be blindly retried.

## Phase 4 — Linux bootstrap and hardening

Blocked until A3.

Planned baseline:

- verify host fingerprint before first managed SSH session;
- use a dedicated administration/deploy account;
- install an operator-approved SSH public key;
- disable password SSH authentication after key access is verified;
- disable direct root SSH login after recovery access is verified;
- patch the OS before application deployment;
- enable automatic security updates if the package state supports them safely;
- firewall default-deny inbound with only required SSH/HTTP/HTTPS exposure;
- install Docker Engine and Compose plugin from an approved source;
- keep application secrets out of Git, chat, Drive, Slack, CASER documents and ordinary evidence;
- record package/runtime versions and non-secret host facts.

No hardening step may lock out the operator without a tested fallback path.

## Phase 5 — Vikunja deployment

Blocked until A3.

Planned application contract:

- exact Vikunja version/digest pinned;
- Caddy version/digest pinned;
- one dedicated Docker network;
- Vikunja port not exposed publicly except through Caddy;
- persistent files/db directories under `/srv/vikunja`;
- SQLite MVP database stored persistently;
- registration enabled only for initial bootstrap, then disabled after intended accounts are created unless explicitly kept open;
- secure public URL configured before normal use;
- restart policy enabled;
- container health/status verification recorded;
- no plaintext application secrets committed to the repository.

## Phase 6 — attention-friendly workflow bootstrap

The initial UX should remain intentionally small. Do not preload a giant productivity ontology.

Minimal structure:

```text
INBOX
TODAY
THIS WEEK
LATER
```

Initial rules:

- `TODAY` should contain at most three primary tasks;
- every actionable item should have one visible next action;
- items that are not actionable today go back to `THIS WEEK` or `LATER`;
- capture is allowed to be messy in `INBOX`; organization happens later;
- no mandatory priority matrix, story points or enterprise Scrum ceremony in the MVP.

Suggested lightweight labels:

```text
5-min
15-min
deep
waiting
low-energy
```

These are workflow defaults, not medical claims. The user may change them after first-use testing.

## Phase 7 — CyberCore integration

Vikunja's documented REST API is the preferred first integration boundary.

Initial CyberCore capabilities should be provider-neutral:

```text
tasks.list
tasks.create
tasks.update
tasks.complete
projects.list
inbox.capture
today.plan
```

The adapter must target Vikunja's current API v2 for new integration work after exact-version verification.

MCP may be evaluated later, but the MVP must not depend on a third-party MCP server when direct API integration is sufficient.

## Verification contract

A successful MVP requires evidence for:

- exactly one intended VPS exists;
- actual monthly price matches the approved quote;
- VPS status is active;
- SSH host identity is verified;
- OS/runtime versions are recorded;
- firewall exposes only approved ports;
- Vikunja responds successfully through the intended verifier;
- data survives container restart;
- a backup can be created;
- restore procedure is documented and tested before the service is treated as durable;
- registration policy matches the approved state;
- no plaintext secrets entered ordinary evidence;
- CyberCore can perform at least one read-only Vikunja API call after the integration credential is separately created and approved.

## Rollback / stop conditions

Stop immediately when:

- quote exceeds USD 3.00/month without new approval;
- provider returns an access/security response that would require security-control mutation or bypass to proceed;
- order response is ambiguous;
- more than one new VPS appears;
- provider behavior differs materially from reviewed documentation;
- credentials could leak into evidence;
- SSH host identity is ambiguous;
- bootstrap risks operator lockout;
- application persistence cannot be verified;
- DNS target is ambiguous;
- any step would touch existing shared-hosting production, mail, Nextcloud, existing VPS or unrelated provider resources.

Rollback is phase-specific and must be defined before each mutation. Deleting/canceling a paid VPS is itself a provider mutation and is never inferred from a failed deployment.

## Exit criteria

WB-0035 planning is ready for A1 completion when:

- repository-only schemas/validators/tests exist;
- no provider or billing mutation path is reachable from plan-only mode;
- current provider docs are linked and the required API operations are semantically reviewed;
- the Vikunja deployment design is reproducible and secret-safe;
- the budget ceiling is machine-enforced;
- the approval packet can distinguish quote, purchase, bootstrap and DNS authorities;
- authenticated catalog evidence is VERIFIED;
- the remaining A1 quote succeeds without spend or mutation;
- current VPS inventory is inspected under a separately explicit read-only authorization before any A2 purchase decision.
