# CyberCore Visual Documentation

This directory contains source-controlled visual explanations of CyberCore's
evidence lifecycle, engineering workflow, security merge gate, architecture,
and public/private boundary. Each diagram represents a relationship already
defined by the project documentation; it is not a substitute for the
authoritative specifications.

## Visual index

- [Evidence lifecycle](generated/evidence-lifecycle.svg)
- [Work Block lifecycle](generated/work-block-lifecycle.svg)
- [Security merge-gate architecture](generated/security-merge-gate.svg)
- [CyberCore architecture overview](generated/architecture-overview.svg)
- [Public Framework and Private Overlay](generated/public-private-overlay.svg)

## Learn demo

Open [the local Learn demo](learn/index.html) in a browser to follow the
evidence lifecycle in a deterministic 9.6-second loop. It runs without network
access, supports keyboard replay, and respects reduced-motion preferences.

Captured documentation media:

- [WebM](generated/learn-evidence-lifecycle.webm)
- [MP4](generated/learn-evidence-lifecycle.mp4)
- [GIF](generated/learn-evidence-lifecycle.gif)
- [Poster](generated/learn-evidence-lifecycle-poster.png)

## Reproducible workflow

The Node toolchain is isolated in `tools/visual-docs`; it is not part of the
Python runtime package. It requires Node.js >=22.13.0. Install pinned dependencies
without downloading redundant Puppeteer browsers; install Chromium for
Playwright separately:

```bash
(cd tools/visual-docs && PUPPETEER_SKIP_DOWNLOAD=1 npm ci)
(cd tools/visual-docs && npx playwright install chromium)
```

Render every Mermaid source from any working directory:

```bash
scripts/render_visual_docs.sh
```

Capture the Learn demo and encode its WebM, MP4, GIF, and poster assets:

```bash
scripts/capture_learn_demo.sh
```

Validate sources, generated SVGs, local-resource policy, scripts, and captured
media:

```bash
scripts/verify_visual_docs.sh
```

The renderer fails when Mermaid source is invalid. The capture script fails
when FFmpeg, Playwright, or a local Chromium executable is unavailable. No
global Node packages, remote browser resources, capture frames, browser binaries, or
`node_modules` are committed.

## Toolchain security

The visual-docs npm dependency tree is separate from the Python runtime. The
2026-10-18 dependency maintenance update moved Mermaid CLI to 12.0.0 and
Playwright to 1.64.1. At the time of that update, `npm audit` reported no
high, critical, or moderate findings; two low-severity entries remain via
KaTeX. Run `npm audit` regularly and review the trustworthiness of diagram
inputs; track the remaining LOW advisory separately.
