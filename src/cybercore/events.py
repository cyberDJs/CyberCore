from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import logging


class RuntimeEvent(StrEnum):
    VERIFY_STARTED = "VERIFY_STARTED"
    VERIFY_OK = "VERIFY_OK"
    VERIFY_FAILED = "VERIFY_FAILED"
    APPLY_STARTED = "APPLY_STARTED"
    APPLY_OK = "APPLY_OK"
    APPLY_FAILED = "APPLY_FAILED"
    ROLLBACK_STARTED = "ROLLBACK_STARTED"
    ROLLBACK_OK = "ROLLBACK_OK"
    ROLLBACK_FAILED = "ROLLBACK_FAILED"


@dataclass(frozen=True, slots=True)
class EventRecord:
    event: RuntimeEvent
    workblock_id: str
    detail: str = ""


def emit(record: EventRecord) -> None:
    logging.getLogger("cybercore.runtime").info(
        "%s workblock=%s detail=%s",
        record.event,
        record.workblock_id,
        record.detail,
    )
