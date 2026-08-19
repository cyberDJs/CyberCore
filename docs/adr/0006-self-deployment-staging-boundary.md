# ADR-0006 — Self-Deployment Staging Boundary

Status: Proposed
Date: 2026-08-19
Work block: `WB-0028`
Renumbered from: `ADR-0005` after post-merge identifier collision with the accepted LangGraph ADR

## Context

CyberCore is moving toward controlled self-development and self-deployment. The operator selected a complete self-development loop and InterServer shared hosting as the first staging target.

Autonomous deployment increases risk because a system that can change itself can also damage its own source of truth, evidence trail, or production environment if the authority boundary is weak.

PR #39 originally introduced this proposal as `ADR-0005`. PR #40 independently established and accepted `ADR-0005 — LangGraph as Optional Orchestration Runtime`. After both branches landed, the repository contained two ADRs with the same identifier. This document is renumbered to `ADR-0006`; the self-deployment decision content is otherwise unchanged.

## Decision proposal

CyberCore self-deployment must start with a staging-only boundary.

The permitted v0 loop is:

```text
branch -> tests -> PR -> staging plan -> explicit operator authorization -> staging deploy -> effect verification -> evidence receipt
```

Production promotion is explicitly outside this ADR candidate and remains blocked by separate human approval, MOP, backup/restore readiness, and effect verification.

## Rules

- Staging target metadata may be stored in GitHub only if it contains no secret values.
- Secret values may only exist in approved secret storage.
- Deployment receipts may store aliases, hashes, commit ids, target ids, timestamps, and verification states, but never plaintext secrets.
- First remote write to InterServer staging requires explicit operator authorization.
- Production, DNS, mail, billing, DirectAdmin, VPS, WordPress, and Nextcloud mutations are outside the self-deploy v0 authority.
- Staging success is not production approval.

## Consequences

Positive:

- CyberCore can start evolving toward self-deployment without unsafe production authority.
- Deployment evidence and rollback become first-class artifacts.
- The staging boundary is clear enough to automate later.

Tradeoffs:

- The first slice is slower because target capability and rollback must be verified first.
- InterServer shared-hosting limitations may force fallback from atomic symlink deployment to backup/no-overwrite deployment.
- Production automation remains deliberately blocked.

## Acceptance

This ADR is only proposed. It is not accepted until Jan Kočí explicitly accepts it or a later approved governance workflow marks it accepted.
