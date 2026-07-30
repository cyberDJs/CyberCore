from __future__ import annotations

import logging

from cybercore.events import EventRecord, RuntimeEvent, emit


def test_event_logging_sanitizes_sensitive_detail(caplog) -> None:
    caplog.set_level(logging.INFO, logger="cybercore.runtime")

    emit(
        EventRecord(
            RuntimeEvent.VERIFY_FAILED,
            "WB-TEST",
            (
                "failed at /Users/example/private/CyberCore with "
                "https://token:secret@github.com/cyberDJs/CyberCore.git"
            ),
        )
    )

    output = caplog.text
    assert "VERIFY_FAILED" in output
    assert "WB-TEST" in output
    assert "/Users/example/private/CyberCore" not in output
    assert "token:secret" not in output
