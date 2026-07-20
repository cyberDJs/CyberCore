# CyberCore Structured Registry

This directory is the machine-readable, sanitized inventory entry point for CyberCore.

## Files

- `schema.yaml` defines allowed entity types, statuses, classifications, relationships, and the minimum record contract.
- `inventory.yaml` contains the initial verified inventory and an explicit queue of unknowns.

## Operating rules

1. Record verified reality, not assumptions.
2. Every record must include evidence and `last_reviewed`.
3. Unknown values remain `unknown` or `null`; they are never guessed.
4. Secrets are never stored here. Use references to an approved secret manager or private overlay.
5. Public or shared documentation must contain sanitized topology only.
6. A production-changing automation may consume registry data only after schema validation and human approval.

## How to add an item

Copy `record_template` from `schema.yaml`, assign a stable ID, select an allowed entity kind and status, add evidence, then link it through explicit relationships.

Example:

```yaml
- id: "ASSET-EXAMPLE-001"
  kind: "asset"
  subtype: "vps"
  name: "Example VPS"
  status: "active"
  owner: "CyberCore"
  classification: "public-sanitized"
  description: "Sanitized description of the resource."
  relationships:
    - type: "hosted_by"
      target: "PROVIDER-EXAMPLE-001"
  evidence:
    - type: "provider-console"
      reference: "sanitized-evidence-reference"
      confidence: "high"
  last_reviewed: "2026-07-20"
```

## Current coverage

The initial registry records:

- InterServer shared hosting;
- the InterServer Slice VPS;
- `eimyherrer.com`;
- `cloud.eimyherrer.com`;
- website, mail, and Nextcloud services;
- the CyberCore repository and project.

The `unknowns` section is deliberate. It is the actionable discovery queue for missing infrastructure facts, including VPS workloads, backup evidence, monitoring, domains, databases, mailboxes, certificates, and cron jobs.

## Intended outputs

The registry is designed to later generate:

- human-readable inventory documentation;
- monitoring targets;
- maintenance and expiry checks;
- security review queues;
- Asana operational work items;
- AI context with explicit confidence and evidence.
