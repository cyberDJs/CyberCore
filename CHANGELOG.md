# Changelog

## v0.1.0 — 2026-07-20

Foundation release for the public CyberCore framework.

### Added

- Foundation Release v0.1 release notes.
- Release branding assets, including the CyberCore logo, icon mark, and social preview SVGs.
- WB-0012 release evidence for the public foundation release.

### Changed

- Promoted package metadata and runtime compatibility from `0.1.0a1` to `0.1.0`.
- Updated README, architecture, roadmap, and public-readiness documentation for the foundation release state.
- Finalized the public license as Apache-2.0.

### Security boundaries

- No provider credentials, production inventory, customer data, runtime state, local virtual environments, or caches are part of the tracked public release.
- Production-changing automation remains gated by explicit human approval.

### Known limitations

- Provider implementations are not included in v0.1.0.
- CXP artifacts can be built and verified, but Runtime does not yet consume them from a registry.
- Cryptographic publisher signing and encrypted transport remain future work.

## v0.1.0-alpha.1 — 2026-07-16

First public development checkpoint for the CyberCore foundation, runtime, and artifact system.

### Added

- CyberCore Identity v1.0, Governance, Manifesto, Glossary, and Design System foundation.
- Foundation engineering model, terminology, decision model, and knowledge model.
- `ARCHITECTURE.md` as the conceptual system map.
- Public Framework + Private Overlay strategy.
- Runtime Alpha with the unified `cybercore` CLI.
- `doctor`, `status`, and `sync` commands.
- Controlled Work Block `verify` and `apply` commands.
- Explicit approval gate, `--dry-run`, branch and clean-working-tree safety checks.
- Lifecycle events and optional `before_apply`, `after_apply`, and `rollback` hooks.
- CXP/1 artifact specification, JSON Schemas, examples, and ADR-0004.
- Deterministic `cybercore build` publisher.
- Canonical JSON, deterministic tar construction, Zstandard payload compression, and SHA-256 artifact identity.
- Baseline tests for runtime, transport, verification, apply, and reproducible artifact builds.

### Security boundaries

- SHA-256 currently proves artifact integrity, not publisher trust.
- Ed25519 publisher signing is deferred to a subsequent alpha increment.
- Age/X25519 end-to-end encryption is deferred to a subsequent alpha increment.
- Secrets and production-derived data remain outside the public framework.

### Known limitations

- CXP artifacts can be built but are not yet consumed directly by Runtime.
- Registry publication and discovery are not implemented.
- Git commit, push, pull-request creation, and merge orchestration remain manual.
- The InterServer provider implementation remains in a separate draft branch pending alignment with Runtime.

## 2026-07-16

### Added

- Foundation layer: `FOUNDATIONS.md`, engineering method, terminology, decision model and knowledge model.
- `ARCHITECTURE.md` as the conceptual system map.
- CXP v1 specifications for package format, runtime, publisher and Git integration.
- WB-0006 Exchange Runtime Design Freeze with explicit state machine and fixed decisions.
- Knowledge Block and Work Block distinction.

### Changed

- README aligned with CyberCore Identity v1.0 and the descriptor **Infrastructure Context & Intelligence Platform**.
- GitHub `main` reaffirmed as stable source of truth; local repositories remain development workspaces.
- Exchange defined as protocol-first and transport-independent.

### Fixed

- Removed ambiguity between directory-based CXP packages and legacy tar archives at the specification level.
- Formalized the human approval gate before mutation, commit, push or PR creation.

## 2026-07-15

### Added

- CyberCore Identity v1.0.
- Governance model and decision layers.
- Manifesto and product vision.
- Glossary and terminology integrity rules.
- Design system foundation and voice principles.
- Public Framework + Private Overlay strategy.
- ADR-0002 recording the identity freeze.

## 2026-07-08

### Added

- Initial CyberCore project bootstrap.
- Initial roadmap.
- Initial security policy.
- Initial vision.
- Initial documentation structure.
