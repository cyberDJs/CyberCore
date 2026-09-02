# CyberCore Architecture

CyberCore is an **Infrastructure Context & Intelligence Platform** with an **AI-first Infrastructure Control Plane** as its technical core.

Its purpose is to reduce uncertainty by turning operational reality into reusable knowledge, safer decisions, and controlled automation.

> Technology serves people. Never the other way around.

## Architectural model

```text
Reality
  |
  v
Observation and evidence
  |
  v
Knowledge and context
  |
  v
Confidence and decisions
  |
  v
Specifications and Work Blocks
  |
  v
Verified implementation
  |
  v
Controlled automation
  |
  v
Operational outcomes
  |
  +--------------------> new observations
```

## Layers

```text
CyberCore
├── Interfaces
│   ├── CLI
│   ├── Cyber Voice
│   ├── automation clients
│   └── AI-assisted interaction
├── Foundation
│   ├── identity and principles
│   ├── engineering method
│   ├── terminology
│   ├── decision model
│   └── knowledge model
├── Knowledge
│   ├── observations and evidence
│   ├── Knowledge Blocks
│   ├── inventory and topology
│   ├── incidents and outcomes
│   └── provenance and confidence
├── Specifications
│   ├── protocol contracts
│   ├── runtime behavior
│   ├── provider contracts
│   └── security and compatibility rules
├── Engineering
│   ├── RFCs and ADRs
│   ├── Work Blocks
│   ├── verification
│   ├── rollout and rollback
│   └── release evidence
├── Runtime
│   ├── local agent
│   ├── Exchange and transport adapters
│   ├── validation and state management
│   ├── controlled apply
│   └── reporting
├── Providers
│   ├── InterServer
│   ├── DirectAdmin
│   ├── SSH
│   ├── GitHub
│   └── future infrastructure adapters
├── Intelligence
│   ├── context resolution
│   ├── risk and drift analysis
│   ├── recommendations
│   ├── cost optimization
│   └── AI-assisted review
└── Operations
    ├── inventory
    ├── monitoring and observability
    ├── deployment
    ├── security
    ├── incident response
    └── controlled self-healing
```

## Public Framework + Private Overlay

The public repository contains reusable framework logic, specifications, sanitized examples, schemas, tests, and documentation.

Private overlays contain credentials, production-derived inventory, client data, private topology, operational secrets, and environment-specific configuration.

The boundary is mandatory. Private data must never be required for the public framework to remain understandable and testable.

The [visual architecture overview](docs/visual/generated/architecture-overview.svg)
and [public/private overlay diagram](docs/visual/generated/public-private-overlay.svg)
provide a compact orientation layer. This document remains the authoritative
written architecture specification.

## Core boundaries

### Interfaces

Interfaces translate human or machine intent into bounded CyberCore contracts. They do not own provider credentials, mutation authority, or verification semantics.

Cyber Voice is the governed human operating interface. Its Foundation contract is documented in [`docs/architecture/CYBER_VOICE.md`](docs/architecture/CYBER_VOICE.md) and ADR-0008.

### Foundation

Foundation documents change rarely. They define how CyberCore thinks and why it exists. Changes require explicit review and must not be smuggled through implementation work.

### Specifications

Specifications define contracts before implementation. Critical runtime behavior follows:

```text
Specification -> approval -> implementation -> verification -> merge
```

### Runtime

Runtime executes approved, verifiable workflows. It does not invent architecture while applying changes.

### Providers

Providers translate external systems into normalized CyberCore capabilities and evidence. Provider-specific behavior must not leak into the core model unless promoted through an approved contract.

### AI

AI may observe, propose, explain, correlate, generate drafts, and verify. AI does not silently cross human approval gates for destructive or production-changing actions.

## Cyber Voice architecture

Cyber Voice converts human utterances into bounded intents and action requests while preserving the existing CyberCore authority model.

```text
Human utterance
      |
      v
Intent compiler
      |
      v
Session + context
      |
      v
Action planner
      |
      v
HOWEDO continuity
      |
      v
OATHDO governance
      |
      v
CCL approval verification
      |
      v
Existing CyberCore execution boundary
```

Key invariants:

- voice input is intent, never implicit authority;
- a voice approval phrase does not itself authorize execution;
- mutating actions require exact plan and revision binding;
- unknown continuity or governance states fail closed;
- HOWEDO and OATHDO remain adapter integrations, not mandatory core dependencies;
- the Foundation Voice layer stops at action readiness and performs no direct execution.

Audio capture, STT, TTS, wake words, speaker authentication, realtime model providers, CASEBOOK/CASER persistence, and tool-specific action routers are future adapter layers.

## Exchange architecture

CyberCore Exchange is protocol-first and transport-independent.

```text
Publisher
   |
   v
CXP package
   |
   v
Transport adapter
   |
   v
Local inbox -> staged -> ready -> processed
                         |
                         +-> failed
```

For CXP v1:

- packages are directories, not tar archives;
- verification is read-only;
- apply requires an explicit human gate;
- commit, push, and PR creation happen only after successful apply and tests;
- Google Drive through rclone is the first transport, not part of the protocol itself.

## Source of truth

- GitHub `main` is the stable source of truth.
- Feature branches contain reviewable change sets.
- Local repositories are development workspaces.
- Runtime state and secrets remain outside Git.
- Documentation is versioned alongside the contracts and code it explains.

## Initial deployment scope

```text
InterServer
├── Shared hosting
│   ├── eimyherrer.com
│   ├── mail
│   ├── WordPress
│   ├── Nextcloud
│   └── selected Softaculous applications
└── VPS
    ├── DirectAdmin
    ├── system services
    ├── automation runtime
    └── observability services
```

## Architectural quality rules

1. Know what exists.
2. Understand why it is there.
3. Keep only what creates value.
4. Automate only what is understood.
5. Complexity is guilty until proven useful.
6. Prefer evidence over confidence theatre.
7. Preserve provenance and rollback paths.
8. Optimize for maintainability, cost, security, and human attention together.

## Current stage

The current architectural milestone is **Foundation Release v0.1** with Cyber Voice Foundation introduced as a reviewable interface-layer extension.

The foundation release freezes the project identity, public/private boundary, CXP v1 contracts, initial CLI/runtime surface, and deterministic artifact publisher. Future releases extend provider integrations, cryptographic trust, registry discovery, GitHub write automation, and governed human interfaces through new specifications and Work Blocks.
