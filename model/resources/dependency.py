from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from core.engine import Engine
from model.rng import SeededRng


@dataclass
class DependencyEndpoint:
    """Represents a dependency with stochastic failures and fixed latency."""

    engine: Engine
    rng: SeededRng
    base_latency: float
    failure_probability: float
    outage_start: float | None = None
    outage_end: float | None = None

    def call(self, on_done: Callable[[bool], None]) -> None:
        if self.base_latency < 0:
            msg = "base_latency must be >= 0"
            raise ValueError(msg)

        def _finish() -> None:
            now = self.engine.now
            in_outage = (
                self.outage_start is not None
                and self.outage_end is not None
                and self.outage_start <= now < self.outage_end
            )
            if in_outage:
                on_done(False)
                return

            success = self.rng.random() >= self.failure_probability
            on_done(success)

        self.engine.schedule(self.base_latency, _finish)
