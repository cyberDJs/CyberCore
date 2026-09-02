# Cyber Voice Foundation

Status: Foundation implementation
Work block: `WB-0036`
Date: 2026-09-02

## Purpose

Cyber Voice is the governed human operating interface for CyberCore. It converts a spoken or text-equivalent utterance into a bounded intent and action request, then routes that request through continuity, governance, approval, and the existing CyberCore execution boundary.

Cyber Voice is not a second agent runtime and it is not an audio provider. Audio capture, speech-to-text, text-to-speech, wake-word detection, speaker recognition, and model-specific realtime APIs are adapters that may be added later.

## Foundation flow

```text
Utterance
  -> Intent Compiler
  -> Session / Context
  -> Action Planner
  -> HOWEDO continuity gate
  -> OATHDO governance gate
  -> CyberCore CCL approval verification
  -> READY for existing execution boundary
  -> external execution / verification lifecycle
```

The Foundation slice stops at `READY`. It does not execute shell commands, mutate GitHub, deploy infrastructure, or create provider credentials.

## Core contracts

### Utterance

An utterance records:

- utterance id;
- voice session id;
- actor id;
- exact text supplied by an upstream text or speech adapter.

### Intent

The Foundation intent vocabulary is:

```text
QUESTION
SEARCH
INSPECT
PLAN
EXECUTE
APPROVE
CANCEL
MONITOR
UNKNOWN
```

The included rule compiler is intentionally small and deterministic. It exists as a testable baseline, not as the final natural-language understanding layer. Future model-backed compilers must produce the same bounded intent contract.

### Session

A voice session keeps only interaction state needed by the interface layer:

- active intent id;
- named references such as the current target;
- `ACTIVE`, `INTERRUPTED`, or `CANCELLED` state;
- an interruption reason.

`CANCELLED` is terminal. Barge-in can move a session to `INTERRUPTED`; resumption must be explicit.

### Action request

An action request carries:

- operation;
- target;
- risk class;
- optional exact plan id and revision;
- explicit scope;
- bounded metadata.

Mutating or consequential actions are never treated as authorized merely because the Voice layer produced them.

## Continuity boundary: HOWEDO

Cyber Voice consumes HOWEDO through a narrow gateway contract. The normalized decisions are:

```text
CONTINUE
PAUSE
REVALIDATE
ABORT
RECOVER
```

Only `CONTINUE` permits the standard Voice routing path to proceed. Every other decision stops ordinary progression so that recovery, revalidation, pause, or abort handling can occur outside the action-ready path.

An absent or unrecognized HOWEDO result fails closed as `ABORT`.

CyberCore does not import HOWEDO as a mandatory runtime dependency in this slice. The gateway is an adapter boundary so HOWEDO can remain independently versioned and testable.

## Governance boundary: OATHDO

Cyber Voice consumes OATHDO through a second narrow gateway contract:

```text
ALLOW
APPROVAL_REQUIRED
DENY
```

An absent or unrecognized result fails closed as `DENY`.

OATHDO may classify governance and authority requirements, but it does not replace CyberCore's canonical mutation approval semantics.

## Canonical approval boundary

CCL-0005 remains authoritative for mutation approval.

A spoken phrase such as "approve this plan" is represented only as a `VoiceApprovalIntent`. The object is bound to:

- actor;
- session and utterance;
- exact plan id;
- exact plan revision;
- requested scope.

`VoiceApprovalIntent.is_authorization` is always false.

The Voice router may mark a mutating action `READY` only when all of the following are true:

1. HOWEDO returns `CONTINUE`;
2. OATHDO does not deny the action;
3. the action is bound to an exact plan id and revision;
4. the existing CyberCore approval verifier confirms a matching active approval.

Voice intent therefore cannot silently mint, infer, or reuse execution authority.

## Event trail

The Foundation emits audit-friendly lifecycle events for:

- utterance receipt;
- intent classification;
- continuity evaluation;
- governance evaluation;
- approval-intent capture;
- blocked actions;
- ready actions;
- cancellation;
- response emission.

The event sink is optional and injected. This keeps the core interface independent of a logging vendor while preserving an observable contract.

## Fail-closed defaults

The default router configuration is deliberately non-operational:

- no action planner -> no bounded action;
- no HOWEDO gateway -> `ABORT`;
- no OATHDO gateway -> `DENY`;
- no CyberCore approval verifier -> mutation remains unapproved.

A fresh `VoiceRouter()` therefore cannot become an accidental execution backdoor.

## Future layers

Deferred from WB-0036:

- microphone and audio-device management;
- voice activity detection and noise suppression;
- streaming STT and TTS;
- wake word and push-to-talk;
- speaker authentication;
- realtime barge-in at the audio transport layer;
- model-backed multilingual intent compilation;
- CASEBOOK/CASER persistence adapters;
- terminal, GitHub, Slack, Drive, browser, and infrastructure tool routers;
- direct execution;
- deployment and production mutation.

These layers must preserve the Foundation contracts instead of bypassing them.

## Security invariants

1. Voice input is untrusted intent, not authority.
2. Mutating actions require exact plan and revision binding.
3. Unknown continuity decisions fail closed.
4. Unknown governance decisions fail closed.
5. No audio or AI provider becomes a required core dependency.
6. Voice may prepare an action but may not bypass CCL approval.
7. `READY` means ready for the existing execution boundary, not executed successfully.
8. Execution success still requires the normal post-change verification and outcome lifecycle.

## Foundation acceptance

WB-0036 Foundation is acceptable when:

- models compile on Python 3.11+;
- session interruption and cancellation are deterministic;
- unknown HOWEDO/OATHDO states fail closed;
- read-only allowed actions can become `READY`;
- mutation cannot become `READY` without matching CCL approval;
- a voice approval phrase is captured as intent only;
- tests cover these invariants without requiring HOWEDO, OATHDO, audio, or model packages.
