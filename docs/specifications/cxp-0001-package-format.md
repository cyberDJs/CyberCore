# CXP-0001 — Package Format v1

## Status

Proposed for WB-0006 design freeze.

## Purpose

Define the transport-independent directory format of a CyberCore Work Block package.

## Canonical structure

```text
WB-XXXX-meaningful-slug/
├── manifest.json
├── checksums.sha256
├── README.md
├── actions/
│   ├── verify.sh
│   └── apply.sh
└── payload/
    └── ...
```

CXP v1 packages are directories. Archive formats are not valid package representations.

## Required files

- `manifest.json` — machine-readable metadata and compatibility contract.
- `checksums.sha256` — SHA-256 digest list for every package file except itself.
- `README.md` — human-readable goal, scope and operator instructions.
- `actions/verify.sh` — non-destructive verification entry point.
- `actions/apply.sh` — explicit mutation entry point.
- `payload/` — files applied to the target repository or runtime.

## Manifest minimum

```json
{
  "schema": "cxp/v1",
  "id": "WB-0007",
  "slug": "exchange-runtime-v1",
  "version": "1.0.0",
  "created_at": "2026-07-15T18:00:00+02:00",
  "target": {
    "repository": "cyberDJs/CyberCore",
    "base_branch": "main"
  },
  "requires": [],
  "capabilities": ["verify", "apply"]
}
```

Unknown mandatory schema versions must be rejected.

## Integrity

- Digests use SHA-256.
- Verification runs from the package root.
- Missing, additional or modified files fail validation unless explicitly allowed by the manifest.
- Checksums prove integrity, not authorship. Cryptographic signing is deferred beyond v1.

## Portability

All scripts must resolve the package root from their own location. They must not depend on the caller's current working directory.

## Prohibited content

- secrets or credentials,
- private production inventory,
- absolute operator-specific paths,
- executable files outside declared actions,
- symlinks escaping the package root.

## Compatibility

A v1 runtime may process only `schema: cxp/v1`. Later schema versions require explicit runtime support.