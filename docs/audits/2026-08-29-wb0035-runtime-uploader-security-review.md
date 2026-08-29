# WB-0035 Runtime Uploader Security Review

Date: 2026-08-29
Verdict: `ACCEPT FOR REVIEW — REMOTE WRITE STILL BLOCKED`
Target: `interserver-shared-hosting-staging`
Related decision: `ADR-0007`

## Scope reviewed

- same-process packet-to-write handoff;
- explicit-FTPS transport configuration;
- endpoint/port binding;
- destination and artifact bounding;
- macOS Keychain alias retrieval;
- upload self-integrity check;
- independent HTTPS effect verification;
- failure behavior before, during, and after remote directory creation.

## Threats and controls

### Credential exposure

Threat: the dedicated FTPS password leaks through arguments, logs, receipts, exceptions, or object representation.

Controls: the Keychain password is read through a captured stdout pipe rather than an argv value; the credential password field uses `repr=False`; runtime exceptions use fixed sanitized text; receipts contain no username/password; the HTTPS verifier carries no credential.

### Authorization bypass

Threat: a caller invokes a mutating transport with a stale packet or without a fresh write approval.

Controls: `execute_first_write_ftps(...)` re-runs `validate_first_write_packet(...)` in-process, requires `remote_write_authorized is True`, requires exact authorization-reference equality, validates the sealed upload input, and only then loads the credential. The mutating FTPS routine is a local closure inside the authorized runner; there is no module-level mutation capability token or direct mutating uploader callable for another module to invoke.

### Endpoint substitution

Threat: a valid credential is sent to another FTPS server.

Controls: protocol must be `FTPS_EXPLICIT`; credential hostname must equal sealed `endpoint_hostname`; username must equal the verified dedicated identity `ccwb34@eimyherrer.com`; port is fixed to 21; TLS peer and hostname verification are mandatory.

### Plaintext downgrade

Threat: FTP authentication or data transfer occurs without TLS.

Controls: the runtime explicitly calls `AUTH TLS`, requires TLS version evidence, calls `PROT P`, enables passive mode, and proves a protected `MLSD` data-channel operation before mutation.

### Path escape or production write

Threat: the uploader traverses outside staging or targets a parent/production path.

Controls: the previously verified DirectAdmin account is chrooted to the staging document root; runtime additionally requires `PWD=/`; the only permitted destination is the exact direct child `cybercore-canary-<run_id>/`; artifact names are fixed to two values. No generic path parameter or delete/chmod/chown operation exists.

### Overwrite

Threat: an existing canary or file is replaced.

Controls: destination absence is proved by a successful protected `MLSD` enumeration of the parent and `MKD` must create a unique directory. Ambiguous `550` responses are not accepted as absence evidence. Each file is likewise proved absent by successful protected `MLSD` before `STOR`. The primary exclusivity boundary is the newly created unique directory. There is no claim of a server-side atomic `O_EXCL` equivalent for `STOR`; post-upload hashes verify resulting bytes. A future server capability that provides stronger atomic file creation may supersede this implementation.

### Unknown-outcome mutation

Threat: a mutating command succeeds remotely but its success response is lost, causing the client to report a false pre-mutation state.

Control: the runtime marks destination creation as potentially mutating before sending `MKD`. If `MKD` raises after dispatch, the result is conservatively reported with `remote_mutation_possible=true`, the same sealed `upload_input`, and partial state with `destination_creation_uncertain=true`. The caller must preserve remote state for independent inspection or separately authorized rollback; it must not assume the destination is absent.

### Partial failure

Threat: a transfer or FTP reply fails after remote mutation, including protocol replies/listings that cannot be decoded as UTF-8, and the caller loses evidence that remote state may already have changed.

Control: uploader performs no automatic delete. FTP transport/protocol errors and `UnicodeDecodeError` are routed through the same sanitized fail-closed handling. If failure occurs after destination creation, during `STOR`, during post-upload retrieval, or after a destination-creation attempt with unknown outcome, the same sealed `upload_input` and partial mutation state are preserved for independent inspection and the separately authorized exact-run-directory rollback procedure.

### False-positive deployment verification

Threat: upload succeeds on FTPS but the public staging site serves different bytes, redirects elsewhere, or returns a stale marker.

Controls: the effect verifier uses a separate HTTPS path, fixed staging origin, no redirect acceptance, exact HTTP 200, exact SHA-256 matching, strict marker schema, exact commit/run/environment binding, and UTC timestamp validation.

## Residual risk

FTP `STOR` does not provide a portable atomic exclusive-create primitive for a chosen filename. WB-0035 narrows this by creating a unique directory first and checking each filename absent immediately before upload. This residual race is materially smaller than using a shared destination and does not expand the allowed path scope. If the server later exposes a verified atomic exclusive-write primitive for exact filenames, it should replace this sequence.

## Decision

The implementation is suitable for branch/CI/review and for a future explicitly authorized single canary write after all WB-0034 evidence and rollback gates are satisfied. It does not itself authorize any remote mutation.
