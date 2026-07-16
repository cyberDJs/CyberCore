# ADR-0004 — CXP Artifact Format v1

- Status: Accepted
- Date: 2026-07-16
- Decision owners: CyberCore maintainers
- Related: EPIC-002, WB-0009

## Context

CyberCore Work Blocks were initially exchanged as directories and tarballs.
That bootstrap format was sufficient to prove transport and apply workflows,
but it does not provide a stable immutable artifact contract.

Publisher, Runtime and Registry require one shared representation with
deterministic identity, integrity verification, compatibility metadata and a
clear extension point for signing and encryption.

## Decision

CyberCore adopts CXP/1 as its artifact contract.

A CXP artifact is:

- a deterministic POSIX tar archive;
- content-addressed by SHA-256;
- composed of manifest, metadata, checksums and compressed payload;
- optionally signed with Ed25519;
- optionally wrapped with age/X25519 encryption;
- independent from the transport backend.

Artifact identity is the digest of canonical bytes, never the filename or
transport path.

## Consequences

Positive:

- reproducible artifacts;
- reliable deduplication and idempotency;
- transport providers remain replaceable;
- signatures and encryption can be added without redesigning payload semantics;
- Runtime can reject ambiguous or unsafe archives.

Costs:

- deterministic packaging is stricter than ordinary tar creation;
- publisher and runtime must implement canonicalization identically;
- key management remains a separate operational responsibility;
- encrypted artifacts cannot be previewed or indexed by Google Drive.

## Alternatives rejected

### Directory packages

Easy to inspect but mutable, transport-dependent and unreliable for identity.

### Generic ZIP files

Broad compatibility but weaker normalization conventions and awkward POSIX
metadata semantics.

### OCI images immediately

Powerful but operationally excessive for the current project and budget.
Future registry mapping remains possible.

### Custom cryptography

Rejected. CXP uses established primitives and external formats.
