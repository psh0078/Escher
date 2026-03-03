from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class MetricsCollector:
    """Tracks request-level success and latency metrics."""

    completed: int = 0
    failed: int = 0
    latencies: list[float] = field(default_factory=list)
    completion_log: list[tuple[float, bool]] = field(default_factory=list)
    response_time_log: list[tuple[float, float]] = field(default_factory=list)
    endpoint_response_time_log: dict[str, list[tuple[float, float]]] = field(
        default_factory=dict
    )
    instance_count_log: dict[str, list[tuple[float, int]]] = field(default_factory=dict)
    circuit_breaker_state_log: dict[str, list[tuple[float, str]]] = field(
        default_factory=dict
    )

    def record(
        self, success: bool, latency: float, completed_at: float | None = None
    ) -> None:
        self.completed += 1
        if not success:
            self.failed += 1
        self.latencies.append(latency)
        if completed_at is not None:
            self.completion_log.append((completed_at, success))
            self.response_time_log.append((completed_at, latency))

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

    def binned_request_counts(
        self, bin_size: float = 1.0
    ) -> tuple[list[tuple[float, int]], list[tuple[float, int]]]:
        """Returns per-bin successful and failed request counts.

        Time complexity is O(n) over the completion log size.
        """
        if bin_size <= 0:
            raise ValueError("bin_size must be > 0")

        success_bins: dict[int, int] = {}
        failure_bins: dict[int, int] = {}
        for completion_time, success in self.completion_log:
            bucket = int(completion_time // bin_size)
            if success:
                success_bins[bucket] = success_bins.get(bucket, 0) + 1
            else:
                failure_bins[bucket] = failure_bins.get(bucket, 0) + 1

        all_keys = sorted(set(success_bins.keys()) | set(failure_bins.keys()))
        success_rows = [(key * bin_size, success_bins.get(key, 0)) for key in all_keys]
        failure_rows = [(key * bin_size, failure_bins.get(key, 0)) for key in all_keys]
        return success_rows, failure_rows

    def record_instance_count(
        self, service_name: str, count: int, at_time: float
    ) -> None:
        if service_name not in self.instance_count_log:
            self.instance_count_log[service_name] = []
        self.instance_count_log[service_name].append((at_time, count))

    def record_endpoint_response_time(
        self, endpoint_ref: str, latency: float, completed_at: float
    ) -> None:
        if endpoint_ref not in self.endpoint_response_time_log:
            self.endpoint_response_time_log[endpoint_ref] = []
        self.endpoint_response_time_log[endpoint_ref].append((completed_at, latency))

    def record_circuit_breaker_state(
        self, breaker_name: str, state: str, at_time: float
    ) -> None:
        if breaker_name not in self.circuit_breaker_state_log:
            self.circuit_breaker_state_log[breaker_name] = []

        state_log = self.circuit_breaker_state_log[breaker_name]
        if state_log and state_log[-1][1] == state:
            return
        state_log.append((at_time, state))
