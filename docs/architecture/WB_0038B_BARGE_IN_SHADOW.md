# WB-0038B — Local Barge-In Shadow Evidence

Status: SHADOW / NO INTERRUPTION AUTHORITY  
Base: `14d4c6c4beb6b03aaedfaf2a76a521a038c98cb1`  
Predecessor: WB-0038A / PR #75 + post-merge repair PR #84

## Goal

Establish a trustworthy local microphone fresh-speech boundary before re-enabling microphone-driven
barge-in during local TTS playback.

WB-0038A intentionally made Local Voice safe half-duplex because one VAD `SPEECH` result during
playback was not trustworthy: physical acceptance reproduced false `SPEAKING -> INTERRUPTED`
transitions, including with system output muted. WB-0038B must therefore collect evidence before it
is allowed to call `RealtimeVoiceRuntime.barge_in()` or pass playback-time microphone frames into the
generic realtime interruption path.

## Stage 1 — shadow-only fresh-speech gate

The first slice is deliberately isolated from `cybercore voice local` and is run as:

```bash
python -m cybercore.voice.barge_shadow_probe \
  --config ~/.config/cybercore/voice-local.json
```

The probe uses the normal local microphone, resampler, VAD, STT, TTS and speaker path, but playback
microphone frames remain observation-only. They are never passed to
`RealtimeVoiceRuntime.receive_input()` and the probe never calls `barge_in()`.

The provisional fresh-speech gate requires:

1. observation starts disarmed;
2. at least two consecutive VAD `SILENCE` frames are observed after playback observation begins;
3. only after that silence boundary can speech arm a candidate;
4. at least three consecutive VAD `SPEECH` frames are required to confirm the candidate;
5. `UNKNOWN` fails closed and forces the gate to re-arm from silence;
6. continuous speech already present when observation starts cannot become a candidate.

At the current 80 ms local block size, the default evidence window is approximately 160 ms of
silence followed by 240 ms of speech. These values are provisional acceptance instrumentation, not
a production barge-in policy.

## Physical A/B acceptance

Run against one exact commit with the same microphone, speaker, volume and room geometry.

### A — control / echo-only

1. Start the shadow probe.
2. Speak one arming utterance so Local Voice reaches the fixed probe TTS message.
3. Stay silent while the complete speaker message plays.
4. Record the final `CYBER VOICE SHADOW` line.

Required result:

```text
NO-CANDIDATE
```

Any candidate during the control run is a false positive and blocks promotion.

### B — intentional fresh speech

1. Start a second shadow probe under the same conditions.
2. Speak one arming utterance.
3. After the speaker message begins, deliberately say `STOP STOP STOP` clearly over playback.
4. Record the final `CYBER VOICE SHADOW` line.

Required result:

```text
CANDIDATE
```

The TTS output must still complete normally because shadow mode has no interruption authority.

## Promotion rule

Stage 1 may progress only when repeated physical A/B runs demonstrate both:

- control specificity: echo-only playback does not produce candidates;
- fresh-speech sensitivity: deliberate speech over playback does produce candidates.

If the control run produces false candidates, WB-0038B must add an echo-aware discriminator or AEC
boundary before any live interruption is enabled. If deliberate speech is not detected, thresholds or
the acoustic strategy may be investigated, but interruption authority remains disabled.

## Explicit non-goals

This slice does not claim:

- acoustic echo cancellation;
- production-ready echo rejection;
- safe microphone-driven full-duplex barge-in;
- STT quality improvements;
- execution or approval authority from speech;
- model downloads, cloud services, credentials, recording persistence, deployment or production
  configuration changes.

Raw microphone audio is not persisted by the probe. The evidence surface is limited to the normal
runtime transcript plus the final bounded shadow-gate state.
