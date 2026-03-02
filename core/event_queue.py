from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class EventQueueStats:
    """Lightweight queue stats for observability and tests."""

    scheduled_count: int = 0
    executed_count: int = 0
    last_event_time: float = 0.0


@dataclass
class EventQueueObserver:
    """Tracks schedule/execute counts without touching engine internals."""

    stats: EventQueueStats = field(default_factory=EventQueueStats)

    def on_scheduled(self) -> None:
        self.stats.scheduled_count += 1

    def on_executed(self, event_time: float) -> None:
        self.stats.executed_count += 1
        self.stats.last_event_time = event_time
