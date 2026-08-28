# ADR-0007 — Path-Scoped Explicit FTPS for WB-0034

Status: Accepted
Date: 2026-08-29
Accepted: 2026-08-29
Authorized by: Jan Kočí
Work block: `WB-0034`
Decision readiness: `DECIDED`

## Context

WB-0034 originally allowed only `SFTP` or `SSH` for the first InterServer staging write. Read-only runtime verification proved that `staging.eimyherrer.com:22` provides SSH/SFTP and that the existing `eimyherr` identity can write the canonical staging document root. The same identity can also write the production document root, so it fails the least-privilege gate for an automated first-write runner.

DirectAdmin supports FTP accounts with a custom filesystem root. InterServer documents explicit FTP over TLS on port 21 and DirectAdmin-managed FTP accounts. This provides a practical route to a credential whose server-side home is restricted to the staging document root instead of the full hosting account.

## Decision

WB-0034 may use `FTPS_EXPLICIT` as an approved first-write transport when, and only when, all of the following are independently verified before authorization:

- the account is a DirectAdmin custom-path FTP identity;
- its effective root is exactly `/home/eimyherr/domains/staging.eimyherrer.com/public_html`;
- it cannot traverse to or write `/home/eimyherr/domains/eimyherrer.com/public_html`;
- the client requires explicit TLS (`AUTH TLS`) and rejects plaintext FTP fallback;
- certificate and hostname verification are enabled;
- the FTPS endpoint hostname is the hostname covered by the server certificate;
- no credential value is stored in GitHub, chat, Drive, CASER evidence, logs, or ordinary receipts;
- the first write remains the existing unique two-file no-overwrite canary;
- fresh operator authorization still binds commit, run id, protocol, scope, destination, artifacts, and rollback permission.

`FTP`, opportunistic TLS, disabled certificate verification, implicit downgrade, and a production-wide FTP identity are not approved transports.

## Alternatives considered

### Existing `eimyherr` SSH/SFTP identity

Rejected for the automated first-write runner because runtime capability evidence shows production write capability.

### Provider-created staging-only SFTP identity

Security-preferred when available, but not currently proven to be self-service on this InterServer shared-hosting account.

### Explicit FTPS with DirectAdmin custom-path account

Selected because it can enforce the staging boundary at the account root while preserving encrypted transport and requiring no production-wide SSH credential.

## Consequences

Positive:

- least privilege is enforced server-side at the staging path;
- the existing production-capable SSH key is excluded from the automated first-write path;
- the current no-overwrite canary and rollback design remain unchanged.

Tradeoffs:

- FTPS uses separate command/data channels and therefore has more network behavior to verify than SFTP;
- certificate hostname verification requires the correct InterServer server hostname, not an assumed web hostname;
- the WB-0034 validators and runtime uploader must explicitly implement `FTPS_EXPLICIT` before the packet can become READY.

## Security invariants

- Plain FTP is always denied.
- TLS verification must fail closed.
- A credential rooted above the canonical staging document root is not least privilege.
- A path-scoped account must not be treated as verified merely because DirectAdmin reports a configured path; an authenticated read-only capability probe must verify the effective root and production exclusion.
- This ADR does not authorize account creation, password creation, remote upload, delete, staging apply, or production mutation.

## Rollback

Before any remote write, rollback remains the WB-0034 exact run-directory delete operation and must be separately authorized. If the FTPS design cannot meet the gates above, revert the transport decision to blocked and do not fall back to the production-capable SSH identity automatically.

## Implementation gate

This ADR changes the approved design, not the current runtime readiness. Existing validators that accept only `SFTP`/`SSH` remain authoritative until updated and tested. `FTPS_EXPLICIT` must not be recorded as VERIFIED in a final packet until validator support, evidence semantics, tests, and the same-process uploader are implemented and reviewed.