# ADR 0003: Provider Framework and InterServer Provider v0.1

Date: 2026-07-15

Status: Proposed

## Context

CyberCore needs a reusable way to integrate providers without hardcoding InterServer into Core. Governance requires structural changes to be explicit, reviewed and understood.

## Decision

Introduce a minimal Python provider abstraction and implement InterServer as the first provider.

The first increment includes:

- a small provider protocol,
- typed provider health results,
- environment-based configuration,
- an InterServer API client,
- a `cybercore doctor` command,
- tests for configuration and provider health behavior.

The design intentionally avoids a full plugin system. Provider extension points remain possible, but complexity must justify itself.

## Boundaries

- Public framework code stays provider-adaptable.
- Secrets are loaded from environment variables and never written to Git.
- Production inventory and private operational knowledge remain in a Private Overlay.
- Destructive InterServer actions are out of scope for v0.1.

## Consequences

- InterServer becomes Provider #1, not a special case in Core.
- Future providers can implement the same contract.
- The first CLI capability validates configuration and connectivity before inventory work starts.

## Verification

- Unit tests pass.
- `cybercore doctor` reports configuration and provider connectivity without revealing secrets.
- No production-derived data is committed.

## Review

This ADR requires maintainer review before merge.
