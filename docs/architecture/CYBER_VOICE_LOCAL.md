# Cyber Voice Local Speech Runtime

Status: Foundation implementation + live acceptance stabilization  
Work blocks: `WB-0038`, `WB-0038A`  
Date: 2026-09-02

## Purpose

WB-0038 turns the provider-neutral realtime contracts from WB-0037 into a usable local
microphone and speaker runtime without changing CyberCore execution authority. The reference
implementation uses optional `sherpa-onnx` speech adapters and a `sounddevice` PortAudio
transport.

WB-0038A is the physical-acceptance stabilization slice. Mac acceptance proved that the local
CoreAudio/TCC microphone path opens, Sherpa inference runs, and local TTS reaches the speaker.
It also exposed four concrete transport problems in sequence:

1. the microphone was opened at the model rate instead of the device-native rate;
2. synchronous VITS generation could starve capture and overflow PortAudio input;
3. delayed previous-turn capture could be misread as playback-time barge-in;
4. the VAD gate clipped the beginning of dictated speech while local playback still
   self-interrupted after a short grace window, including with system output muted.

The stabilization policy is therefore deliberately conservative: preserve the beginning of
input with bounded pre-roll and make the current local speaker path safe half-duplex. Full
duplex barge-in remains a WB-0037 capability, but Local Voice does not enable microphone-driven
barge-in until a reliable fresh-speech/echo boundary is implemented separately.

## Runtime flow

```text
local microphone
  -> sounddevice RawInputStream at native device rate
  -> PCM_S16LE capture
  -> explicit mono resampling to model rate
  -> bounded ~500 ms local pre-roll
  -> Silero VAD onset gate
  -> replay pre-roll + onset frame into WB-0037 LISTENING state
  -> sherpa streaming transducer STT
  -> WB-0036 Utterance / Intent / Plan
  -> HOWEDO -> OATHDO -> CCL approval boundary
  -> response text
  -> sherpa VITS TTS
  -> bounded output frames
  -> sounddevice RawOutputStream
  -> local speaker

while local TTS is generating/playing:
  microphone -> drain for continuity/overflow detection -> discard
```

No adapter in this path creates execution authority. A spoken approval remains untrusted
intent material and is still subject to the existing exact-plan CyberCore approval rules.

## Installation

Local speech dependencies are isolated behind an optional extra:

```bash
python -m pip install -e '.[voice-local]'
```

CyberCore does not automatically download speech models, create credentials, or select a
remote speech service.

## Configuration

Default configuration path:

```text
~/.config/cybercore/voice-local.json
```

It can be overridden with `CYBERCORE_VOICE_CONFIG` or `--config`.

`audio.sample_rate_hz` is the normalized CyberCore/model rate. The selected microphone is
opened at its reported native/default rate and converted to the configured model rate before
VAD or STT receives audio. `audio.sample_rate_hz` must match `stt.sample_rate_hz`.

Example:

```json
{
  "audio": {
    "sample_rate_hz": 16000,
    "channels": 1,
    "block_ms": 80,
    "input_device": null,
    "output_device": null
  },
  "vad": {
    "model": "/models/silero_vad.onnx"
  },
  "stt": {
    "tokens": "/models/stt/tokens.txt",
    "encoder": "/models/stt/encoder.onnx",
    "decoder": "/models/stt/decoder.onnx",
    "joiner": "/models/stt/joiner.onnx",
    "sample_rate_hz": 16000
  },
  "tts": {
    "model": "/models/tts/model.onnx",
    "tokens": "/models/tts/tokens.txt",
    "data_dir": "/models/tts/espeak-ng-data"
  }
}
```

Unknown configuration keys fail closed. The local microphone path remains deliberately mono
PCM.

## CLI

```bash
cybercore voice devices
cybercore voice doctor --config ~/.config/cybercore/voice-local.json
cybercore voice local --config ~/.config/cybercore/voice-local.json
```

`voice devices` performs read-only PortAudio discovery. `voice doctor` validates optional
packages, model paths and selected audio settings, including the native-capture to model-rate
boundary. `voice local` starts the local speech loop and emits concise operator states.

## Native device boundary

WB-0038A separates physical capture rate from canonical model rate:

```text
selected input device native/default rate
  -> RawInputStream
  -> PCM_S16LE mono block
  -> deterministic software resampling
  -> configured audio/model rate
```

String device names must resolve exactly once. Invalid or ambiguous selections fail closed.
Microphone overflow rejects the affected frame instead of hiding loss. A blocking speaker write
may report a transient underflow when the device experiences a gap between writes; Local Voice
records that condition and continues sending the remaining TTS frames. Explicit cancellation or
transport shutdown still flushes the output stream so stale speech is not replayed.

## Input onset and bounded pre-roll

Physical acceptance showed that the first part of dictated phrases was consistently missing.
The previous local path passed each idle frame directly to `RealtimeVoiceRuntime`; idle frames
classified as non-speech were correctly ignored by the generic realtime contract, but that
also meant STT never received the audio immediately before the VAD onset decision. With the
acceptance Silero configuration requiring a minimum speech duration, this produced transcripts
such as `ER`, `'S DOCTOR`, `OR DOCTOR`, and `U` from a longer spoken prompt.

Local Voice now keeps a bounded pre-roll ring of roughly 500 ms while idle. The ring is sized
from `audio.block_ms` and never grows without bound. On VAD speech onset the local runtime:

1. enters the existing WB-0037 `LISTENING` state;
2. resets the concrete local VAD so the gate decision cannot leak detector state into replay;
3. replays the bounded pre-roll in chronological order;
4. appends the speech-onset frame;
5. continues normal streaming STT and endpoint detection.

The pre-roll exists only in memory for the active capture turn. Raw audio is not persisted.
This is an onset-preservation mechanism, not an alternate STT or authority path.

## Synchronous TTS and microphone continuity

The current Sherpa VITS adapter performs model inference synchronously. During that blocking
call the local runtime runs a microphone pump solely to keep physical capture moving and to
surface overflow/failure explicitly. Captured frames from that period are drained and not
replayed as commands or interruption evidence.

The same continuity rule applies for the complete local speaker turn. `SoundDeviceTransport`
continues sending every generated TTS frame while Local Voice drains any available microphone
frames between output writes. This prevents capture backlog without letting delayed capture,
VAD hangover, room noise, or device timing cancel the active response.

## Safe half-duplex local playback

The physical acceptance sequence showed repeated `SPEAKING -> INTERRUPTED` transitions even
with system output volume set to zero. A bounded post-playback grace interval reduced timing
exposure but did not make the interruption signal trustworthy. Continuing to treat one local
VAD speech result as sufficient evidence to cancel TTS would therefore make the local runtime
unreliable.

WB-0038A stabilizes Local Voice as safe half-duplex:

```text
LISTENING / STT                 SPEAKING / TTS
mic -> VAD -> STT               mic -> drain/discard
             |                                |
             v                                v
        whole input turn                whole output turn
```

During local TTS generation and playback:

- the microphone remains open and drained;
- overflow and capture failures remain explicit;
- microphone frames are not passed to `RealtimeVoiceRuntime.receive_input()`;
- local microphone speech therefore cannot auto-cancel the response;
- the complete TTS output is allowed to settle normally.

This does **not** remove or weaken WB-0037's provider-neutral barge-in state machine. The
realtime runtime still supports explicit/fresh barge-in for transports that can provide a
trustworthy interruption signal. This repair changes only the current Local Voice policy.

A future `WB-0038B` should re-enable local full-duplex interruption only with a dedicated
fresh-speech confirmation boundary and, where needed, acoustic echo cancellation or equivalent
echo-aware detection. No AEC capability is claimed here.

## Sherpa adapters

The reference provider implements:

- `SherpaVadAdapter` using Silero VAD;
- `SherpaSttAdapter` using streaming transducer recognition and endpoint detection;
- `SherpaTtsAdapter` using VITS-compatible offline TTS;
- `SherpaSpeechProvider` as the aggregate WB-0037 provider contract.

The small English 20M Zipformer used for live acceptance is only an acceptance asset. Its
observed recognition quality is not production quality and is not claimed as fixed by
WB-0038A. A stronger multilingual/Czech STT provider remains a separate provider decision.

## Physical acceptance evidence

The Mac acceptance sequence established:

- CoreAudio/TCC microphone opening: PASS;
- native 48 kHz capture -> 16 kHz model normalization: PASS;
- Sherpa STT inference: PASS, but tiny-model recognition quality poor;
- Sherpa TTS generation and speaker transport: PASS;
- original synchronous-TTS microphone overflow: reproduced, then removed by live input drain;
- repeated false playback interruption: reproduced both with audible output and with system
  output muted;
- latest pre-stabilization run on the VAD-reset/grace head still clipped dictated onsets and
  repeatedly produced `SPEAKING -> INTERRUPTED`.

Those observations are why this slice prefers deterministic complete turns over pretending the
current local microphone is already a safe full-duplex interruption detector.

## Privacy and security

- raw microphone audio is not persisted;
- pre-roll is bounded and memory-only;
- microphone audio drained during TTS is discarded;
- no recording archive is created;
- no cloud credential is introduced;
- no model is downloaded automatically;
- microphone identity is not user identity;
- STT text is untrusted intent material;
- speaker output is not proof of authorization;
- no shell, GitHub, deployment, provider, or infrastructure executor is added.

## Acceptance

WB-0038A is acceptable when:

- CyberCore without `voice-local` still imports and existing CLI commands still delegate;
- `cybercore voice devices` remains read-only;
- `cybercore voice doctor` reports native capture and model rates;
- native-rate microphone input is normalized into the configured STT/VAD rate;
- idle input pre-roll is bounded to roughly 500 ms;
- STT receives the retained pre-roll plus the speech-onset frame in chronological order;
- synchronous TTS generation cannot starve the microphone without explicit failure;
- microphone input remains drained throughout local playback;
- local microphone frames cannot automatically cancel an active TTS response;
- a complete local TTS response can settle to `IDLE` without false `INTERRUPTED`;
- generic WB-0037 barge-in semantics remain unchanged;
- no local full-duplex/AEC capability is falsely claimed;
- no model download, recording persistence, credential, execution authority, deployment, or
  production mutation is introduced.
