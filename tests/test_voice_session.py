import pytest

from cybercore.voice.session import SessionStatus, VoiceSession


def test_session_reference_and_interruption_lifecycle() -> None:
    session = VoiceSession("s1")
    session.remember("target", "staging")
    session.mark_intent("intent-1")
    session.interrupt("operator barge-in")

    assert session.resolve("target") == "staging"
    assert session.status is SessionStatus.INTERRUPTED
    assert session.active_intent_id == "intent-1"

    session.resume()
    assert session.status is SessionStatus.ACTIVE
    assert session.interruption_reason is None


def test_cancelled_session_is_terminal() -> None:
    session = VoiceSession("s1")
    session.cancel()

    assert session.status is SessionStatus.CANCELLED
    with pytest.raises(RuntimeError):
        session.resume()
    with pytest.raises(RuntimeError):
        session.remember("target", "prod")
