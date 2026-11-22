# InterServer VPS inventory — read-only foundation (2026-11-22)

## Goal
Inventory the InterServer VPS fleet without exposing the account API key or
confusing historical CyberCore targets with currently billed VPS instances.

## Implemented in this candidate
- `cybercore.interserver_inventory.summarize_vps_inventory(payload)` validates
  an explicitly reviewed service-list envelope and returns aggregate counts.
- Unknown status values and unexpected response shapes fail closed.
- No outbound HTTP calls, credentials, production writes or billing mutations.
- Unit tests use synthetic records to check redaction and schema rejection.

## Not yet implemented / intentionally blocked
- No authenticated InterServer provider connector or GitHub Actions secret access.
- The precise current provider response schema and list endpoint still need
  read-only verification against the official API specification.
- The existing GitHub secret `INTERSERVER_API_KEY` was reported by the operator,
  but its value, scopes, validity and runtime availability are not verified.
- No GitHub workflow or live API run is included in this PR.
- Count of currently active or billed VPS remains UNKNOWN.

## Next controlled integration slice
1. Confirm exact InterServer read-only list endpoint and schema from primary
   documentation, including semantic side effects and response sensitivity.
2. Bind an authorized provider runtime to the existing GitHub Actions secret
   without logging, outputting or passing credential material through GitHub
   artifacts or user-visible output.
3. Keep provider transport isolated from the summarizer; sanitize responses
   before durable logging. Require narrow egress and minimum permissions.
4. Add mocked transport tests for success, 401/403, timeout, malformed JSON,
   unexpected schema and pagination. Avoid assuming empty inventory on failure.
5. Use a manually triggered workflow with `contents: read` and no pull_request
   secret exposure, on a reviewed protected branch after explicit approval.
6. Independently compare returned counts with CyberCore target records and
   billing evidence; never infer billing status from VPS existence.

## Acceptance
- Mocked tests green, endpoint contract reviewed, no secret leaks in logs.
- Actual VPS count stated only after a successful authorized read-only call.
- No privilege elevation, credential rotation or production changes.

## 2026-11-22: safe failure diagnostics

An authorized manual workflow run (`45013721930`) reached the inventory
request but failed with a generic provider-query error. The previous handler
deliberately hid upstream details, so the cause could not be distinguished.

The follow-up patch provides only fixed diagnostic categories:
`key_missing`, `http_error`, `network_error`, `timeout`,
`response_too_large`, `invalid_json`, `schema_invalid`.
For `http_error`, a validated numeric status (100–599) may be shown.
Never log exception text, raw HTTP bodies, response headers, URLs or API key.
The previous run's root cause remains unknown until a **new, separately
authorized** read-only run with the reviewed patch.

The CLI exit remains nonzero on any failure; invalid output never becomes
an empty inventory. Merging this diagnostic patch does not trigger the manual
workflow. Confirm CI/security checks before merge and request a fresh
authorization for a new live invocation.
