# WB-VIKUNJA-001 — Current-main Vikunja/VPS plan reset

Date: 2026-10-06
Repository: `cyberDJs/CyberCore`
Base: `main@b2ef9088728930707cd9bad3dd5cd33e855c5480`
Status: `DRAFT — REPOSITORY-ONLY PLAN RESET`

## Purpose

Restart the `tasks.cyberdjs.org` Vikunja/VPS work from the current canonical `main` after the historical PR #61 plan was closed as stale and high risk.

This work block exists to define a clean, reviewable path forward before any provider, payment, SSH, DNS, or deployment action is considered.

## Explicit non-authority

This document and the WB-VIKUNJA-001 branch do not authorize or perform:

- InterServer API calls;
- provider contact;
- VPS order creation;
- invoice creation;
- PayPal or any other payment initiation;
- SSH connection or remote host mutation;
- DNS mutation;
- application deployment;
- credential creation, exposure, rotation, or storage changes;
- merge to `main`.

Any future action outside repository planning requires a fresh explicit approval bound to the current head, exact scope, and rollback/abort criteria.

## Background

Historical PR #61 attempted to prepare an InterServer VPS + Vikunja ADHD task-management MVP plan. It is now closed/unmerged and retained only as historical evidence. Its old A2 order/payment authorization text is not current authority for any provider, payment, VPS, DNS, SSH, deployment, or credential action.

The restart point is current canonical `main@b2ef9088728930707cd9bad3dd5cd33e855c5480`, after the PR #99 and PR #100 cleanup sequence.

## Desired outcome

A safe current-main plan for a small `tasks.cyberdjs.org` task-management service, with gates that keep exploration, provider contact, ordering, payment, provisioning, DNS, and deployment separated.

The system should eventually support:

- one clearly identified target hostname;
- one selected hosting/provisioning approach;
- explicit cost ceiling before any paid action;
- pinned deploy artifacts before any runtime use;
- known rollback path before cutover;
- independent verification after every consequential step.

## Gate model

The work is split into gates. Passing one gate never grants the next gate.

| Gate | Name | Allowed at this PR | Requires fresh approval later |
|---|---|---:|---:|
| A0 | Current-main planning reset | yes | no |
| A1 | Read-only option discovery plan | plan only | yes, before external calls |
| A2 | Provider quote / order / payment plan | plan only | yes, before quote/order/payment |
| A3 | Provisioning / SSH / bootstrap plan | plan only | yes, before SSH or host mutation |
| A4 | DNS / cutover / production plan | plan only | yes, before DNS or production cutover |

## A0 — repository planning reset

Allowed in this PR:

- record PR #61 closure inheritance;
- define new gate boundaries;
- identify required evidence before any later provider or deployment phase;
- prepare runbook skeletons and stop lines.

Not allowed in this PR:

- provider calls;
- live price checks;
- account inventory reads;
- order/payment workflow execution;
- SSH, DNS, or deploy actions.

## A1 — discovery plan, not execution

A1 will be a later separately approved read-only discovery phase. It may include comparing options such as:

- existing available CyberDJS infrastructure;
- current VPS providers;
- container-only deployment;
- managed task app alternatives;
- self-hosted Vikunja on a small VPS;
- deferring paid infrastructure if an existing host is sufficient.

A1 must not inherit historical PR #61 quotes or inventory as current truth. Any future external price or provider evidence must be fresh and cited in a new evidence record.

## A2 — provider quote / order / payment plan, not execution

A2 is blocked until A1 produces current evidence and the operator explicitly approves a current exact envelope.

Minimum A2 preconditions:

- exact provider and product selected;
- exact recurring and one-time cost ceilings recorded;
- exact location/region decision recorded when applicable;
- fresh provider quote or cart semantics verified;
- duplicate-service guard designed;
- payment method explicitly selected;
- all P1/P2 review findings resolved or explicitly waived with rationale;
- clear abort rule for ambiguous responses or timeouts.

No historical A2 language from PR #61 can be reused as current permission.

## A3 — provisioning / SSH / bootstrap plan, not execution

A3 is blocked until any provider account state is known, any paid resource exists by explicit approval, and a host-specific bootstrap plan is reviewed.

Minimum A3 preconditions:

- target host identity confirmed;
- access method approved;
- no plaintext secret exposure in repository or chat;
- pinned container image digests or equivalent immutable artifact references;
- service secret handling specified under the correct application keys;
- backup/restore and rollback plan written before deployment;
- validation commands and expected outputs written before execution.

## A4 — DNS / cutover / production plan, not execution

A4 is blocked until A3 is verified and a DNS/cutover plan exists.

Minimum A4 preconditions:

- current DNS source of truth identified;
- exact records and TTLs planned;
- rollback DNS values known;
- TLS/certificate behavior understood;
- health checks defined;
- operator approves exact DNS mutation and cutover window.

## Review expectations

Before any merge or further gate transition, reviewers should verify:

- the PR contains docs only;
- no code or deployment assets are introduced;
- no provider/payment authority is implied;
- PR #61 is referenced only as historical non-authority;
- gates are explicit and separable;
- every future external or consequential action requires a fresh approval.

## Current recommendation

Keep this PR as draft until the docs-only scope is verified. After merge, start A1 as a separate read-only discovery work block only if the operator gives a fresh approval that explicitly allows external research or connector reads.
