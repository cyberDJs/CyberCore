# CASER v4.1 evidence preflight

Tracks #141. Optional pure read-only validator of untrusted provider candidates. A syntactically valid batch returns CANDIDATE_ONLY, never VERIFIED. It rejects malformed identities, source SHA drift, duplicate attempts, invalid timestamps and hashes. Provider strings and caller digests are not authentication. Trusted provider adapter and external retained checkpoint are prerequisites for any persistent verification; reuse existing ActionKernel audit and do not build a second audit database. No production, credentials, CASER skill changes, or Drive writes. Rollback: stop importing the pure module. Verify with exact-head CI, CodeQL, CyberHIVE and independent review.

The repository identity grammar requires exactly two ASCII owner/repo segments and rejects control characters, missing segments, and unexpected slashes. Expected and observed identities are validated before comparison. Untrusted datetime tzinfo implementations may raise arbitrary Exception subclasses; these are translated to BLOCKED/INVALID_TIMESTAMP, not propagated as runtime errors. Neither result is a provider-authenticated attestation.

Untrusted scalar and container identities require exact built-in types (str, int and tuple) before equality, set hashing, or iteration; hostile subclasses are rejected rather than interpreted as evidence. This is defensive shape validation, not authentication.

Datetime values must be exact built-in datetime objects; spoofed __class__ values and hostile datetime subclasses cannot bypass the fail-closed timestamp check.

All candidate fields are first captured into local variables. A partially initialized or tampered dataclass with missing attributes is BLOCKED/INVALID_RECORD before parsing, and no later check re-reads the mutable object fields.
