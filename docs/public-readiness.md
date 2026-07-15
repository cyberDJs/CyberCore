# Public Readiness and Open-Source Strategy

Status: Accepted

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

## License direction

Apache License 2.0 is the current recommendation because it supports broad adoption, commercial use and includes an explicit patent grant. Final licensing is confirmed before public release.

## Data rule

> No production-derived knowledge is committed to the public repository.

## Product ambition

> CyberCore should give engineers back the time they deserve to spend on what matters most.
