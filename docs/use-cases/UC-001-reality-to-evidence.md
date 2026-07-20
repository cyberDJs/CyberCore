# UC-001 — Reality to Evidence

## Goal

Demonstrate the first CyberCore loop without mutating infrastructure:

```text
Reality -> Observation -> Evidence -> Knowledge -> Decision Candidate
```

## Story

An operator receives an unknown Linux service environment. CyberCore inspects the environment, records evidence, builds a minimal dependency model and explains whether any action is required.

## Expected terminal flow

```console
$ cybercore doctor
CyberCore runtime: ready
Repository: clean
Mutation policy: human approval required

$ cybercore observe demo/fixtures/web-stack
Observed entities: 4
Observed relationships: 5
Evidence records: 9

$ cybercore explain service:web
State: degraded
Reason: reverse proxy depends on an unhealthy upstream
Confidence: 0.94
Evidence: EV-0001, EV-0004, EV-0007

$ cybercore plan service:web
Decision candidate: restart upstream application
Risk: low
Automatic execution: blocked
Approval required: yes
```

## Learning outcomes

After the demonstration, the viewer should understand that:

- CyberCore starts from observed reality rather than assumptions;
- claims are backed by evidence identifiers;
- relationships provide impact context;
- recommendations are explainable;
- observation and planning do not imply automatic execution;
- mutations remain behind an explicit human gate.

## Safety constraints

This scenario must use only synthetic fixtures. It must not contact production systems or include real hostnames, addresses, credentials, customer names or infrastructure inventory.

## Recording target

- Duration: 35–60 seconds
- Terminal: 110x32
- Pace: readable without pausing
- Output: canonical `.cast`, plus generated GIF/SVG for GitHub

## Future learning module

UC-001 becomes the introductory lesson in **CyberCore Learn / Foundations** and can later include checkpoints asking the learner to identify:

1. the observed entities,
2. the evidence supporting the diagnosis,
3. the proposed decision,
4. the point at which human approval is required.
