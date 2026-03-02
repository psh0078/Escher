from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from analysis.metrics.collector import MetricsCollector
from core.simpy_engine import SimPyEngine
from model.resources.dependency import DependencyEndpoint
from model.resilience.circuit_breaker import CircuitBreaker
from model.resilience.connection_limiter import ConnectionLimiter
from model.resilience.retry import RetryPolicy
from model.rng import SeededRng
from model.workloads.generators import ConstantRateWorkload


@dataclass(frozen=True)
class SmokeScenario:
    duration: float
    request_interval: float
    dependency_latency: float
    dependency_failure_probability: float
    outage_start: float
    outage_end: float
    retry_max_attempts: int
    breaker_failure_threshold: float
    breaker_window: float
    breaker_min_calls: int
    breaker_open_timeout: float
    connection_limit: int
    seed: int


def load_scenario(path: Path) -> SmokeScenario:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return SmokeScenario(**payload)


def run_scenario(scenario: SmokeScenario) -> MetricsCollector:
    engine = SimPyEngine()
    rng = SeededRng(seed=scenario.seed)
    metrics = MetricsCollector()
    retry_policy = RetryPolicy(max_attempts=scenario.retry_max_attempts)
    breaker = CircuitBreaker(
        failure_threshold=scenario.breaker_failure_threshold,
        rolling_window=scenario.breaker_window,
        min_calls=scenario.breaker_min_calls,
        open_timeout=scenario.breaker_open_timeout,
    )
    limiter = ConnectionLimiter(max_inflight=scenario.connection_limit)

    dep = DependencyEndpoint(
        engine=engine,
        rng=rng,
        base_latency=scenario.dependency_latency,
        failure_probability=scenario.dependency_failure_probability,
        outage_start=scenario.outage_start,
        outage_end=scenario.outage_end,
    )

    request_id = 0

    def on_arrival(created_at: float) -> None:
        nonlocal request_id
        request_id += 1

        if not limiter.try_acquire():
            metrics.record(success=False, latency=engine.now - created_at)
            return

        attempts = 1

        def attempt_once() -> None:
            nonlocal attempts
            if not breaker.allow_request(engine.now):
                limiter.release()
                metrics.record(success=False, latency=engine.now - created_at)
                return

            def on_dependency_done(success: bool) -> None:
                nonlocal attempts
                breaker.record(engine.now, success)
                if success:
                    limiter.release()
                    metrics.record(success=True, latency=engine.now - created_at)
                    return

                attempts += 1
                if attempts > retry_policy.max_attempts:
                    limiter.release()
                    metrics.record(success=False, latency=engine.now - created_at)
                    return

                backoff = retry_policy.backoff_for_attempt(attempts)
                engine.schedule(backoff, attempt_once)

            dep.call(on_dependency_done)

        attempt_once()

    workload = ConstantRateWorkload(
        interval=scenario.request_interval,
        duration=scenario.duration,
    )
    workload.start(engine, on_arrival)
    engine.run(until=scenario.duration)
    return metrics


def run_from_config(path: Path) -> dict[str, float]:
    scenario = load_scenario(path)
    metrics = run_scenario(scenario)
    return {
        "completed": float(metrics.completed),
        "failed": float(metrics.failed),
        "success_rate": metrics.success_rate,
        "p50_latency": metrics.percentile(0.50),
        "p95_latency": metrics.percentile(0.95),
        "p99_latency": metrics.percentile(0.99),
    }


if __name__ == "__main__":
    config = Path("experiments/configs/smoke_scenario.json")
    result = run_from_config(config)
    print(json.dumps(result, indent=2, sort_keys=True))
