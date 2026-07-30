# Operation Context Disclosure Policy

CyberCore Trusted Operation Context uses one disclosure policy for terminal text,
JSON output, checkpoint rendering, evidence diagnostics, and post-merge
diagnostics.

## Field classes

- Public fields remain visible in every mode and preserve native JSON types.
- Operational fields are visible in standard and full mode, and replaced with
  `[REDACTED]` in redacted mode.
- Sensitive fields are replaced with `[REDACTED]` unless full mode is explicitly
  selected.
- Secret fields are never emitted.
- Unknown fields are omitted.

## Diagnostic text

Nested operational diagnostics, including check details and error messages, are
sanitized before output. Standard and redacted diagnostics remove absolute local
paths. Credential-bearing HTTP(S) URLs are stripped of embedded credentials in
every mode.

Full mode can expose sensitive local paths for explicit operator diagnostics, but
it does not expose credentials or secret fields.

## Identity and evidence

Repository identity diagnostics use the same standard, redacted, and full modes.
Default identity output redacts local repository paths and path fallback
identities. Credential-bearing origins are sanitized in every mode.

Checkpoint output exposes `changed_path_count` by default. Changed path strings
are sensitive and are emitted only in explicit full mode.

Verification evidence persists a non-reversible repository binding instead of a
local repository path. Persisted command metadata is sanitized before writing.

## Internal identity data

Repository identity, checkpoint identity, evidence binding, and post-merge
validation continue to use raw internal values. Redaction is applied only at
external disclosure boundaries.
