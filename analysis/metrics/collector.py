from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MetricsCollector:
    """Tracks request-level success and latency metrics."""

    completed: int = 0
    failed: int = 0
    latencies: list[float] = field(default_factory=list)

    def record(self, success: bool, latency: float) -> None:
        self.completed += 1
        if not success:
            self.failed += 1
        self.latencies.append(latency)

    @property
    def success_rate(self) -> float:
        if self.completed == 0:
            return 1.0
        return (self.completed - self.failed) / self.completed

    def percentile(self, p: float) -> float:
        if not self.latencies:
            return 0.0
        samples = sorted(self.latencies)
        idx = int((len(samples) - 1) * p)
        return samples[idx]
