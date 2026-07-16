# CyberCore Terminology

CyberCore uses a small controlled vocabulary.

## Core terms

- **Reality** — the actual state of systems and services.
- **Observation** — a measured or recorded view of reality.
- **Evidence** — reproducible data supporting a claim.
- **Knowledge** — interpreted evidence with context and provenance.
- **Confidence** — an explicit assessment of certainty and assumptions.
- **Decision** — a chosen action with rationale and consequences.
- **Specification** — an implementation-independent definition of expected behavior.
- **Knowledge Block (KB)** — a durable unit capturing problem, evidence, interpretation, decision, and consequences.
- **Work Block (WB)** — a coherent implementation unit with scope, verification, rollout, and outcome.
- **Provider** — an adapter exposing infrastructure capabilities and observations through a stable interface.
- **Runtime** — the local execution environment that validates and applies approved Work Blocks.
- **Transport** — a replaceable mechanism used to move Work Blocks; it never defines workflow semantics.
- **Exchange** — the transport-agnostic workflow for publishing, validating, staging, and applying Work Blocks.
- **Capability** — a user-visible or operationally meaningful function delivered by CyberCore.

Terms must be used consistently across code, documentation, issues, and reviews.