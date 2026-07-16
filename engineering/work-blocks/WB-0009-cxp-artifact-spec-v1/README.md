# WB-0009 — CXP Artifact Specification v1

EPIC: **EPIC-002 — Artifact System**

## Goal

Freeze the first stable artifact contract before implementing Publisher,
Registry, signing or encrypted transport.

## Delivered

- CXP/1 specification;
- ADR-0004;
- manifest JSON Schema;
- metadata JSON Schema;
- valid reference examples;
- deterministic packaging rules;
- content-addressed identity model;
- signature and encryption boundaries;
- compatibility and security rules.

## Not delivered

- Publisher implementation;
- Runtime `.cxp` reader;
- Ed25519 signing;
- age encryption;
- registry backend.

## Definition of Done

- [x] artifact layout defined;
- [x] canonical identity defined;
- [x] deterministic build rules defined;
- [x] trust and confidentiality separated;
- [x] schemas included;
- [x] examples included;
- [x] architecture decision recorded.

## Verification

```bash
python -m json.tool schemas/cxp-manifest-v1.schema.json >/dev/null
python -m json.tool schemas/cxp-metadata-v1.schema.json >/dev/null
python -m json.tool examples/cxp/manifest.valid.json >/dev/null
python -m json.tool examples/cxp/metadata.valid.json >/dev/null
```

Optional schema validation:

```bash
python -m pip install jsonschema
jsonschema \
  -i examples/cxp/manifest.valid.json \
  schemas/cxp-manifest-v1.schema.json
jsonschema \
  -i examples/cxp/metadata.valid.json \
  schemas/cxp-metadata-v1.schema.json
```

## Rollback

Revert the WB-0009 commit. No runtime or production behavior is changed.
