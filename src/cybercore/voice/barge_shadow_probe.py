from __future__ import annotations

import argparse
from pathlib import Path

from cybercore.voice.barge_shadow import BargeInShadowSnapshot, FreshSpeechShadowGate
from cybercore.voice.local_config import LocalVoiceConfig, load_local_voice_config
from cybercore.voice.local_runtime import LocalSpeechRuntime
from cybercore.voice.realtime import RealtimeState


DEFAULT_PROBE_TEXT = (
    "Cyber Voice barge in shadow probe is active. This sentence is intentionally long enough "
    "to create a stable local speaker window. During the first control run, stay silent while "
    "this message plays. During the second run, wait for the message to begin and then say stop "
    "stop stop clearly over the speaker. The shadow detector records evidence only and cannot "
    "cancel playback."
)


class ShadowLocalSpeechRuntime(LocalSpeechRuntime):
    """Local Voice runtime that observes playback-time VAD without interrupting TTS."""

    def __init__(self, **kwargs) -> None:  # type: ignore[no-untyped-def]
        super().__init__(**kwargs)
        self._barge_shadow = FreshSpeechShadowGate()

    @property
    def barge_in_shadow_snapshot(self) -> BargeInShadowSnapshot:
        return self._barge_shadow.snapshot

    def _observe_barge_in_shadow(self, frame) -> None:  # type: ignore[no-untyped-def]
        vad = self.provider.vad.evaluate(frame)
        self._barge_shadow.observe(vad.state, frame_sequence=frame.sequence)

    def _drain_microphone_input(self, reason: str) -> None:
        try:
            while True:
                incoming = self.audio_input.read_frame_if_available()
                if incoming is None:
                    return
                self._observe_barge_in_shadow(incoming)
        except Exception:
            if self.realtime.state is not RealtimeState.CANCELLED:
                self.realtime.cancel(f"microphone input failed while {reason}")
            raise

    def speak(self, text: str) -> bool:
        self._barge_shadow.reset()
        self._reset_vad("WB-0038B shadow playback observation started")
        try:
            return super().speak(text)
        finally:
            if self.realtime.state is not RealtimeState.CANCELLED:
                self._reset_vad("WB-0038B shadow playback observation completed")


def run_barge_in_shadow_probe(
    config: LocalVoiceConfig,
    *,
    actor_id: str = "local-operator",
    probe_text: str = DEFAULT_PROBE_TEXT,
) -> int:
    local = ShadowLocalSpeechRuntime.from_config(config)
    try:
        local.open()
        print("CYBER VOICE SHADOW: LISTENING FOR ARMING UTTERANCE")
        utterance = local.capture_utterance(
            actor_id=actor_id,
            utterance_id=f"shadow:{local.session.session_id}:1",
        )
        if utterance is None:
            print("CYBER VOICE SHADOW: no utterance produced")
            return 2

        print(f"YOU: {utterance.text}")
        print("CYBER VOICE SHADOW: SPEAKING — observation only, interruption disabled")
        interrupted = local.speak(probe_text)
        snapshot = local.barge_in_shadow_snapshot
        status = "CANDIDATE" if snapshot.candidate else "NO-CANDIDATE"
        sequence = (
            str(snapshot.candidate_frame_sequence)
            if snapshot.candidate_frame_sequence is not None
            else "none"
        )
        print(
            "CYBER VOICE SHADOW: "
            f"{status} armed={snapshot.armed} "
            f"silence_frames={snapshot.silence_frames} "
            f"speech_frames={snapshot.speech_frames} "
            f"candidate_frame={sequence}"
        )
        if interrupted:
            print("CYBER VOICE SHADOW: FAIL — playback was interrupted in shadow mode")
            return 3
        return 0
    except KeyboardInterrupt:
        if local.realtime.state is not RealtimeState.CANCELLED:
            local.cancel("keyboard interrupt")
        return 130
    finally:
        local.close()


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m cybercore.voice.barge_shadow_probe",
        description="WB-0038B local microphone barge-in shadow evidence probe",
    )
    parser.add_argument("--config", type=Path)
    parser.add_argument("--actor", default="local-operator")
    parser.add_argument("--text", default=DEFAULT_PROBE_TEXT)
    return parser


def main(arguments: list[str] | None = None) -> int:
    args = _parser().parse_args(arguments)
    config = load_local_voice_config(args.config)
    return run_barge_in_shadow_probe(config, actor_id=args.actor, probe_text=args.text)


if __name__ == "__main__":
    raise SystemExit(main())
