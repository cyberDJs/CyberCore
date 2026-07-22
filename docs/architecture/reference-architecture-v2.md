# CyberCore Reference Architecture v2

**Status:** Approved direction  
**Date:** 2026-07-22  
**Scope:** Canonical architectural model for CyberCore  
**Supersession:** This document is the highest-level architectural reference. Existing architecture, foundation, ADR, specification, work-block, and README documents remain valid only where they do not conflict with this model.

## 1. Architectural thesis

CyberCore is an evidence-driven control plane for observing, understanding, planning, and safely changing infrastructure.

Its central invariant is:

> No infrastructure decision or mutation may be treated as valid unless it is grounded in explicit, traceable evidence and passes the required governance gates.

The architectural kernel is the **Evidence Runtime**.

The CLI, providers, CXP transport, registry, knowledge engine, planner, mutation engine, demo, learning layer, and project-memory system are modules around that kernel. None of them individually defines CyberCore.

## 2. Canonical end-to-end flow

```text
Provider / Observer
        |
        v
Observation
        |
        v
Evidence
        |
        v
Entity + Claim + Relationship
        |
        v
Knowledge State
        |
        v
Finding / Policy Evaluation / Risk
        |
        v
Decision Candidate
        |
        v
Mutation Plan
        |
        v
Human Approval Gate
        |
        v
Controlled Apply
        |
        v
Post-change Observation and Evidence
```

Every presentation, automation, audit, and learning flow should explain or execute a part of this same lifecycle.

## 3. Kernel

### 3.1 Evidence Runtime

The Evidence Runtime is responsible for the minimum domain primitives and invariants required by all higher layers.

It owns:

- observations;
- evidence records;
- source identity and provenance;
- timestamps and freshness;
- confidence and classification;
- entities and stable identifiers;
- claims;
- contradictions;
- relationships;
- validation contracts.

It does not own:

- provider-specific API behavior;
- user interface rendering;
- transport packaging;
- mutation execution;
- business-specific policy;
- private credentials.

### 3.2 Kernel invariants

1. Assumptions are not evidence.
2. Evidence must have provenance.
3. Evidence must have an observation time.
4. Evidence may expire or become stale.
5. Contradictory claims are preserved and reported, not silently overwritten.
6. Public records must not contain secrets or forbidden production details.
7. A missing fact remains unknown; it is not inferred into certainty.
8. Decisions must be traceable back to supporting evidence.
9. Mutation requires an explicit approval gate.
10. Mutation results must be observed again and recorded as new evidence.

## 4. Architectural layers

### 4.1 Provider Observation Layer

Providers interface with external systems such as hosting platforms, DNS providers, cloud APIs, Git repositories, operating systems, containers, routers, and applications.

Providers should:

- authenticate through private configuration;
- observe external reality;
- normalize observations into Evidence Runtime contracts;
- sanitize public output;
- expose capability metadata;
- distinguish read operations from mutation operations.

Providers must not:

- directly create knowledge conclusions;
- directly bypass policy and approval;
- embed credentials into evidence;
- couple the kernel to provider-specific response formats.

Dependency direction:

```text
Provider -> Evidence Runtime
```

The Evidence Runtime must not depend on a concrete provider.

### 4.2 Knowledge Layer

The Knowledge Layer builds a validated view of the world from evidence.

It owns:

- registry views;
- entity resolution;
- claim validation;
- relationship graph construction;
- contradiction reporting;
- stale and missing evidence detection;
- machine-readable and human-readable reports.

It consumes Evidence Runtime records but does not mutate production infrastructure.

Dependency direction:

```text
Knowledge -> Evidence Runtime
```

### 4.3 Decision Layer

The Decision Layer evaluates knowledge against policy, risk, desired state, and governance.

It owns:

- findings;
- policy evaluation;
- risk scoring;
- decision candidates;
- remediation or change proposals;
- explanation of why a proposal exists.

A decision candidate is not an approved action.

Dependency direction:

```text
Decision -> Knowledge -> Evidence Runtime
```

### 4.4 Mutation Layer

The Mutation Layer converts an approved decision into a controlled execution plan.

It owns:

- deterministic plans;
- dry runs;
- verification;
- approval state;
- apply execution;
- rollback or recovery metadata where supported;
- post-change verification requirements.

Mandatory sequence:

```text
Decision Candidate
    -> Plan
    -> Verify
    -> Explicit Human Approval
    -> Apply
    -> Observe Again
```

No provider mutation may bypass this layer.

### 4.5 CXP Transport Layer

CXP is a transport and packaging subsystem.

It provides:

- deterministic artifact packaging;
- canonical manifests;
- identity and integrity checks;
- transport of work blocks or execution material;
- reproducible build behavior.

CXP is not the CyberCore kernel and must not define domain truth.

Dependency direction:

```text
CXP transports approved runtime material
```

The Evidence Runtime and Knowledge Layer must remain usable without requiring CXP.

### 4.6 Presentation Layer

The Presentation Layer exposes the system through:

- CLI output;
- reports;
- interactive demos;
- learning flows;
- future web interfaces;
- recordings and explanatory surfaces.

Presentation may explain domain state but must not contain independent business logic.

Dependency direction:

```text
Presentation -> Application Services -> Domain Layers
```

### 4.7 Project Memory and Governance Layer

Project Memory tracks the state and evolution of CyberCore itself.

It owns:

- current project state;
- worklog;
- decisions;
- next actions;
- architecture references;
- audit reports;
- capability genome;
- branch and PR disposition;
- verification evidence.

It is a governance subsystem, not a substitute for the Evidence Runtime.

## 5. Canonical domain vocabulary

### Observation

A raw or minimally normalized result obtained from a source at a specific time.

### Evidence

A traceable record derived from an observation and suitable for supporting or challenging a claim.

### Entity

A stable subject in the managed world, such as a server, domain, account, service, repository, certificate, application, or provider resource.

### Claim

A statement about an entity supported by one or more evidence records.

### Relationship

A typed connection between entities or claims.

### Knowledge State

The validated collection of current claims, contradictions, relationships, unknowns, and freshness status.

### Finding

A notable condition derived from knowledge, such as a mismatch, stale certificate, unsupported runtime, missing backup, or policy violation.

### Decision Candidate

A proposed conclusion or course of action supported by findings and policy evaluation. It has not yet passed approval.

### Mutation Plan

A deterministic description of intended changes, prerequisites, checks, expected effects, and recovery considerations.

### Approval

An explicit human authorization bound to a specific plan and revision.

### Apply Result

The recorded result of mutation execution, followed by required post-change observation.

## 6. Dependency rules

Allowed high-level direction:

```text
Presentation
    -> Application / Commands
        -> Mutation
        -> Decision
        -> Knowledge
        -> Evidence Runtime

Providers -> Evidence Runtime
CXP -> transport and packaging services
Project Memory -> repository and process metadata
```

Forbidden directions:

- Evidence Runtime depending on providers;
- Evidence Runtime depending on presentation;
- Knowledge directly executing mutation;
- Providers approving their own mutations;
- Presentation embedding policy decisions;
- CXP becoming the owner of domain truth;
- Project Memory storing production secrets.

## 7. Public and private boundary

The public repository may contain:

- schemas;
- sanitized examples;
- stable entity identifiers that are explicitly safe;
- public architecture;
- provider interfaces;
- deterministic validation logic;
- tests and synthetic fixtures;
- references to private evidence IDs.

The private overlay contains:

- credentials and tokens;
- raw production exports;
- private IPs and topology where classified;
- mailbox details;
- customer data;
- billing details;
- sensitive evidence payloads;
- environment-specific mutation approvals.

The boundary must be enforceable by validation, not only documented as intention.

## 8. Module classification

### Kernel

- Evidence Runtime contracts and validation primitives

### Core domain modules

- Knowledge
- Decision
- Mutation governance

### Infrastructure adapters

- Providers
- filesystem and Git integration
- transport clients

### Transport subsystem

- CXP

### Interface modules

- CLI
- reports
- demo
- learn
- future web UI

### Governance modules

- Project Memory
- ADRs
- audits
- work blocks
- capability genome

## 9. Relationship to existing work

### `main`

Provides the stable runtime, CXP, verify/apply, build, release, and governance foundation.

### PR #13

Contains substantial unmerged implementation of the Evidence, Knowledge, Registry, Policy, Risk, and Planning layers. Its concepts are strategically aligned with this architecture, but the branch must be reintegrated by domain slice rather than merged blindly.

### PR #18

Contains the Presentation Layer foundation, demo, learn, and initial Project Memory artifacts. It is compatible with this architecture provided presentation logic remains separated from domain logic.

### PR #5

Contains earlier provider work. It must be audited and adapted so providers produce Observation and Evidence contracts rather than defining independent knowledge or mutation flows.

## 10. Consolidation principles

1. Preserve valid work before restructuring.
2. Merge low-risk presentation work first where compatibility is confirmed.
3. Create a clean integration branch from updated `main`.
4. Port PR #13 in small domain slices with tests.
5. Rework provider abstractions against the Evidence Runtime contract.
6. Keep mutation disabled until decision-to-approval boundaries are explicit.
7. Replace duplicated architecture sources with indexed, subordinate documents.
8. Generate project-state views from the CyberCore Genome where practical.
9. Require checkpoint updates at the end of each significant work block.
10. Avoid another long-lived architectural feature branch.

## 11. Canonical source hierarchy

When documents disagree, use this precedence:

1. `docs/architecture/reference-architecture-v2.md`
2. Accepted ADRs in `docs/adr/`
3. Versioned specifications in `docs/specifications/`
4. `docs/audits/cybercore-genome.v0.yaml`
5. `PROJECT_STATE.md`
6. Work-block documentation
7. Root README and explanatory documentation

Lower-level documents may add detail but may not contradict a higher-level source.

## 12. Immediate next actions

1. Complete the capability and contradiction matrix.
2. Add `DECISIONS.md` and record approval of Evidence Runtime as kernel.
3. Add `NEXT.md` with the consolidation sequence.
4. Verify PR #18 against this dependency model and merge it if clean.
5. Create a dedicated integration work block for selective PR #13 reintegration.
6. Define the Evidence Runtime schema boundary before porting provider code.
7. Audit and disposition stale PRs and issues.

## 13. Architectural decision summary

CyberCore is not primarily a CLI, package manager, provider library, deployment tool, or documentation system.

CyberCore is an **evidence-driven control plane**.

Its kernel converts observed reality into traceable evidence. Its higher layers convert evidence into knowledge, decisions, approved plans, controlled mutations, and new evidence. Everything else exists to support, transport, present, govern, or extend that lifecycle.
