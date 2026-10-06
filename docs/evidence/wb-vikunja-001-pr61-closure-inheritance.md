# WB-VIKUNJA-001 — PR61 closure inheritance

Date: 2026-10-06
Repository: `cyberDJs/CyberCore`
New work block: `WB-VIKUNJA-001`
Historical source: PR #61 `docs(wb0035): plan InterServer VPS + Vikunja ADHD MVP`

## Status

PR #61 is closed and unmerged. It is retained only as historical planning evidence.

The old PR #61 A2 text must not be interpreted as current authority for any external or consequential action.

## Closure facts to inherit

The new work block inherits only these facts:

- PR #61 existed as historical WB-0035 planning work.
- PR #61 targeted `tasks.cyberdjs.org` and a Vikunja/VPS concept.
- PR #61 was closed as stale/high-risk after current-main cleanup.
- PR #61 contained unresolved review findings in provider, quote, payment, YAML, money, image-pinning, and deployment safety areas.
- PR #61 contains historical evidence that may help write new requirements, but it is not source-of-truth for current provider state or current approval.

## Non-authority explicitly inherited

The new work block preserves the closure stop-line:

- no provider calls are authorized;
- no payment is authorized;
- no order or invoice creation is authorized;
- no SSH or VPS mutation is authorized;
- no DNS mutation is authorized;
- no application deployment is authorized;
- no branch revival is authorized;
- no old A2 approval text is reusable as current permission.

## Required fresh evidence for any future phase

Before any future phase can proceed beyond documentation, it must collect or produce fresh current-main evidence:

| Future phase | Required fresh evidence |
|---|---|
| A1 discovery | current option list, assumptions, risks, and allowed data sources |
| A2 quote/order/payment | current provider/product/price/inventory/payment evidence and exact approval envelope |
| A3 provisioning | current target host, access path, bootstrap plan, secret handling, rollback, and verification commands |
| A4 DNS/cutover | current DNS source of truth, record snapshot, target records, TLS/health plan, rollback values |

## Review-risk inheritance from PR61

A new plan must explicitly avoid the historical risk classes from PR #61:

- secret-bearing values hidden in YAML, decoded scalars, quote references, or provider JSON;
- binary-float or YAML numeric parsing changing money values;
- provider quote responses with ambiguous or conflicting price fields;
- missing exact location and hostname binding;
- accepting mutable container image tags where pinned immutable references are required;
- incorrect application secret configuration keys;
- proceeding from stale inventory into an order;
- conflating quote, order, invoice, payment, SSH, DNS, and deploy authority.

## Current-main reset rule

WB-VIKUNJA-001 starts from current canonical `main@b2ef9088728930707cd9bad3dd5cd33e855c5480` and does not revive the old PR #61 branch.

A later implementation branch may borrow ideas from historical PR #61 only after revalidating them against current main and current external truth.

## Evidence statement

This file is repository-only evidence. It contains no secrets, no provider credentials, no live quotes, no invoices, no payment records, no DNS records, and no deployment output.
