from __future__ import annotations

from dataclasses import dataclass

from model.rng import SeededRng


@dataclass
class RoundRobinLoadBalancer:
    """Round-robin instance selector."""

    instance_count: int
    _cursor: int = 0

    def select(self) -> int:
        if self.instance_count <= 0:
            msg = "instance_count must be > 0"
            raise ValueError(msg)
        value = self._cursor % self.instance_count
        self._cursor += 1
        return value


@dataclass
class RandomLoadBalancer:
    """Deterministic random selector via injected seeded RNG."""

    instance_count: int
    rng: SeededRng

    def select(self) -> int:
        if self.instance_count <= 0:
            msg = "instance_count must be > 0"
            raise ValueError(msg)
        return int(self.rng.random() * self.instance_count)
