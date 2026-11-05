# CASER v4.1 — safe handoff inspection and resume policy

Status: opt-in candidate. Tracks CyberCore #136.

This library defines a **non-authoritative** immutable handoff snapshot, a
pure validation function, and structured reasons. It does not access GitHub,
execute recovery commands, persist records, authorize tasks, or replay writes.

## State and source contract

Each handoff records a scoped `run_id`, canonical repository, exact source SHA,
transaction state, completed/pending action identifiers, open side effects,
last verified step, and evidence references. A future trusted adapter must read
these fields from a versioned source and authenticate the record's provenance.
The caller must independently read current GitHub/canonical state and supply
that actual SHA. Never copy the handoff SHA into `current_sha` without querying
the provider.

A matching clean `PLANNED` state yields `READONLY_RECONCILE`: a prompt to run
fresh discovery and preflight, **not** permission to execute. Changed repository
state yields `REPLAN_REQUIRED` **only when no mutation remains unresolved**.
Any `ACTIVE`, `VERIFYING`, `COMPENSATING`, `PARTIAL` or open side effect blocks
replanning until its actual outcome is independently reconciled, even if the
canonical source SHA has changed. Invalid identities/state also block.
Likewise, `FAILED` or `BLOCKED` remains `BLOCKED` across source drift;
`COMMITTED` and `ROLLED_BACK` remain `READONLY_RECONCILE` with mandatory
`TERMINAL_RUN_VERIFY_EFFECT` before any further action, even if the SHA moved.
Only a clean, non-terminal plan can receive `REPLAN_REQUIRED` on drift.

Never infer success from a receipt alone. A separate authorization gate,
external effect validation, rollback authority and independent verification
remain mandatory for consequential steps.

## Threat model

- A crafted handoff cannot grant authority (no execution API).
- A valid-looking snapshot can still be forged: independent provenance checks
  are required at the storage adapter.
- Duplicate action receipts and pending/completed conflicts are rejected.
- Drift cannot silently replay a write; it forces a new plan.
- A former approval may be stale when the artifact or provider state changes.
- The handoff stores identifiers and references, not credentials or secret data.

## Integration / rollback

Optional pure module only. Do not enable automatic continuation, schedules or
production writes based on its result. Keep existing CASER skill governance and
SandCloud transaction records authoritative until validated integration.
Rollback is to stop importing this module; no migrations or data are changed.

## Verification

Regressions cover source drift, run/repository substitution, incomplete active
transactions, ambiguous mutation effects, duplicate and conflicting receipts,
invalid SHA/states and conservative terminal-state handling.
