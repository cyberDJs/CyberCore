from __future__ import annotations

from dataclasses import dataclass
import logging
from queue import Empty, Full, Queue
from threading import Event, Thread
import time
from typing import Mapping, Protocol

from cybercore.communication.contracts import RoomEvent

WAKE_EVENT_TYPES = frozenset({"message.text", "message.voice.transcript", "task.created"})
_STOP = object()


@dataclass(frozen=True, slots=True)
class WakeRequest:
    wake_id: str
    target: str
    room_id: str
    session_id: str
    event_id: str
    sequence: int
    event_type: str

    @classmethod
    def from_event(cls, event: RoomEvent, *, target: str) -> "WakeRequest":
        return cls(
            wake_id=f"wake:{target}:{event.event_id}",
            target=target,
            room_id=event.room_id,
            session_id=event.session_id,
            event_id=event.event_id,
            sequence=event.sequence,
            event_type=event.event_type,
        )


class WakeSink(Protocol):
    def send(self, request: WakeRequest) -> None: ...


class WakeDispatcher:
    """Best-effort event-driven wake fanout.

    Canonical communication persistence completes before this dispatcher is called.
    Delivery failures are logged and never invalidate the persisted room event.
    """

    def __init__(
        self,
        sinks: Mapping[str, WakeSink],
        *,
        queue_size: int = 256,
    ) -> None:
        if queue_size <= 0:
            raise ValueError("queue_size must be positive")
        self.sinks = dict(sinks)
        self._queue: Queue[WakeRequest | object] = Queue(maxsize=queue_size)
        self._stopped = Event()
        self._thread: Thread | None = None
        self._log = logging.getLogger("cybercore.wake")

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stopped.clear()
        self._thread = Thread(target=self._run, name="cybercore-wake", daemon=True)
        self._thread.start()

    def _targets_for(self, event: RoomEvent) -> tuple[str, ...]:
        if event.event_type not in WAKE_EVENT_TYPES:
            return ()
        if event.target == "*":
            return tuple(sorted(target for target in self.sinks if target != event.actor_id))
        if event.target in self.sinks and event.target != event.actor_id:
            return (event.target,)
        return ()

    def submit(self, event: RoomEvent) -> tuple[WakeRequest, ...]:
        requests = tuple(
            WakeRequest.from_event(event, target=target) for target in self._targets_for(event)
        )
        accepted: list[WakeRequest] = []
        for request in requests:
            try:
                self._queue.put_nowait(request)
                accepted.append(request)
            except Full:
                self._log.warning(
                    "wake queue full target=%s event_id=%s sequence=%s",
                    request.target,
                    request.event_id,
                    request.sequence,
                )
        return tuple(accepted)

    def drain(self, *, timeout_seconds: float = 2.0) -> bool:
        deadline = time.monotonic() + max(0.0, timeout_seconds)
        while time.monotonic() < deadline:
            if self._queue.unfinished_tasks == 0:
                return True
            time.sleep(0.01)
        return self._queue.unfinished_tasks == 0

    def stop(self, *, timeout_seconds: float = 2.0) -> None:
        if self._thread is None:
            return
        try:
            self._queue.put_nowait(_STOP)
        except Full:
            pass
        self._thread.join(timeout=max(0.0, timeout_seconds))
        self._stopped.set()

    def _run(self) -> None:
        while not self._stopped.is_set():
            try:
                item = self._queue.get(timeout=0.2)
            except Empty:
                continue
            try:
                if item is _STOP:
                    return
                if not isinstance(item, WakeRequest):
                    continue
                sink = self.sinks.get(item.target)
                if sink is None:
                    continue
                try:
                    sink.send(item)
                except Exception as exc:
                    self._log.warning(
                        "wake delivery failed target=%s event_id=%s error=%s",
                        item.target,
                        item.event_id,
                        type(exc).__name__,
                    )
            finally:
                self._queue.task_done()
