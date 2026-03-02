from __future__ import annotations

from dataclasses import dataclass, field

import simpy

from core.engine import BaseEngine, EventCallback, ScheduledToken
from core.event_queue import EventQueueObserver


@dataclass
class SimPyEngine(BaseEngine):
    """SimPy-backed implementation of the engine interface."""

    observer: EventQueueObserver = field(default_factory=EventQueueObserver)

    def __post_init__(self) -> None:
        self._env = simpy.Environment()
        self._next_event_id = 1

    @property
    def now(self) -> float:
        return float(self._env.now)

    def schedule(self, delay: float, callback: EventCallback) -> ScheduledToken:
        if delay < 0:
            msg = f"delay must be >= 0, got {delay}"
            raise ValueError(msg)

        event_id = self._next_event_id
        self._next_event_id += 1
        self.observer.on_scheduled()

        def _runner() -> simpy.events.Event:
            yield self._env.timeout(delay)
            self.observer.on_executed(float(self._env.now))
            callback()

        self._env.process(_runner())
        return ScheduledToken(event_id=event_id)

    def run(self, until: float | None = None) -> None:
        if until is None:
            self._env.run()
            return
        if until < self._env.now:
            msg = f"until must be >= now ({self._env.now}), got {until}"
            raise ValueError(msg)
        self._env.run(until=until)
