# CyberCore visual-docs dependency remediation evidence — 2026-10-18

Status: PR candidate; not deployed.
Baseline `main`: `cd2f19f5921b2837781e9a069979501a27624941`.
Scope: isolated Node visual-docs toolchain, not the Python runtime.

## GitHub alert inventory

At discovery: 10 open Dependabot alerts (5 HIGH / 4 MEDIUM / 1 LOW).
All 5 HIGH alerts affect `tools/visual-docs/package-lock.json`:

| Alert | Package | Prior lock version | Finding |
| --- | --- | --- | --- |
| GHSA-c475-qrg2-pj4r | `basic-ftp` | 5.3.1 | CPU denial of service |
| GHSA-2883-xcg3-v3hh | `js-yaml` | 4.3.1 | Excessive merge-key CPU |
| GHSA-7pqw-9j4j-h8q3 | `extract-zip` | 2.0.1 | Symlink archive write |
| GHSA-jmr9-qjv8-65gv | `extract-zip` | 2.0.1 | Symlink path traversal |
| GHSA-7mvr-c777-76hp | `playwright` | 1.55.0 | Browser download TLS |

The original `npm audit --json` reported 11 HIGH, 1 MODERATE and 3 LOW
dependency-tree entries; this is not the count of distinct CVEs or GitHub alerts.

## Remediation change

- `@mermaid-js/mermaid-cli`: 11.12.0 -> 12.0.0.
- `playwright`: 1.55.0 -> 1.64.1.
- Regenerate `package-lock.json` and document Node.js >=22.13.0.
- Skip redundant Puppeteer browser downloads in install instructions.
- Refresh 5 generated Mermaid SVG assets for the new renderer.

## Verification evidence

- `npm audit --audit-level=moderate --json`: exit 0; **0 CRITICAL, 0 HIGH,
  0 MODERATE, 2 LOW**.
- Clean `npm ci --ignore-scripts` with browser download skip flags: PASS.
- Lock dependency tree: `extract-zip`, `basic-ftp`, `js-yaml`: ABSENT.
- `scripts/verify_visual_docs.sh`: PASS, five Mermaid renders.
- All original text labels retained in the regenerated SVGs; no external
  SVG resource references; new layout/viewBox values are renderer changes.
- Playwright resolved local Google Chrome successfully on macOS.
- `node tools/visual-docs/capture.mjs`: PASS: 162 frames, 1280x720,
  10.800-second WebM; disposable capture artifacts removed afterward.
- `git diff --check`: PASS.

## Remaining risk

The 2 LOW npm-audit entries trace to one KaTeX advisory:
[GHSA-238p-pmpm-9mq7](https://github.com/advisories/GHSA-238p-pmpm-9mq7).
Mermaid CLI 12 currently requests KaTeX 0.16.x, while the advisory reports
versions before 0.18.2 affected. No untested forced major override was applied.
Track this remaining LOW exposure as separately reviewed maintenance.

The toolchain processes trusted local source diagrams. Do not run it with
untrusted input without additional isolation or reviewing the trust boundary.

## Impact and rollback

Changed scope: visual-docs manifest, lockfile, generated diagrams and
documentation/evidence only. No servers, runtime packages, DNS, deployment,
GitHub rules, CI configuration or production storage were modified.

On regression: hold visual docs publishing and revert this remediation PR
with a separate reviewed change. Restoring the old vulnerable package lock
is not a safe permanent fix. Merge requires approved review and green checks.
