# LG-0001 — Read-Only Source-of-Truth Reconciler

Status: Experimental candidate  
Date: 2026-08-19

## Purpose

Prove that LangGraph can orchestrate a useful CyberCore workflow without becoming a source of
truth or gaining mutation authority.

LG-0001 consumes normalized source snapshots and known remediation metadata. Provider-specific
collection remains outside the graph. This keeps GitHub, Google Drive and future adapters behind
CyberCore's provider and provenance boundaries.

## Input contract

Each source snapshot contains:

- `source_id` — stable observation reference;
- `authority` — `CANONICAL`, `EVIDENCE`, or `WORKING`;
- `facts` — normalized scalar facts keyed by a stable fact identifier.

Known remediation contains:

- `id` — remediation reference such as `PR#38`;
- `state` — `OPEN` or `CLOSED`;
- `target_keys` — fact keys the remediation is intended to reconcile.

No secret values are valid inputs.

## Graph

```text
START
  -> resolve_authority
  -> compare_observations
  -> detect_existing_remediation
  -> finalize
  -> END
```

The graph is deterministic. LG-0001 has no LLM node, tool node, network node or write node.

## Classification

- `CURRENT` — canonical facts and overlapping lower-authority observations agree.
- `DRIFT` — a lower-authority observation disagrees with canonical facts.
- `CONFLICT` — explicitly canonical sources disagree on the same fact; fail closed.
- `UNKNOWN` — no canonical source is available.

## Recommendation

- `NO_ACTION`
- `OBSERVE_EXISTING_REMEDIATION`
- `PROPOSE_REMEDIATION`
- `ESCALATE_AUTHORITY_CONFLICT`
- `REQUEST_MORE_EVIDENCE`

A recommendation is not authorization and never performs the proposed action.

## Regression scenario

The initial acceptance fixture models the observed CyberCore sequence:

1. GitHub reports PR #37 merged.
2. `PROJECT_STATE.md` still reports PR #37 open.
3. PR #38 is already open to reconcile that exact state.
4. LG-0001 must report `DRIFT` plus `OBSERVE_EXISTING_REMEDIATION` rather than recommend a second PR.

## Non-goals

- fetching GitHub or Drive directly;
- accepting an ADR;
- changing `PROJECT_STATE.md`;
- opening or merging pull requests;
- persistence/checkpointing;
- human interrupts;
- autonomous remediation.

Those are separate slices and require their own value, architecture and authorization gates.

## Removal path

Delete the optional orchestration module, its tests and the `orchestration` dependency extra.
No canonical CyberCore data model, provider contract or persisted format depends on LG-0001.
