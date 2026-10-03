from pathlib import Path

from cybercore.voice.local_runtime import _voice_parser


def test_local_voice_intelligence_config_is_explicit_opt_in() -> None:
    args = _voice_parser().parse_args(["voice", "local", "--once"])
    assert args.intelligence_config is None


def test_local_voice_accepts_explicit_intelligence_config() -> None:
    args = _voice_parser().parse_args(
        ["voice", "local", "--intelligence-config", "/tmp/intelligence.json", "--once"]
    )
    assert args.intelligence_config == Path("/tmp/intelligence.json")
