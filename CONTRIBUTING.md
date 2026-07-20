# Contributing

This repository operates as a public framework with private overlays for environment-specific data.

## Rules

- No secrets.
- Keep documentation clear and dated.
- Use issues or roadmap entries for planned work.
- Use architecture decision records for significant decisions.
- Prefer small, reviewable changes.

## Required request format

All project instructions must be submitted in a structured format. This applies to Jan, Eimy and any future contributor.

If someone gives an instruction in an unclear, incomplete or non-standard form, the assistant must not guess. It must reply with the template below and ask the person to fill it in.

### Standard task template

```md
# CyberCore Task Request

## 1. Request title
Short name of the task.

## 2. Requested by
Name: 
Role: 
Date/time: 

## 3. Goal
What should be achieved?

## 4. Context
Why is this needed? What system, domain, service, file or workflow does it affect?

## 5. Scope
In scope:
- 

Out of scope:
- 

## 6. Priority
Choose one:
- P0 Critical: outage, security incident, data loss risk
- P1 High: important project work or near deadline
- P2 Normal: planned roadmap work
- P3 Low: idea, cleanup, improvement

## 7. Deadline
Is there a deadline? If yes, write it here.

## 8. Desired output
Choose all that apply:
- explanation
- command/script
- documentation update
- GitHub issue
- code change
- architecture decision record
- runbook
- roadmap update
- checklist
- other: 

## 9. Constraints
Budget, security limits, access limits, no-go technologies, privacy restrictions.

## 10. Data and access
What information, screenshots, files, URLs or credentials are available?
Never paste secrets directly.

## 11. Acceptance criteria
How do we know this is done?
- 

## 12. Notes
Anything else important?
```

### Short emergency template

Use only for urgent incidents.

```md
# CyberCore Incident Request

## Severity
P0 / P1 / P2

## What is broken?

## Since when?

## Impact
Who or what is affected?

## Last change before problem

## Evidence
Errors, screenshots, logs, URLs.

## What must not be touched?

## Desired action
Investigate / propose fix / prepare command / execute via human approval.
```
