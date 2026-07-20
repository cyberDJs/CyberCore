# Public Readiness and Open-Source Strategy

Status: Accepted

Release baseline: **v0.1.0 foundation release**

## Model

> Public Framework + Private Overlay

## Always open-source

- Core
- CLI
- SDK
- Documentation Engine

Provider and plugin extension points should remain possible without prematurely implementing a full plugin system.

## Always private

- production Inventory,
- Secrets,
- AI Memory,
- deployment configuration,
- internal Knowledge Graph,
- customer overlays,
- production telemetry and audit data.

## Overlay

An Overlay is a private adaptation layer that extends CyberCore for a specific Environment without modifying the public framework.

## Vendor approach

CyberCore is vendor-adaptable rather than artificially vendor-independent.

Provider-specific capabilities belong in adapters. Shared concepts belong in Core.

## License

CyberCore v0.1.0 is released under the Apache License 2.0.

Apache License 2.0 supports broad adoption, commercial use, and includes an explicit patent grant.

## Data rule

> No production-derived knowledge is committed to the public repository.

## v0.1.0 public release gate

- [x] Public Framework + Private Overlay boundary documented.
- [x] License finalized.
- [x] No secrets, credentials, or production-derived inventory required by the public framework.
- [x] Runtime state, caches, local virtual environments, and private overlays remain outside Git.
- [x] Release notes and changelog identify known limitations before publication.

## Product ambition

> CyberCore should give engineers back the time they deserve to spend on what matters most.
