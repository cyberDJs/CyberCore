# WB-0012 — Foundation Release v0.1

Status: Complete

Date: 2026-07-20

## Goal

Prepare CyberCore for the v0.1.0 public foundation release.

## Scope

- Promote version metadata from alpha to `0.1.0`.
- Align README, architecture, roadmap, changelog, and public-readiness docs.
- Finalize the release license as Apache-2.0.
- Add release notes for v0.1.0.
- Add CyberCore branding assets.
- Verify that the public repository does not require private overlay data.

## Out of scope

- Provider implementation.
- Registry publication.
- GitHub write automation inside the runtime.
- Publisher signing and encrypted transport.
- Production infrastructure inventory.

## Verification

Required checks:

- `python -m pytest`
- `python -m compileall src tests`
- `python -m build`

## Rollback

Revert the WB-0012 commit and remove the GitHub release/tag if publication must
be withdrawn.

## Release boundary

The release contains public framework code, schemas, tests, sanitized examples,
specifications, and documentation only. Private overlays, credentials,
production inventory, runtime state, local virtual environments, and caches are
not part of the tracked release.
