# CyberCore

> **Infrastructure Context & Intelligence Platform**  
> Technical descriptor: **AI-first Infrastructure Control Plane**

CyberCore reduces uncertainty by turning operational reality into reusable knowledge, safer decisions, and controlled automation.

It begins as the control plane for the Eimy Herrer / CyberDJS infrastructure ecosystem. The first deployment target is **InterServer**: shared hosting, VPS, DirectAdmin, mail, DNS, WordPress, Nextcloud, and selected applications.

## Why CyberCore exists

Infrastructure usually fails long before the outage: ownership becomes unclear, decisions lose context, documentation drifts, and automation grows faster than understanding.

CyberCore is designed to answer:

- What exists?
- Why is it there?
- What changed?
- What evidence supports the current state?
- What is risky, obsolete, or unnecessarily expensive?
- What can be changed safely?
- What should remain under explicit human control?

> Technology serves people. Never the other way around.

## Core philosophy

CyberCore exists to reduce uncertainty by turning operational knowledge into reusable intelligence.

Its decision model is:

```text
Reality -> Evidence -> Knowledge -> Confidence -> Decision -> Automation
```

Its operating principles are:

1. Know what exists.
2. Understand why it is there.
3. Keep only what creates value.
4. Automate only what is understood.
5. Complexity is guilty until proven useful.

## Architectural layers

```text
Foundation
    ↓
Knowledge and context
    ↓
Specifications
    ↓
Engineering and Work Blocks
    ↓
Runtime
    ↓
Providers
    ↓
Infrastructure operations
    ↓
New evidence and outcomes
```

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for the complete system map.

## Public Framework + Private Overlay

The public repository contains reusable framework code, specifications, schemas, tests, sanitized examples, and documentation.

Private overlays contain credentials, production-derived inventory, private topology, client data, and environment-specific configuration.

Private information must never be required for the public framework to remain understandable and testable.

## Engineering model

Critical changes follow:

```text
Observation
  -> Evidence
  -> Knowledge Block
  -> Decision
  -> Specification
  -> Work Block
  -> Verification
  -> Human approval
  -> Apply
  -> Outcome
```

Key record types:

| Prefix | Purpose |
|---|---|
| `ADR` | Architecture Decision Record |
| `RFC` | Proposal requiring discussion |
| `CXP` | CyberCore Exchange Protocol specification |
| `KB` | Knowledge Block: evidence, context, and decision rationale |
| `WB` | Work Block: implementation, verification, rollout, and rollback |
| `EPIC` | Large capability or program increment |

## Repository map

```text
foundation/              Stable principles and engineering models
docs/specifications/     Technical contracts, including CXP
engineering/work-blocks/ Traceable implementation units
knowledge/               Evidence, inventory, context, and generated knowledge
src/                     CyberCore implementation
providers/               Infrastructure adapters
runtime/                 Runtime and Exchange implementation assets
automation/              Supporting operational automation
monitoring/              Observability definitions and configuration
security/                Security guidance and hardening material
```

## Current milestone

**Foundation and Exchange Runtime Design Freeze**

The active design package defines:

- Foundation documents and terminology;
- the conceptual architecture;
- CXP v1 package, runtime, publisher, and Git-integration contracts;
- WB-0006 decisions and state machine;
- explicit human approval before mutation;
- GitHub `main` as the stable source of truth.

Runtime implementation resumes after the design-freeze pull request is reviewed and merged.

## Initial operational priorities

1. Maintain secrets hygiene and rotate exposed credentials.
2. Implement the CyberCore Runtime according to CXP v1.
3. Complete the Provider Framework and InterServer provider.
4. Produce sanitized infrastructure inventory and topology.
5. Stabilize and update Nextcloud using backup-first verification.
6. Replace FTP-first deployment with a controlled Git-based workflow.

## Status and navigation

- [`roadmap.md`](roadmap.md) — delivery plan and current work
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — conceptual architecture
- [`foundation/FOUNDATIONS.md`](foundation/FOUNDATIONS.md) — stable project foundations
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — contribution and collaboration rules
- [`SECURITY.md`](SECURITY.md) — security policy
- [`CHANGELOG.md`](CHANGELOG.md) — notable changes

CyberCore is pre-release software. Contracts are being stabilized before production-changing automation is enabled.
