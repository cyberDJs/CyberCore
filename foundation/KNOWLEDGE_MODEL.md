# CyberCore Knowledge Model

CyberCore treats operational knowledge as a first-class asset.

## Knowledge Block

A Knowledge Block (KB) captures:

- the problem or question,
- observations and evidence,
- interpretation,
- confidence and assumptions,
- decisions and consequences,
- links to related Work Blocks, ADRs, incidents, assets, and services.

A Knowledge Block may exist without implementation.

## Work Block

A Work Block (WB) captures:

- the implementation goal,
- scope and exclusions,
- dependencies,
- files and systems affected,
- verification,
- rollout and rollback,
- result and lessons learned.

A Work Block must reference the knowledge or decision that justifies it.

## Provenance

Knowledge must retain:

- source,
- collection time,
- author or agent,
- environment,
- freshness,
- confidence.

Generated knowledge must be distinguishable from human-authored conclusions.

## Lifecycle

```text
Observation -> Evidence -> Knowledge Block -> Decision -> Work Block -> Verification -> Outcome -> Knowledge update
```

Knowledge is never considered final merely because implementation succeeded. Operational outcomes may confirm, refine, or invalidate it.
