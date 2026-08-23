# WB-0035 PRE-A2 — InterServer existing VPS inventory

Status: `AUTHORIZED — READ-ONLY INVENTORY PENDING EXECUTION`

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

## Safety handling

- execute from the operator Mac, where the authenticated InterServer GET/PUT contract already returned HTTP 200;
- load the API key from the existing macOS Keychain alias and never print it;
- save the raw inventory response only to a mode-0600 temporary file;
- first inspect response shape/field names without exposing values that may be sensitive;
- produce only sanitized inventory evidence;
- delete the temporary raw response after sanitization;
- stop immediately on non-200 transport, unexpected response shape, credential exposure risk or any requirement for a mutating endpoint.

## Current state

```yaml
PRE_A2_authorized: true
inventory_endpoint: GET /apiv2/vps
inventory_executed: false
inventory_verified: false
reuse_vs_new_decision: pending
provider_mutation_authorized: false
A2_purchase_authorized: false
A2_payment_authorized: false
A3_bootstrap_deploy_authorized: false
A4_dns_authorized: false
```

No provider request is claimed by this file yet. Runtime evidence will be added only after the authorized GET is executed and sanitized.
