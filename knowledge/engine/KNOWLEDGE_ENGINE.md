# CyberCore Knowledge Engine v0

## Purpose

The Knowledge Engine turns raw operational observations into reusable, confidence-scored knowledge that can safely drive work and later automation.

```text
Observation -> Evidence -> Claim -> Confidence -> Relationship -> Decision -> Work
```

The engine is not an autonomous mutation layer. It prepares verified context and recommendations. Production-changing actions remain behind explicit human approval.

## Inputs

- structured registry objects;
- sanitized configuration extracts;
- GitHub issues, pull requests, ADRs, KBs and Work Blocks;
- Asana task state and operator notes;
- monitoring events and maintenance outcomes;
- human-confirmed observations.

## Core records

### Evidence
A traceable observation from a source at a specific time.

Required fields:

- `id`
- `source_type`
- `source_ref`
- `observed_at`
- `classification`
- `summary`
- `freshness`

### Claim
A statement inferred or directly observed from one or more evidence records.

Required fields:

- `id`
- `subject_ref`
- `predicate`
- `value`
- `evidence_refs`
- `confidence`
- `status`
- `review_after`

### Relationship
A typed edge between registered objects.

Examples:

- `runs_on`
- `depends_on`
- `served_by`
- `owned_by`
- `documented_by`
- `tracked_by`
- `supersedes`

### Decision candidate
A recommendation generated from verified claims. It is never applied automatically in v0.

Required fields:

- `id`
- `problem`
- `options`
- `recommended_option`
- `supporting_claims`
- `risk`
- `requires_human_approval: true`

## Confidence model

Confidence is stored as a decimal from `0.0` to `1.0`.

- `0.95-1.00`: directly verified from authoritative current evidence;
- `0.80-0.94`: strongly supported by multiple consistent sources;
- `0.60-0.79`: plausible but incomplete or aging evidence;
- `0.30-0.59`: weak assumption; discovery work required;
- `0.00-0.29`: unknown or contradicted; must not drive automation.

Confidence must decrease when evidence exceeds its review window.

## Safety rules

1. Secrets are referenced, never copied.
2. Private topology remains in the private overlay.
3. Claims without evidence cannot become decisions.
4. Contradictory claims remain visible until resolved.
5. No production mutation is allowed from a confidence score alone.
6. Every generated work item must link back to claims and evidence.

## v0 outputs

- resolved registry relationships;
- stale-evidence queue;
- contradiction queue;
- unknowns/discovery queue;
- decision candidates;
- GitHub issue payloads;
- Asana task payloads;
- human-readable knowledge summaries.

## Initial implementation boundary

v0 is file-backed and deterministic:

- YAML records in Git;
- schema validation in CI;
- no vector database requirement;
- no autonomous production writes;
- no hidden state outside versioned records and private evidence references.

## Acceptance criteria

- every claim validates against the schema;
- every claim references at least one evidence record;
- stale evidence is detectable;
- contradictions are represented, not overwritten;
- generated tasks include traceability links;
- public files contain no secret values or private topology.