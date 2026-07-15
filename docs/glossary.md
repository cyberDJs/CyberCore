# CyberCore Glossary

Status: Accepted working vocabulary.

## Terminology principle

> One Concept = One Word

A term must have one stable meaning across code, documentation, prompts and interfaces.

## Core terms

### Environment

Everything that forms the operational ecosystem of a project. Infrastructure is a subset of an Environment.

### Provider

An external or internal system integrated through a defined adapter or API.

### Inventory

The structured representation of known entities in an Environment.

### State

The condition of an entity at a specific point in time.

### Evidence

Observed data supporting a conclusion, including logs, metrics, API responses, traces and verified configuration.

### Context

The relationships, purpose, ownership and history that make State and Evidence understandable.

### Knowledge

Validated operational understanding derived from Evidence and Context.

### Confidence

An explicit assessment of how strongly available Evidence supports a conclusion or action.

### Integrity

Consistency and trustworthiness across data, architecture, workflow, documentation and decisions.

### Snapshot

A timestamped representation of an Environment or part of it.

### Runbook

A reviewed operational procedure with prerequisites, actions, verification and rollback.

### Overlay

A private adaptation layer that extends CyberCore for a specific Environment without modifying the public framework.

### Issue

A bounded problem requiring work.

### Risk

A possible future event with probability and impact.

### Incident

An active event affecting or threatening normal operation.

## Language policy

- Domain terms remain English.
- Surrounding documentation may be Czech or English.
- Use AI-native terminology only where technically accurate.
- Observability does not automatically replace Monitoring.
- Evidence does not automatically replace Logs.

## Discouraged words

Avoid unsupported simplifications such as:

- obviously,
- somehow,
- simply,
- just,
- trivial,
- easy,
- magic.

Explain the mechanism instead.
