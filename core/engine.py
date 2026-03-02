from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Callable, Protocol


EventCallback = Callable[[], None]


@dataclass(frozen=True)
class ScheduledToken:
    """Handle returned by the engine when scheduling an event."""

    event_id: int


class Engine(Protocol):
    """Engine interface for all event scheduling and execution."""

    @property
    def now(self) -> float:
        """Current simulation time."""
        ...

    def schedule(self, delay: float, callback: EventCallback) -> ScheduledToken:
        """Schedule callback at now + delay."""
        ...

    def run(self, until: float | None = None) -> None:
        """Advance time and execute scheduled events."""
        ...


class BaseEngine(ABC):
    """Base class for concrete engine implementations."""

    @property
    @abstractmethod
    def now(self) -> float:
        raise NotImplementedError

    @abstractmethod
    def schedule(self, delay: float, callback: EventCallback) -> ScheduledToken:
        raise NotImplementedError

    @abstractmethod
    def run(self, until: float | None = None) -> None:
        raise NotImplementedError
