from __future__ import annotations

from dataclasses import dataclass

from core.engine import Engine


@dataclass(frozen=True)
class SimulationClock:
    """Read-only view of simulation time."""

    engine: Engine

    @property
    def now(self) -> float:
        return self.engine.now
