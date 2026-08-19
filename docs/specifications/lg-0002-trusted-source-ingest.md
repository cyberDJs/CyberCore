# LG-0002 — Trusted GitHub / Google Drive Source Ingest

Status: Candidate  
Date: 2026-08-19  
Depends on: ADR-0005 (Accepted), LG-0001

## Purpose

LG-0002 closes the trust gap between provider observations and LG-0001. Provider payloads may
contain useful facts and metadata, but they do not get to declare their own authority. A trusted
CASER-SOURCER binding layer assigns `CANONICAL`, `EVIDENCE`, or `WORKING` only after an exact
provider locator match.

The workflow remains read-only. It performs no GitHub or Google Drive API calls itself and has
no provider write, LLM, secret, remediation, deployment, or approval node. Connected provider
adapters collect metadata outside the graph and pass normalized observations into LG-0002.

## Trust model

```text
GitHub / Google Drive connector result
        |
        v
ProviderObservation  -- no authority field
        |
        v
trusted CASER-SOURCER bindings
        |
        +-- exact one match --> SourceSnapshot + provenance
        |
        +-- zero / many / invalid --> UNKNOWN (fail closed)
        |
        v
LG-0001 reconciler
        |
        v
CURRENT | DRIFT | CONFLICT | UNKNOWN
```

Authority is resolved before freshness. `observed_at` is provenance only; a newer lower-authority
Drive observation cannot override GitHub canonical state.

## Provider observation contract

A provider observation contains:

- `source_id` — stable identity inside one reconciliation run;
- `provider` — `GITHUB` or `GOOGLE_DRIVE`;
- `locator` — provider metadata extracted by the trusted adapter, never document-body claims;
- `facts` — normalized scalar facts to reconcile;
- optional `observed_at`;
- optional `content_sha256`.

Provider observations intentionally contain **no authority field**.

### Safe locator keys

GitHub: `repository`, `ref`, `path`, `resource_kind`, `number`, `sha`.

Google Drive: `file_id`, `parent_id`, `ancestor_id`, `resource_kind`, `mime_type`.

Any other locator key is rejected before provenance capture. This prevents credentials or
arbitrary document content from being copied into orchestration provenance by accident.

## Trusted binding contract

A binding contains:

- `binding_id`;
- provider;
- assigned authority;
- exact locator fields in `match`.

Rules:

1. provider-wide empty matches are forbidden;
2. GitHub bindings must pin `repository`;
3. Google Drive bindings must pin `file_id`, `parent_id`, or `ancestor_id`;
4. duplicate binding IDs fail closed;
5. zero matching bindings means `UNBOUND`;
6. more than one matching binding means `AMBIGUOUS_BINDING`, even if both assign the same
   authority.

Example policy shape using placeholders rather than private Drive identifiers:

```yaml
bindings:
  - binding_id: github-main-files
    provider: GITHUB
    authority: CANONICAL
    match:
      repository: cyberDJs/CyberCore
      ref: main
      resource_kind: file

  - binding_id: caser-e-working
    provider: GOOGLE_DRIVE
    authority: WORKING
    match:
      ancestor_id: ${CASER_E_WORKING_FOLDER_ID}

  - binding_id: caser-e-evidence
    provider: GOOGLE_DRIVE
    authority: EVIDENCE
    match:
      ancestor_id: ${CASER_E_EVIDENCE_FOLDER_ID}
```

Private Drive IDs belong in trusted runtime configuration or an approved secret/configuration
store, not in the public CyberCore repository.

## Graph

```text
START
  -> bind_authority
      -> [BOUND]   reconcile (LG-0001)
      -> [UNKNOWN] fail_closed
  -> END
```

`fail_closed` returns `UNKNOWN + REQUEST_MORE_EVIDENCE`. Successfully bound observations are
still returned for diagnostics, but a partial binding set is never treated as complete truth.

## Provenance output

For every successfully bound source LG-0002 returns:

- source ID;
- provider;
- resolved authority;
- trusted binding ID;
- safe provider locator;
- optional observed timestamp;
- optional normalized SHA-256.

This is runtime provenance, not a persistence format. LG-0002 adds no checkpoint store; durable
provenance/evidence persistence is a later governed slice.

## CyberCore source policy observed during design

Current project evidence declares GitHub as canonical product state while Google Drive serves as
source/evidence/archive/working collaboration and contains an older repository mirror. CASER-E
currently has separate `working` and `evidence` folders. LG-0002 encodes that separation as a
binding capability, not as hard-coded private folder IDs.

## Acceptance criteria

LG-0002 is ready for merge when:

1. trusted exact-match binding works for GitHub and Google Drive observations;
2. unbound and ambiguous observations fail closed to `UNKNOWN`;
3. provider content cannot self-declare authority;
4. freshness cannot elevate lower-authority observations;
5. unsafe locator keys are rejected before provenance capture;
6. LG-0001 behavior remains unchanged;
7. real LangGraph execution, Python 3.11–3.14 tests, Ruff, Pyright, package build, and CodeQL pass;
8. no private Drive IDs or secret values are committed.

## Non-goals

- making network calls from LangGraph;
- storing Google Drive IDs in public canonical configuration;
- persisting graph checkpoints;
- automated remediation;
- GitHub or Drive writes;
- production mutation;
- policy/approval decisions.

## Removal path

Delete `source_binding.py`, `trusted_sot.py`, their tests, and this specification. LG-0001 remains
usable because the shared orchestration contracts are provider-independent.
