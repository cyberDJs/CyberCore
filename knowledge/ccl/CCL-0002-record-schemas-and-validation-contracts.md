---
id: CCL-0002
type: language-specification
title: CyberCore Canonical Language — Record Schemas and Validation Contracts
status: draft
version: 0.1.0
owner: CyberCore
created: 2026-07-28
updated: 2026-07-28
requires:
  - CCL-0001
---

# CCL-0002 — Record Schemas and Validation Contracts

## 1. Purpose

CCL-0002 converts the vocabulary from CCL-0001 into versioned machine-readable contracts. It defines the common record envelope, validation levels, compatibility rules, and the first Evidence Runtime schemas.

## 2. Contract principles

1. Every canonical record declares its schema version.
2. Validation is deterministic and must not depend on an AI model.
3. Unknown properties are rejected in kernel records unless a schema explicitly permits an extension area.
4. Provider payloads remain outside the kernel until normalized.
5. Timestamps use RFC 3339 UTC form.
6. Identifiers are opaque strings and must not contain secrets.
7. References are identifiers, not embedded mutable objects, unless a schema explicitly defines a snapshot.
8. Validation failure never silently repairs or invents data.
9. Backward compatibility is evaluated at the schema boundary.
10. Public validation fixtures must be synthetic or sanitized.

## 3. Validation levels

### Syntax validation

Checks JSON/YAML structure, primitive types, required fields, enumerations, formats, and forbidden additional properties.

### Semantic validation

Checks domain invariants that cannot be expressed safely in JSON Schema alone, including:

- `recorded_at >= observed_at`,
- referenced records exist,
- referenced record types are compatible,
- confidence level agrees with score range,
- a plan revision matches its approval,
- an Apply Result references an approved plan,
- verification observations occur after mutation execution.

### Governance validation

Checks policy and authorization boundaries, including:

- classification rules,
- secret detection,
- approval requirements,
- actor authorization,
- mutation scope,
- evidence freshness requirements.

## 4. Common record envelope

All kernel records use the common envelope defined by:

```text
schemas/ccl/v1/common-record.schema.json
```

Required fields:

- `id`
- `type`
- `schema_version`
- `created_at`
- `created_by`
- `classification`
- `attributes`
- `relationships`

Optional correlation fields:

- `correlation_id`
- `causation_id`
- `tenant_id`

The `attributes` object is specialized by each record schema.

## 5. Initial schema set

The first schema slice contains:

```text
schemas/ccl/v1/common-record.schema.json
schemas/ccl/v1/observation.schema.json
schemas/ccl/v1/evidence.schema.json
```

This slice establishes the entry boundary of the Evidence Runtime:

```text
external source -> Observation -> Evidence
```

## 6. Observation contract

An Observation records what was collected, when, from where, and by which method. It may contain raw or minimally normalized data, but it must not assert domain truth.

Semantic invariants:

1. `observed_at` is required.
2. `source_id` is required.
3. `collection_method` is explicit.
4. Payload integrity may be recorded before transformation.
5. Rejected observations remain auditable; they are not deleted.

## 7. Evidence contract

Evidence is derived from exactly one primary Observation in this initial schema version. Future schemas may permit composite evidence while preserving complete provenance.

Semantic invariants:

1. Evidence references its source Observation.
2. `recorded_at` cannot precede `observed_at`.
3. Integrity status is explicit.
4. Freshness state is explicit.
5. Classification cannot be less restrictive than the source Observation without an approved sanitization transformation.
6. Evidence content is immutable after creation.

## 8. Versioning

Schema identifiers use semantic major versions in their path:

```text
schemas/ccl/v1/...
```

Rules:

- additive optional fields may be introduced within the same major version;
- newly required fields require a new major version;
- changed meaning requires a new major version;
- enum removal requires a new major version;
- enum addition requires compatibility review;
- old schemas remain available for historical record validation.

Canonical `schema_version` for this slice:

```text
ccl/1.0
```

## 9. Extension mechanism

Kernel schemas reject arbitrary additional properties. Controlled extensions belong only in:

```json
"extensions": {
  "namespace.example": {}
}
```

Extension namespaces must be globally unique within CyberCore and must not redefine canonical fields.

## 10. Validation result

Validators return a structured result:

```yaml
valid: false
schema_id: cybercore://schemas/ccl/v1/evidence
record_id: cybercore:evidence:example
errors:
  - code: required_field_missing
    path: /attributes/source_id
    message: source_id is required
warnings: []
validated_at: 2026-07-28T00:00:00Z
validator_version: string
```

Validation output is evidence about validation execution, but it is not automatically domain Evidence unless ingested through the Evidence Runtime.

## 11. Conformance

An implementation conforms to CCL-0002 when it:

1. validates records against the declared schema before kernel ingestion;
2. performs required semantic checks;
3. preserves rejected input for audit according to classification policy;
4. never mutates an accepted Evidence record in place;
5. identifies validator and schema versions;
6. rejects undeclared kernel properties outside the extension mechanism.

## 12. Next slice

- Entity schema
- Claim schema
- Relationship schema
- Confidence schema
- Contradiction schema
- Knowledge State schema
- reference resolver contract
- semantic validator test fixtures
