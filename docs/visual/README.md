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
Python runtime package. Install its pinned dependencies once:

```bash
(cd tools/visual-docs && npm ci)
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
