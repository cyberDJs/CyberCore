# WB-0006 — Exchange Runtime Design Freeze

## Metadata

- **Status:** Active
- **Created:** 2026-07-15T17:20:00+02:00
- **Branch:** `docs/exchange-runtime-design-freeze`
- **Epic:** EPIC-000 — CyberCore Bootstrap
- **Depends on:** WB-0004, WB-0005

## Goal

Freeze the CyberCore Exchange v1 design before further implementation.

## Why

The first runtime experiments proved that transport, package format, runtime state and repository application must be specified independently. Mixing `.tar.gz` bundles with directory packages created ambiguous behaviour and repeated failures.

## Scope

- package format
- runtime state machine
- publisher contract
- verification and apply gates
- failure handling
- repository safety
- acceptance tests

## Non-goals

- production implementation
- auto-commit or auto-push
- multi-node distribution
- cryptographic signing beyond checksums

## Fixed decisions

1. Google Drive via `rclone` is the first transport, not the protocol itself.
2. A Work Block is transferred as a directory, never as a `.tar.gz` archive in CXP v1.
3. Runtime lifecycle is `incoming → staged → ready → processed | failed`.
4. Verification must be non-destructive.
5. Apply requires an explicit human gate.
6. Git commit, push and PR creation are separate post-apply steps.
7. Every package must be location-independent.
8. The target repository must be validated by expected remote and repository markers.

## Acceptance criteria

- CXP-0001, CXP-0002 and CXP-0003 are present and internally consistent.
- The state machine has no ambiguous transitions.
- Security boundaries are explicit.
- Acceptance tests cover happy path, checksum failure, wrong repository, dirty tree and duplicate delivery.
- No runtime code is merged before this block is approved.

## What did we build?

A frozen design contract for the first CyberCore Exchange runtime.

## What did we learn?

Transport and workflow must be decoupled, and bootstrap artifacts must not silently become protocol artifacts.

## What became possible now?

A clean implementation of WB-0007 without redesigning the protocol during coding.
