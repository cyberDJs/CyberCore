# CXP-0003 — Publisher Specification v1

## Status

Proposed for WB-0006 design freeze.

## Purpose

Define how a local Work Block becomes an immutable CXP package in a transport `incoming` queue.

## Publisher contract

The publisher MUST:

1. validate the package directory name and required structure,
2. validate `manifest.json` against `cxp/v1`,
3. reject secrets, unsafe paths, forbidden file types and absolute operator-specific paths,
4. regenerate `checksums.sha256`,
5. perform a complete local verification pass,
6. compute a package digest,
7. publish to a temporary transport path,
8. finalize publication using an atomic rename or equivalent completion marker,
9. print the package ID, digest, transport destination and result.

## Publication lifecycle

```text
local draft
  ↓ validate
local sealed
  ↓ upload to temporary path
remote publishing
  ↓ finalize atomically
remote incoming
```

Consumers MUST ignore incomplete temporary publications.

## Immutability

Once published, a package is immutable. Republishing the same Work Block ID and revision is permitted only when the digest is identical. Changed content requires a higher revision.

## Transport boundary

The publisher uses a transport adapter. Google Drive through `rclone` is the first implementation, but Drive-specific details are not part of CXP.

Required transport operations:

- `put_temp(source, destination)`
- `finalize(temp, incoming)`
- `exists(package_identity)`
- `inspect(package_identity)`

## Safety

The publisher MUST NOT:

- upload credentials or private production data,
- mutate the target repository,
- remove existing remote packages automatically,
- overwrite a conflicting package,
- treat a partially uploaded directory as published.

## Required result metadata

- package ID,
- revision,
- content digest,
- schema version,
- publication timestamp,
- transport name,
- remote path or reference,
- publisher version.

## Failure behavior

A failed publication leaves no package visible in `incoming`. Temporary artifacts may be retained for diagnosis or removed only when their ownership is unambiguous.