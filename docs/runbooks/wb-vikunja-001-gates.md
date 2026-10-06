# WB-VIKUNJA-001 — Gate runbook

Date: 2026-10-06
Base work block: `WB-VIKUNJA-001`
Scope: current-main planning reset for `tasks.cyberdjs.org`

## Hard stop

This runbook is a planning artifact. It does not authorize execution.

Until a later explicit approval says otherwise, the following remain prohibited:

- provider calls;
- payment or invoice action;
- order creation;
- account security or credential mutation;
- SSH or remote host mutation;
- DNS change;
- application deployment;
- production cutover.

## Gate principles

1. Each gate has one purpose.
2. Evidence from an older branch or closed PR is historical unless revalidated.
3. External state must be checked fresh immediately before any consequential action.
4. Approval must bind the exact operation, exact head, exact target, and exact limits.
5. Ambiguous or timed-out consequential operations are not retried automatically.
6. No secret values may be written to repository files, PR bodies, comments, logs, or ordinary evidence.

## A0 — current-main plan reset

### Allowed

- Create a docs-only branch from current `main`.
- Record PR #61 as closed historical non-authority.
- Define gate boundaries.
- Prepare evidence and review expectations.

### Required evidence

- current main commit;
- branch name;
- created file list;
- draft PR number;
- verification that the diff is docs-only.

### Completion criteria

- draft PR exists;
- changed files are limited to `docs/plans/`, `docs/runbooks/`, and `docs/evidence/`;
- PR body states no provider/payment/deploy authority;
- no provider or payment call occurred.

## A1 — read-only discovery

A1 must be opened as a separate approval after A0.

### Possible scope

- compare current deployment options;
- inspect existing repository docs and historical evidence;
- perform public web research if approved;
- optionally perform read-only account/provider inventory only if explicitly approved and scoped.

### Must not do without explicit approval

- authenticate to InterServer or any provider;
- read billing/account inventory;
- create carts, orders, invoices, tickets, or payments;
- change DNS, SSH, credentials, or remote systems.

### Output

- options matrix;
- cost and risk assumptions;
- recommended target path;
- required approvals for A2/A3/A4;
- stale-evidence list.

## A2 — quote, order, payment envelope

A2 is split into sub-gates. They must not be collapsed.

### A2-Q — current quote discovery

Requires fresh approval before any provider read or quote call.

Minimum output:

- exact provider endpoint/action used;
- whether the action is read-only or non-mutating;
- exact candidate configuration;
- exact returned price fields;
- modeled recurring and one-time costs;
- explicit statement that no order/invoice/payment occurred.

### A2-O — order creation

Requires a later explicit approval bound to:

- exact provider;
- exact product/configuration;
- exact maximum recurring price;
- exact maximum one-time charge;
- exact quantity;
- duplicate-service guard;
- no automatic retry rule;
- abort conditions.

### A2-P — payment

Requires a later explicit approval bound to:

- exact invoice or payment request;
- exact amount;
- exact payment method;
- exact ownership relation to the intended service;
- no unrelated prepay/account/security changes.

## A3 — provisioning and bootstrap

Requires current target host state and a host-specific runbook.

### Required before execution

- host identifier and network access path;
- access authorization and credential handling plan;
- immutable image/artifact references;
- service secret strategy;
- backup and rollback procedure;
- validation commands;
- stop conditions.

### Default stop conditions

- unexpected existing service on the host;
- image reference is mutable;
- secret path or application key is ambiguous;
- SSH identity or target host does not match the approval;
- any command output differs from expected safety preconditions.

## A4 — DNS and cutover

Requires A3 verified and a DNS-specific approval.

### Required before execution

- DNS provider/source of truth;
- current record snapshot;
- target record set;
- TTL plan;
- TLS/certificate behavior;
- health check and rollback values;
- cutover window and abort rule.

## Review checklist for WB-VIKUNJA-001 PR

- [ ] Branch is based on `main@b2ef9088728930707cd9bad3dd5cd33e855c5480` or a later explicitly approved current-main commit.
- [ ] Diff is docs-only.
- [ ] PR #61 is referenced only as historical non-authority.
- [ ] No old A2 authorization is treated as current.
- [ ] A0/A1/A2/A3/A4 gates are separated.
- [ ] No provider/payment/DNS/SSH/deploy operation is described as already approved.
- [ ] Future execution requires fresh explicit approvals.

## Rollback

For A0 repository-only work, rollback is to close the draft PR or revert the docs-only commit. No external state should exist to clean up.
