from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from core.engine import Engine
from model.rng import SeededRng


@dataclass
class DependencyEndpoint:
    """Represents a dependency with stochastic failures and latency injection.

    Time complexity per call is O(1).
    """

    engine: Engine
    rng: SeededRng
    base_latency: float
    failure_probability: float
    injected_latency: float = 0.0
    injection_start: float | None = None
    injection_end: float | None = None

    def call(self, on_done: Callable[[bool], None]) -> None:
        if self.base_latency < 0:
            msg = "base_latency must be >= 0"
            raise ValueError(msg)

        if self.injected_latency < 0:
            msg = "injected_latency must be >= 0"
            raise ValueError(msg)

        start_time = self.engine.now
        in_injection_window = (
            self.injection_start is not None
            and self.injection_end is not None
            and self.injection_start <= start_time < self.injection_end
        )
        total_latency = self.base_latency + (
            self.injected_latency if in_injection_window else 0.0
        )

        def _finish() -> None:
            success = self.rng.random() >= self.failure_probability
            on_done(success)

        self.engine.schedule(total_latency, _finish)
