# Cyber Voice Local Speech Runtime

Status: Foundation implementation  
Work block: `WB-0038`  
Date: 2026-09-02

## Purpose

WB-0038 turns the provider-neutral realtime contracts from WB-0037 into a usable local
microphone and speaker runtime without changing CyberCore execution authority.

The reference implementation uses optional `sherpa-onnx` speech adapters and a
`sounddevice` PortAudio transport. Neither package is required by the core CyberCore
installation.

## Runtime flow

```text
local microphone
  -> sounddevice RawInputStream
  -> PCM_S16LE AudioFrame
  -> sherpa Silero VAD
  -> sherpa streaming transducer STT
  -> WB-0037 RealtimeVoiceRuntime
  -> WB-0036 Utterance / Intent / Plan
  -> HOWEDO -> OATHDO -> CCL approval boundary
  -> response text
  -> sherpa VITS TTS
  -> bounded output frames
  -> sounddevice RawOutputStream
  -> local speaker
```

No adapter in this path creates execution authority. A spoken approval remains an approval
intent and is still subject to the existing exact-plan CyberCore approval rules.

## Installation

Local speech dependencies are isolated behind an optional extra:

```bash
python -m pip install -e '.[voice-local]'
```

The extra installs `sherpa-onnx` and `sounddevice`. CyberCore does not automatically
download speech models, create credentials, or select a remote service.

## Configuration

The default configuration path is:

```text
~/.config/cybercore/voice-local.json
```

It can be overridden with `CYBERCORE_VOICE_CONFIG` or `--config`.

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

Unknown configuration keys fail closed. The audio and STT sample rates must match, and the
WB-0038 microphone path is deliberately mono PCM.

## CLI

```bash
cybercore voice devices
cybercore voice doctor --config ~/.config/cybercore/voice-local.json
cybercore voice local --config ~/.config/cybercore/voice-local.json
```

`voice devices` performs read-only PortAudio discovery. `voice doctor` validates optional
packages, model paths, and input/output device settings without downloading or modifying
anything. `voice local` starts the interactive local speech loop.

A thin top-level console-script router handles only the `voice` command family. Every other
command is delegated to the existing CyberCore entrypoint before the Voice package is imported,
preserving the current CLI implementation and keeping local speech code off normal CLI startup.

## Device boundary

`sounddevice` is loaded lazily. Importing `cybercore` or `cybercore.voice` does not require a
working audio device.

Input and output are fail-closed:

- microphone overflow rejects the affected frame instead of hiding audio loss;
- speaker underflow flushes the output stream so stale speech is not replayed;
- a format change reopens the output stream explicitly;
- output flush is used by the existing WB-0037 barge-in path.

## Sherpa adapters

The reference provider implements:

- `SherpaVadAdapter` using Silero VAD;
- `SherpaSttAdapter` using streaming transducer recognition and endpoint detection;
- `SherpaTtsAdapter` using VITS-compatible offline TTS;
- `SherpaSpeechProvider` as the aggregate WB-0037 provider contract.

PCM conversion between CyberCore `PCM_S16LE` frames and normalized floating-point model
samples is explicit and testable.

## Barge-in

Speaker playback is chunked. Between output chunks, the local runtime checks microphone
input. Speech received while WB-0037 is speaking follows the already accepted barge-in
sequence:

1. cancel queued TTS output;
2. reset the previous STT turn;
3. flush CyberCore audio buffers;
4. abort the local speaker output stream;
5. mark `VoiceSession` interrupted;
6. preserve the interrupting frame as the first frame of the next turn.

WB-0038 does not weaken or replace these semantics.

## Privacy and security

- raw microphone audio is not persisted by this layer;
- no recording archive is created;
- no cloud credential is introduced;
- no model is downloaded automatically;
- microphone identity is not user identity;
- speaker output is not proof of authorization;
- STT text is untrusted intent material;
- no shell, GitHub, deployment, provider, or infrastructure executor is added.

## Known first-slice limitation

The reference VITS adapter performs model inference synchronously when a TTS turn starts,
then exposes the generated audio as bounded chunks. Playback is interruptible, but WB-0038
does not yet preempt a TTS inference call that is already running inside the local provider.
A later provider may implement incremental synthesis without changing the WB-0037 contract.

## Acceptance

WB-0038 is acceptable when:

- CyberCore without `voice-local` still imports and existing CLI commands still delegate;
- `cybercore voice devices` lists read-only local audio capabilities;
- `cybercore voice doctor` fails clearly on missing packages, models, or unsupported devices;
- configured microphone frames enter the existing WB-0037 realtime runtime;
- sherpa STT produces the existing `Utterance` contract;
- response text can be rendered to local speaker frames;
- microphone speech during playback triggers the existing barge-in path;
- no model download, recording persistence, credential, execution authority, deployment, or
  production mutation is introduced.
