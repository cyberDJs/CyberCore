# CyberCore Use Cases

This directory defines repeatable demonstrations of CyberCore workflows. Each use case is designed to exist in three forms:

1. a human-readable walkthrough,
2. an executable scenario script,
3. a recorded terminal session (`.cast`) rendered for documentation.

## Demonstration pipeline

```text
scenario script
    -> asciinema recording
    -> .cast source
    -> SVG/GIF/MP4 render
    -> README and learning module
```

## Initial scenarios

| ID | Scenario | Purpose |
|---|---|---|
| UC-001 | Reality to Evidence | Observe an environment and produce verifiable evidence. |
| UC-002 | Drift Detection | Compare current and desired state. |
| UC-003 | Explain Risk | Explain dependencies, impact and confidence. |
| UC-004 | Governed Remediation | Generate a plan and require explicit approval. |
| UC-005 | Verify and Roll Back | Verify an outcome and demonstrate safe recovery. |

## Recording standard

Recommended terminal size: `110x32`.

```bash
asciinema rec assets/asciinema/uc-001-reality-to-evidence.cast \
  --cols 110 \
  --rows 32 \
  --command "bash demos/uc-001-reality-to-evidence.sh"
```

Recordings must:

- contain no credentials, customer data or private inventory,
- use deterministic demo fixtures,
- be reproducible from a clean checkout,
- clearly separate observation from mutation,
- show human approval before any state-changing action.

## Rendering

A `.cast` file remains the canonical source. Derived assets may be generated with tools such as `agg` or `asciicast2gif`.

```bash
agg assets/asciinema/uc-001-reality-to-evidence.cast \
    assets/asciinema/uc-001-reality-to-evidence.gif
```

The long-term goal is to reuse these scenarios as documentation, onboarding, regression examples and interactive CyberCore Learn modules.
