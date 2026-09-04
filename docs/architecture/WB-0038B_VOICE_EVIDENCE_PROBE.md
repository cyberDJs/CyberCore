# WB-0038B Voice Evidence Probe

Status: proposed evidence scaffold  
Work block: `WB-0038B`  
Date: 2026-09-04

## Purpose

WB-0038A intentionally stabilized Local Voice as safe half-duplex: microphone input remains
open and drained during local TTS, but playback-time microphone frames are discarded rather
than treated as interruption evidence.

WB-0038B starts by measuring the missing boundary instead of immediately changing runtime
behavior. The first slice introduces an evidence-only local interruption probe that can
classify playback-time microphone frames as discarded, observed candidate speech, or a
confirmed interrupt when confirmation is explicitly enabled by tests or a future opt-in mode.

## Non-goals

This slice does not:

- enable local full-duplex barge-in by default;
- pass playback-time microphone frames into `RealtimeVoiceRuntime.receive_input()`;
- add acoustic echo cancellation;
- change Voice approval or execution authority;
- download or select speech models;
- persist raw microphone audio;
- alter deployment or production configuration.

## Probe contract

The probe accepts:

- the microphone `AudioFrame` being classified;
- the local VAD result for that frame;
- playback context such as phase, output frame sequence, RMS values and optional echo
  correlation.

It emits structured `LocalInterruptionEvidence` containing:

- frame sequence;
- VAD state;
- playback phase;
- consecutive playback-time speech frame count;
- decision: `discard`, `observe`, or `confirmed_interrupt`;
- reason text suitable for logs and physical acceptance notes;
- optional RMS and echo-correlation measurements.

The default is fail-closed. Candidate speech during playback is reported as `observe`, not as
`confirmed_interrupt`, unless the probe is explicitly constructed with confirmation enabled.

## Expected next slices

1. Wire the probe into a physical diagnostic command or harness that records event metadata,
   not raw audio archives.
2. Measure silent playback, echo-only playback, delayed previous-turn capture and intentional
   human interruption.
3. Add a conservative opt-in Local Voice policy only after false-interrupt cases are separated
   from fresh speech.
4. Keep half-duplex as the default fallback whenever the detector is unavailable, invalid or
   uncertain.

## Acceptance for this scaffold

This PR is acceptable when:

- the new probe has no effect on default Local Voice behavior;
- silence during playback is discarded;
- echo-like speech is discarded and resets the speech run;
- candidate speech is observable without confirming interruption by default;
- confirmed interruption is only possible when explicitly enabled;
- invalid probe settings fail closed;
- no recording persistence, credential, model download, deployment or authority change is
  introduced.
