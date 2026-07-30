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

## Internal identity data

Repository identity, checkpoint identity, evidence binding, and post-merge
validation continue to use raw internal values. Redaction is applied only at
external disclosure boundaries.
