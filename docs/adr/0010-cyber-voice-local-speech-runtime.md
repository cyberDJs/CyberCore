# ADR-0010 — Local Speech Runtime for Cyber Voice

Status: Accepted  
Date: 2026-09-02  
Accepted: 2026-09-02  
Authorized by: Jan Kočí  
Work block: `WB-0038`  
Decision readiness: `DECIDED`

## Context

WB-0037 defined a provider-neutral realtime audio boundary, deterministic buffering, and
barge-in semantics, but deliberately did not open a microphone, play speaker audio, or bind
a concrete speech implementation.

Cyber Voice now needs one locally runnable reference implementation that proves those
contracts against real device and speech-library boundaries without making a cloud vendor,
credential, or heavyweight speech dependency part of the CyberCore core runtime.

## Decision

Cyber Voice will add an optional local reference runtime with these boundaries:

```text
sounddevice <-> PCM_S16LE <-> sherpa-onnx <-> RealtimeVoiceRuntime
```

The following rules are binding:

- `sherpa-onnx` and `sounddevice` are optional dependencies under `voice-local`;
- imports remain lazy so the base CyberCore package works without local speech packages;
- configured model files must already exist; CyberCore does not download models;
- sounddevice device discovery and compatibility checks are read-only;
- microphone input remains mono `PCM_S16LE` in this first local implementation;
- streaming transducer STT converts recognized text to the existing `Utterance` contract;
- VITS-compatible TTS emits bounded `AudioFrame` chunks to the existing realtime runtime;
- device overflow or underflow fails closed rather than silently hiding audio loss;
- speaker playback uses the existing WB-0037 transport flush for barge-in;
- no speech component creates, infers, or substitutes CyberCore approval authority;
- no terminal, GitHub, deployment, infrastructure, or provider executor is added.

A thin top-level `cybercore` console router will route only the new `voice` command family
through the local runtime and delegate all other commands to the existing CyberCore entrypoint
before importing the Voice package.

## Alternatives considered

### Make local speech dependencies mandatory

Rejected. Audio and model runtimes are large, platform-sensitive dependencies and should not
be required for headless CyberCore installations.

### Bind the core directly to a cloud realtime API

Rejected. It would introduce credentials, connectivity requirements, vendor session
semantics, and a new trust boundary before the local provider contract is proven.

### Add a second command/execution path inside the speech runtime

Rejected. Speech is an interface, not an execution authority. Tool routing remains a later,
separately governed work block.

### Optional sherpa-onnx plus sounddevice reference implementation

Selected. It proves the existing provider-neutral contracts locally, supports replacement,
and introduces no service account or network dependency.

## Consequences

Positive:

- Cyber Voice can receive microphone audio and play responses locally;
- one reference implementation validates the WB-0037 adapter boundary;
- audio device selection and model paths become explicit configuration;
- local/offline use requires no cloud secret;
- existing barge-in remains authoritative.

Tradeoffs:

- users must install the optional extra and obtain compatible models separately;
- PortAudio availability remains platform-dependent;
- the first VITS adapter generates a TTS utterance synchronously before chunked playback;
- speaker identity and acoustic authentication remain deliberately out of scope.

## Security and privacy invariants

- Audio input is untrusted data, not authentication.
- Spoken approval does not create an `ApprovalGrant`.
- Raw audio is not persisted by WB-0038.
- Model files are local operator-supplied assets and are not fetched automatically.
- No credential or cloud endpoint is configured by the reference runtime.
- No direct executor is added.
- Existing HOWEDO, OATHDO, CCL, execution, and verification boundaries remain unchanged.

## Rollback

Rollback restores the previous console-script entry point, removes the optional `voice-local`
dependency group, and removes the local config, device, provider, runtime, tests, and docs.
No database migration, credential rotation, recording deletion, provider teardown, or
production rollback is required.

## Implementation gate

WB-0038 may implement only the local speech and device adapter slice described here. Model
download management, incremental provider-specific streaming, speaker authentication,
CASEBOOK/CASER persistence, tool routing, deployment, and any new execution authority require
separate work blocks and review.
