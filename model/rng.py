from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class SeededRng:
    """Single explicit random source for deterministic runs."""

    seed: int

    def __post_init__(self) -> None:
        self._rng = random.Random(self.seed)

    def uniform(self, low: float, high: float) -> float:
        return self._rng.uniform(low, high)

    def random(self) -> float:
        return self._rng.random()
