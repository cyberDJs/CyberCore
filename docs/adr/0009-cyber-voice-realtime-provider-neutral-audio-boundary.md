# ADR-0009 — Provider-Neutral Realtime Audio Boundary for Cyber Voice

Status: Accepted
Date: 2026-09-02
Accepted: 2026-09-02
Authorized by: Jan Kočí
Work block: `WB-0037`
Decision readiness: `DECIDED`

## Context

WB-0036 established Cyber Voice as a governed human operating interface and deliberately
stopped before microphone, streaming speech, TTS, and realtime transport concerns.

The next layer must support natural full-duplex interaction, including interruption, without
turning a speech provider into a privileged runtime or coupling CyberCore to one vendor.
It must also avoid unbounded audio queues, stale playback after interruption, and accidental
persistence of raw recordings.

## Decision

Cyber Voice will use a provider-neutral realtime audio boundary with these contracts:

```text
AudioFrame -> VAD -> bounded input -> streaming STT -> Utterance
text -> streaming TTS -> bounded output -> RealtimeAudioTransport
```

The runtime state model is:

```text
IDLE -> LISTENING -> PROCESSING -> SPEAKING -> IDLE
                     |             |
                     +-------> INTERRUPTED

Any non-cancelled state -> CANCELLED
```

The following rules are binding:

- `PCM_S16LE` is the first deterministic raw-audio contract;
- frame and byte limits are explicit for both directions;
- overflow rejects new audio rather than overwriting queued audio;
- speech detected during `PROCESSING` or `SPEAKING` causes barge-in;
- barge-in cancels TTS, resets the previous STT turn, flushes buffers and transport output,
  and marks the existing `VoiceSession` interrupted;
- idle silence does not start a new turn;
- STT output is converted into the existing WB-0036 `Utterance` contract;
- realtime events contain metadata but no raw audio or transcript text by default;
- provider adapters are optional and independently replaceable;
- realtime input does not change HOWEDO, OATHDO, CCL, execution, or verification authority.

## Alternatives considered

### Direct OpenAI Realtime integration in the core

Rejected. It would make one provider's session, audio, and tool semantics part of the
CyberCore architecture and would complicate local/offline replacement.

### Voice-to-command streaming runtime

Rejected. Streaming speech directly into commands would bypass the intent, plan,
continuity, governance, and approval boundaries established by WB-0036.

### Unbounded queues with drop-oldest behavior

Rejected. Silent audio loss makes transcripts and playback nondeterministic and hides load
problems from operators.

### Provider-neutral bounded duplex contracts

Selected. They preserve replaceability, make interruption testable, and keep authority in
the existing CyberCore control plane.

## Consequences

Positive:

- local and cloud STT/TTS providers can share one contract;
- barge-in has deterministic cancellation and flush semantics;
- audio overload is explicit and testable;
- raw audio does not require persistence;
- WB-0036 governance remains unchanged;
- the same runtime can later support microphone, browser, kiosk, mobile, or remote audio
  transports.

Tradeoffs:

- WB-0037 does not yet open a microphone or produce audible speech on its own;
- echo cancellation and device-level playback flushing remain adapter responsibilities;
- compressed codecs require a later adapter or contract extension;
- asynchronous scheduling and network reconnection policy are deferred until a concrete
  provider/transport implementation requires them.

## Security and privacy invariants

- Audio source identity is not execution authority.
- Speaker biometrics are not introduced by this ADR.
- Raw audio is bounded in memory and not persisted by the core.
- Realtime event metadata must not contain transcript text by default.
- Cancellation and barge-in must flush queued output to prevent stale speech from continuing.
- Output backpressure fails closed by cancelling the active synthesis turn.
- No credential or provider secret is introduced.
- No shell, GitHub, deployment, or infrastructure mutation is authorized.

## Rollback

WB-0037 is an isolated source-level extension. Rollback removes the realtime/audio modules,
exports, tests, and documentation. It requires no database migration, provider rollback,
credential rotation, audio deletion job, or production infrastructure change.

## Implementation gate

A concrete microphone, STT/TTS provider, realtime API, speaker-authentication mechanism,
or production tool router requires a separately reviewed work block. Any change that gives
voice input new authority requires a new governance/security decision rather than an adapter
implementation hidden inside this boundary.
