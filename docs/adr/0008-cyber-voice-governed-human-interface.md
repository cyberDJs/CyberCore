# ADR-0008 — Cyber Voice as a Governed Human Operating Interface

Status: Accepted
Date: 2026-09-02
Accepted: 2026-09-02
Authorized by: Jan Kočí
Work block: `WB-0036`
Decision readiness: `DECIDED`

## Context

CyberCore already separates evidence, decisions, human approval, controlled execution, verification, and memory. A voice interface that directly maps speech to shell commands or provider mutations would create a parallel authority path and undermine those boundaries.

At the same time, voice interaction is valuable precisely when it can preserve conversational context, accept interruption and correction, explain risk, prepare plans, and hand bounded actions to the existing CyberCore control plane.

HOWEDO already defines continuity semantics for long-lived stateful work, while OATHDO defines governance and authority-oriented change controls. Both are useful to CyberCore when consumed as narrow adapters rather than copied into the core or promoted into competing runtimes.

## Decision

Cyber Voice is implemented as the governed human operating interface of CyberCore.

The Foundation contract is:

```text
Utterance
  -> Intent
  -> Session / Context
  -> Action Plan
  -> HOWEDO continuity
  -> OATHDO governance
  -> CyberCore approval verification
  -> existing execution boundary
```

The following rules are binding:

- Cyber Voice is an interface layer, not a second execution runtime;
- HOWEDO and OATHDO remain independently versioned systems behind adapter contracts;
- neither HOWEDO nor OATHDO is a mandatory Python dependency of CyberCore Foundation;
- CCL-0005 remains the canonical authority for mutating CyberCore actions;
- a voice approval phrase creates an approval intent only, not authorization;
- mutating actions require exact plan id and plan revision binding;
- absent or unknown continuity/governance integration states fail closed;
- the Foundation slice may return `READY` but does not execute the action itself;
- audio, STT, TTS, wake-word, speaker identity, and realtime-model providers are deferred adapters.

## Why this boundary

This design lets Cyber Voice become substantially more capable without making speech a privileged path around CyberCore governance.

A user can eventually interrupt a response, correct a target, ask for impact analysis, approve a bounded plan, or resume long-running work while the same evidence and authority rules remain intact.

## Alternatives considered

### Voice-to-command bridge

Rejected as the primary architecture. It is simple, but it collapses natural-language intent, authority, planning, and execution into one unsafe boundary.

### Embed HOWEDO and OATHDO directly into CyberCore

Rejected. Their semantics are useful independently, and hard coupling would create release and dependency pressure while making future replacement or standalone use harder.

### Separate Cyber Voice service with its own approvals

Rejected. A second approval system would fragment authority and create ambiguous precedence against CCL-0005.

### Governed interface with adapters

Selected. It reuses CyberCore's existing lifecycle and keeps audio/model/tool providers replaceable.

## Consequences

Positive:

- voice cannot become a hidden privileged execution channel;
- HOWEDO continuity and OATHDO governance gain concrete CyberCore integration points;
- CCL approval remains canonical;
- the core remains dependency-light and provider-neutral;
- future STT/TTS or realtime-model providers can change without redesigning authority semantics;
- the same interface contract can accept typed text for testing and non-audio clients.

Tradeoffs:

- the first slice is intentionally not a complete voice assistant;
- an upstream speech adapter and downstream action planner are still required for useful end-to-end operation;
- `READY` must not be confused with execution success;
- speaker authentication will require a separate security design before voice can participate in high-assurance identity workflows.

## Security invariants

- Voice input is always treated as untrusted intent.
- Voice never self-mints human authority.
- Approval must remain bound to the exact CyberCore plan and revision.
- Unknown HOWEDO decisions become `ABORT`.
- Unknown OATHDO decisions become `DENY`.
- Mutation without a matching CyberCore approval is blocked.
- No provider credential, audio recording, biometric template, or secret is introduced by WB-0036.
- No shell, GitHub, deployment, or infrastructure mutation is authorized by this ADR.

## Rollback

WB-0036 adds a new isolated Python package surface, adapter contracts, tests, and documentation. Rollback is source-level removal of those additions plus the architecture references. It requires no data migration, credential rotation, provider change, or production rollback.

## Implementation gate

The Foundation implementation must remain inside the interface/control boundary described above. Adding direct execution, microphone access, external voice providers, speaker authentication, credentials, or production-changing behavior requires a separately reviewed work block and, where the authority model changes, a new ADR.
