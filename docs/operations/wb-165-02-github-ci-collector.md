# WB-165-02 — authenticated read-only GitHub CI collector (draft candidate)

**Scope:** review-only Python library and negative tests. No token provisioning, scheduler, transport, checkpoint persistence, notifications, runtime registration, merge, or deployment.

## Boundary and decision

`operator_ci_snapshot.py` from PR #165 is already **MERGED** into main and remains a pure fail-closed formatter. The previous draft-status line is obsolete. Its `CONSISTENT_ONLY` state must remain `UNKNOWN` even when GitHub workflow observations were read through this authenticated collector: transport authentication is not cryptographic attestation, and reporting is not merge authorization.

`github_ci_collector.collect_pr_ci(reader, pr_number, expected_sha)` fetches PR HEAD before and after acquisition, binds exact repository/PR/head, paginates runs and jobs with `total_count` checks, validates latest-attempt job records, rejects duplicate/foreign workflow identity, enforces small explicit resource caps, and returns data structures consumed by `reconcile_github_snapshot`. Reject, do not repair, drift or provider anomalies.

`GitHubHTTPSReader` uses HTTPS to the fixed `api.github.com` host, bearer auth supplied explicitly by a caller, strict GET-only repository paths, TLS validation, response-size bound, timeouts, and **no redirects**. It never stores tokens, logs provider bodies, grants permissions or invokes merge/deploy. A trusted caller is responsible for supplying a least-privilege token and protecting its lifecycle; no credential is embedded or created here.

## Preconditions and residual limitations

- Only GitHub REST read endpoints are accessed. No GitHub API key or other credential is written to source/configuration.
- The collector accepts only PR-linked `pull_request` workflow runs with matching HEAD, repository, and PR number; tests must not conflate unrelated main-push CI with PR-head checks.
- Pagination is `per_page=25`, with multi-page total-count stability checks and checked against `total_count` with a maximum of 20 runs/100 jobs. Larger histories fail closed and require a redesigned bounded collector.
- `filter=latest` excludes earlier workflow attempts: this draft **does not authenticate completeness across all run attempts**. Before any claim of audited historical attestation, extend acquisition to enumerate every attempt or explicitly limit claims to latest-attempt state; neither is authorized as PASS here.
- A caller-supplied client may be fake or untrusted. The real HTTPS reader is the only authenticated transport candidate. No signed GitHub attestation is verified.
- Any API error, bad shape, missing/duplicate workflow, changed HEAD, foreign run/job, truncated pagination, or size limit must fail closed. No automatic retries that silently change the observed HEAD.
- `operator_checkpoint` still requires transport ACK before the caller persists fingerprint. No ACK storage or external notification built here.

## Test and review gates

Unit tests use an in-memory fake reader: complete data, wrong PR/repo/HEAD, racing HEAD, duplicate workflow, missing workflow, foreign job, incomplete pagination, oversized data, bad token/endpoint, and failed job. Run Python 3.11–3.14 CI, package, quality, CodeQL and CyberHIVE exact-head checks. Security review must consider remote-host pinning, redirect suppression, token leakage through exception/log handling, pagination/attempt completeness, and PR-to-run binding.

**Rollback:** close the isolated draft PR without merge. No runtime impact. Future adoption, scheduled delivery, authenticated attestation, checkpoint persistence and deployment require separately authorized work.
