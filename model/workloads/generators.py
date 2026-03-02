from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from core.engine import Engine


@dataclass(frozen=True)
class ConstantRateWorkload:
    """Generates request arrivals every fixed interval."""

    interval: float
    duration: float

    def start(self, engine: Engine, on_arrival: Callable[[float], None]) -> None:
        if self.interval <= 0:
            msg = "interval must be > 0"
            raise ValueError(msg)

        t = 0.0
        while t <= self.duration:
            fire_at = t

            def _emit(ts: float = fire_at) -> None:
                on_arrival(ts)

            engine.schedule(fire_at - engine.now, _emit)
            t += self.interval
