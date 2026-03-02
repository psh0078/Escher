from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
    return parse_canonical_config(payload)


def parse_canonical_config(payload: dict[str, Any]) -> SmokeScenario:
    """Parse canonical experiment schema into the smoke scenario model."""
    metadata = payload.get("simulation_metadata", {})
    if not isinstance(metadata, dict):
        raise ValueError("simulation_metadata must be an object")

    duration = _required_float(metadata, "duration")
    seed = _required_int(metadata, "seed")

    workloads = payload.get("workloads", [])
    if not isinstance(workloads, list):
        raise ValueError("workloads must be a list")
    constant = next((w for w in workloads if w.get("type") == "constant_rate"), None)
    if constant is None:
        raise ValueError("At least one constant_rate workload is required")
    request_interval = _required_float(constant, "interval")

    policies = payload.get("policies", {})
    if not isinstance(policies, dict):
        raise ValueError("policies must be an object")

    retry_cfg = policies.get("retry", {})
    if not isinstance(retry_cfg, dict):
        raise ValueError("policies.retry must be an object")

    breaker_cfg = policies.get("circuit_breaker", {})
    if not isinstance(breaker_cfg, dict):
        raise ValueError("policies.circuit_breaker must be an object")

    limiter_cfg = policies.get("connection_limiter", {})
    if not isinstance(limiter_cfg, dict):
        raise ValueError("policies.connection_limiter must be an object")

    delay = _first_delay_injection(payload)
    dep_cfg = _resolve_dependency_config(payload)
    dependency_failure_probability = float(dep_cfg.get("failure_probability", 0.0))

    return SmokeScenario(
        duration=duration,
        request_interval=request_interval,
        dependency_latency=float(delay.get("latency", 0.0)),
        dependency_failure_probability=dependency_failure_probability,
        outage_start=float(delay.get("start", duration + 1.0)),
        outage_end=float(delay.get("end", duration + 1.0)),
        retry_max_attempts=int(retry_cfg.get("max_attempts", 3)),
        breaker_failure_threshold=float(breaker_cfg.get("failure_threshold", 0.5)),
        breaker_window=float(breaker_cfg.get("rolling_window", 10.0)),
        breaker_min_calls=int(breaker_cfg.get("min_calls", 10)),
        breaker_open_timeout=float(breaker_cfg.get("open_timeout", 5.0)),
        connection_limit=int(limiter_cfg.get("max_inflight", 100)),
        seed=seed,
    )


def _required_float(payload: dict[str, Any], key: str) -> float:
    if key not in payload:
        raise ValueError(f"Missing required numeric field: {key}")
    return float(payload[key])


def _required_int(payload: dict[str, Any], key: str) -> int:
    if key not in payload:
        raise ValueError(f"Missing required integer field: {key}")
    return int(payload[key])


def _first_delay_injection(payload: dict[str, Any]) -> dict[str, Any]:
    faultloads = payload.get("faultloads", [])
    if not isinstance(faultloads, list):
        raise ValueError("faultloads must be a list")
    delay = next((f for f in faultloads if f.get("type") == "delay_injection"), None)
    if delay is None:
        return {}
    if not isinstance(delay, dict):
        raise ValueError("delay_injection entry must be an object")
    return delay


def _resolve_dependency_config(payload: dict[str, Any]) -> dict[str, Any]:
    services = payload.get("services", [])
    if not isinstance(services, list):
        raise ValueError("services must be a list")

    for service in services:
        if not isinstance(service, dict):
            continue
        for operation in service.get("operations", []):
            if not isinstance(operation, dict):
                continue
            dependencies = operation.get("dependencies", [])
            if not isinstance(dependencies, list):
                continue
            if dependencies:
                first = dependencies[0]
                if isinstance(first, dict):
                    return first
    return {}


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
