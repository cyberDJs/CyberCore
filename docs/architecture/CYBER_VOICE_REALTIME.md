# Cyber Voice Realtime Foundation

Status: Foundation implementation
Work block: `WB-0037`
Date: 2026-09-02

## Purpose

WB-0037 adds a provider-neutral realtime audio boundary above the Cyber Voice Foundation.
It accepts bounded PCM audio frames, detects speech, streams frames into STT, converts a
finished transcript into the existing `Utterance` contract, and streams TTS frames back
through a bounded output path.

The realtime layer does not execute CyberCore actions and does not create authority. The
`Utterance` produced by STT enters the existing WB-0036 flow and remains subject to HOWEDO,
OATHDO, CCL approval, execution, and verification boundaries.

## Runtime flow

```text
Microphone / upstream audio adapter
        |
        v
     AudioFrame
        |
        v
       VAD
        |
        v
bounded input buffer
        |
        v
streaming STT
        |
        v
     Utterance
        |
        v
Cyber Voice Foundation
        |
        v
 response text
        |
        v
streaming TTS
        |
        v
bounded output buffer
        |
        v
speaker / realtime transport adapter
```

## Realtime state model

```text
IDLE -> LISTENING -> PROCESSING -> SPEAKING -> IDLE
                     |             |
                     +-------> INTERRUPTED
                                   |
                                   +-------> PROCESSING

Any non-cancelled state -> CANCELLED
```

`CANCELLED` is terminal. `INTERRUPTED` represents a real interruption of the active turn,
not a successful completion.

## Audio contract

The Foundation audio format is explicit, deterministic PCM:

- encoding: `PCM_S16LE`;
- sample rate: carried in `AudioFormat`;
- channel count: carried in `AudioFormat`;
- sample width: two bytes for `PCM_S16LE`;
- sequence number: monotonic ordering is supplied by the upstream adapter;
- capture timestamp: optional and non-authoritative.

`AudioFrame` rejects empty, negative-sequence, and sample-misaligned payloads.

The core does not open microphones, select devices, decode compressed codecs, or persist
recordings. Those responsibilities remain adapter concerns.

## Bounded buffering and backpressure

Both input and output use `BoundedAudioBuffer` with explicit frame and byte limits.

Capacity overflow is fail-closed:

- the incoming frame is rejected;
- queued frames are not overwritten;
- no silent drop-oldest behavior exists;
- input overflow does not forward the rejected frame into STT;
- output overflow cancels synthesis, flushes queued output, and interrupts the turn.

This makes overload observable instead of hiding lost speech or stale audio.

## Adapter boundaries

WB-0037 defines four provider-neutral protocols:

- `VoiceActivityDetector`;
- `StreamingSpeechToText`;
- `StreamingTextToSpeech`;
- `RealtimeAudioTransport`.

`RealtimeSpeechProvider` is an aggregate contract for providers that expose VAD, STT, and
TTS as one integration. CyberCore does not require any specific cloud or local provider.

Adapters must make `reset`, TTS `cancel`, and transport `flush_output` safe to call during
interruption and cancellation paths.

## Barge-in

Speech detected while Cyber Voice is `PROCESSING` or `SPEAKING` is an interruption.

The runtime performs this sequence:

1. cancel active TTS;
2. reset the previous STT turn;
3. flush bounded input and output buffers;
4. request the audio transport to flush already queued output;
5. mark the canonical `VoiceSession` as `INTERRUPTED`;
6. transition realtime state to `INTERRUPTED`;
7. accept the interrupting speech frame as the first frame of the new turn.

Silence or unknown audio received while speaking does not interrupt output.

When the interrupting transcript is finalized, `VoiceSession` resumes to `ACTIVE` and the
realtime state moves to `PROCESSING` with a new `Utterance`.

## Privacy and evidence

WB-0037 keeps raw audio only in bounded in-memory buffers and flushes it after a turn,
interruption, backpressure failure, or cancellation.

Realtime lifecycle events contain operational metadata such as frame sequence, state,
character count, and language. They do not include raw audio or transcript text by default.
The resulting `Utterance` necessarily contains the transcript required by the Foundation
intent path, but persistence of that content is outside this layer.

## Authority boundary

Realtime audio is untrusted input. Neither a voice print, a microphone source, VAD, STT,
TTS, nor a realtime provider grants execution authority.

The complete governed path remains:

```text
Audio -> STT -> Utterance -> Intent -> Plan
      -> HOWEDO -> OATHDO -> CCL approval
      -> existing execution boundary -> verification
```

A spoken approval therefore has exactly the same WB-0036 semantics as typed approval
intent: it cannot mint or replace CyberCore authorization.

## Explicit non-goals

WB-0037 does not add:

- microphone or speaker device discovery;
- wake-word detection;
- noise suppression or echo cancellation implementations;
- compressed audio codecs;
- OpenAI, Whisper, Piper, ElevenLabs, or another provider dependency;
- speaker biometrics or identity assurance;
- recording persistence;
- CASEBOOK/CASER persistence;
- direct terminal, GitHub, Slack, Drive, browser, or infrastructure execution;
- deployment or production mutation.

## Acceptance

WB-0037 is acceptable when:

- audio frames and buffer limits are deterministic;
- idle silence does not create a turn;
- STT can produce the existing `Utterance` contract;
- empty STT results do not leave the runtime stuck in `PROCESSING`;
- TTS output is bounded and transport-neutral;
- speech during processing or speaking produces a real barge-in;
- barge-in cancels TTS and flushes queued output;
- cancellation is terminal and flushes both directions;
- backpressure fails closed without overwriting queued audio;
- realtime events do not persist raw transcript text;
- no new runtime dependency, credential, executor, deployment, or authority path is added.
