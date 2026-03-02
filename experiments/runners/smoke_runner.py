from __future__ import annotations

import json
import hashlib
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from analysis.metrics.collector import MetricsCollector
from analysis.metrics.exporter import export_misim_compatible_csv
from core.simpy_engine import SimPyEngine
from model.resources.dependency import DependencyEndpoint
from model.resources.service_graph import DependencySpec, OperationSpec, ServiceGraph
from model.resilience.circuit_breaker import CircuitBreaker
from model.resilience.connection_limiter import ConnectionLimiter
from model.resilience.retry import RetryPolicy
from model.rng import SeededRng
from model.workloads.generators import ConstantRateWorkload


@dataclass(frozen=True)
class KillEvent:
    service: str
    instance_count: int
    at_time: float


@dataclass(frozen=True)
class SmokeScenario:
    duration: float
    request_interval: float
    target_operation_ref: str
    service_graph: ServiceGraph
    initial_instances: dict[str, int]
    kill_events: tuple[KillEvent, ...]
    delay_injections: dict[str, dict[str, float]]
    retry_max_attempts: int
    breaker_failure_threshold: float
    breaker_window: float
    breaker_min_calls: int
    breaker_open_timeout: float
    connection_limit: int
    seed: int
    time_unit: str = "second"


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
    time_unit = str(metadata.get("time_unit", "second"))

    workloads = payload.get("workloads", [])
    if not isinstance(workloads, list):
        raise ValueError("workloads must be a list")
    constant = next((w for w in workloads if w.get("type") == "constant_rate"), None)
    if constant is None:
        raise ValueError("At least one constant_rate workload is required")
    request_interval = _required_float(constant, "interval")
    target_operation_ref = _required_str(constant, "target")

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

    service_graph = _build_service_graph(payload)
    initial_instances = _parse_initial_instances(payload)
    kill_events = _parse_kill_events(payload)
    delay_injections = _parse_delay_injections(payload)
    service_graph.get(target_operation_ref)

    return SmokeScenario(
        duration=duration,
        request_interval=request_interval,
        target_operation_ref=target_operation_ref,
        service_graph=service_graph,
        initial_instances=initial_instances,
        kill_events=kill_events,
        delay_injections=delay_injections,
        retry_max_attempts=int(retry_cfg.get("max_attempts", 3)),
        breaker_failure_threshold=float(breaker_cfg.get("failure_threshold", 0.5)),
        breaker_window=float(breaker_cfg.get("rolling_window", 10.0)),
        breaker_min_calls=int(breaker_cfg.get("min_calls", 10)),
        breaker_open_timeout=float(breaker_cfg.get("open_timeout", 5.0)),
        connection_limit=int(limiter_cfg.get("max_inflight", 100)),
        seed=seed,
        time_unit=time_unit,
    )


def _required_float(payload: dict[str, Any], key: str) -> float:
    if key not in payload:
        raise ValueError(f"Missing required numeric field: {key}")
    return float(payload[key])


def _required_int(payload: dict[str, Any], key: str) -> int:
    if key not in payload:
        raise ValueError(f"Missing required integer field: {key}")
    return int(payload[key])


def _required_str(payload: dict[str, Any], key: str) -> str:
    if key not in payload:
        raise ValueError(f"Missing required string field: {key}")
    return str(payload[key])


def _parse_delay_injections(payload: dict[str, Any]) -> dict[str, dict[str, float]]:
    faultloads = payload.get("faultloads", [])
    if not isinstance(faultloads, list):
        raise ValueError("faultloads must be a list")
    injections: dict[str, dict[str, float]] = {}
    for faultload in faultloads:
        if not isinstance(faultload, dict):
            continue
        if faultload.get("type") != "delay_injection":
            continue
        target = _required_str(faultload, "target")
        injections[target] = {
            "start": float(faultload.get("start", 0.0)),
            "end": float(faultload.get("end", 0.0)),
            "latency": float(faultload.get("latency", 0.0)),
        }
    return injections


def _parse_initial_instances(payload: dict[str, Any]) -> dict[str, int]:
    services = payload.get("services", [])
    if not isinstance(services, list):
        raise ValueError("services must be a list")

    initial_instances: dict[str, int] = {}
    for service in services:
        if not isinstance(service, dict):
            continue
        name = _required_str(service, "name")
        initial_instances[name] = int(service.get("instances", 1))

    if not initial_instances:
        raise ValueError("No services were provided")
    return initial_instances


def _parse_kill_events(payload: dict[str, Any]) -> tuple[KillEvent, ...]:
    faultloads = payload.get("faultloads", [])
    if not isinstance(faultloads, list):
        raise ValueError("faultloads must be a list")

    events: list[KillEvent] = []
    for faultload in faultloads:
        if not isinstance(faultload, dict):
            continue
        if faultload.get("type") != "kill_instance":
            continue

        events.append(
            KillEvent(
                service=_required_str(faultload, "target_service"),
                instance_count=int(faultload.get("instance_count", 1)),
                at_time=float(faultload.get("at", 0.0)),
            )
        )

    return tuple(sorted(events, key=lambda event: event.at_time))


def _build_service_graph(payload: dict[str, Any]) -> ServiceGraph:
    services = payload.get("services", [])
    if not isinstance(services, list):
        raise ValueError("services must be a list")

    operations: dict[str, OperationSpec] = {}

    for service in services:
        if not isinstance(service, dict):
            continue
        service_name = _required_str(service, "name")
        service_operations = service.get("operations", [])
        if not isinstance(service_operations, list):
            raise ValueError("service.operations must be a list")

        for operation in service_operations:
            if not isinstance(operation, dict):
                continue
            operation_name = _required_str(operation, "name")
            dependencies = operation.get("dependencies", [])
            if not isinstance(dependencies, list):
                raise ValueError("operation.dependencies must be a list")

            dep_specs: list[DependencySpec] = []
            for dependency in dependencies:
                if not isinstance(dependency, dict):
                    continue
                dep_specs.append(
                    DependencySpec(
                        target_service=_required_str(dependency, "service"),
                        target_operation=_required_str(dependency, "operation"),
                        failure_probability=float(
                            dependency.get("failure_probability", 0.0)
                        ),
                        latency=float(dependency.get("latency", 0.0)),
                    )
                )

            op_spec = OperationSpec(
                service=service_name,
                operation=operation_name,
                dependencies=tuple(dep_specs),
            )
            operations[op_spec.ref] = op_spec

    if not operations:
        raise ValueError("No operations were parsed from services")
    return ServiceGraph(operations=operations)


def run_scenario(scenario: SmokeScenario) -> MetricsCollector:
    engine = SimPyEngine()
    rng = SeededRng(seed=scenario.seed)
    metrics = MetricsCollector()
    active_instances = dict(scenario.initial_instances)

    for service_name, count in sorted(active_instances.items()):
        metrics.record_instance_count(service_name, count, at_time=engine.now)

    retry_policy = RetryPolicy(max_attempts=scenario.retry_max_attempts)
    breaker = CircuitBreaker(
        failure_threshold=scenario.breaker_failure_threshold,
        rolling_window=scenario.breaker_window,
        min_calls=scenario.breaker_min_calls,
        open_timeout=scenario.breaker_open_timeout,
    )
    limiter = ConnectionLimiter(max_inflight=scenario.connection_limit)

    endpoint_cache: dict[str, DependencyEndpoint] = {}

    def schedule_kill_event(event: KillEvent) -> None:
        def _apply_kill() -> None:
            if event.service not in active_instances:
                return
            new_count = max(0, active_instances[event.service] - event.instance_count)
            active_instances[event.service] = new_count
            metrics.record_instance_count(event.service, new_count, at_time=engine.now)

        engine.schedule(event.at_time - engine.now, _apply_kill)

    for event in scenario.kill_events:
        schedule_kill_event(event)

    def endpoint_for(dependency: DependencySpec) -> DependencyEndpoint:
        key = dependency.target_ref
        if key in endpoint_cache:
            return endpoint_cache[key]

        delay = scenario.delay_injections.get(key, {})
        endpoint = DependencyEndpoint(
            engine=engine,
            rng=rng,
            base_latency=dependency.latency,
            failure_probability=dependency.failure_probability,
            injected_latency=float(delay.get("latency", 0.0)),
            injection_start=float(delay["start"]) if "start" in delay else None,
            injection_end=float(delay["end"]) if "end" in delay else None,
        )
        endpoint_cache[key] = endpoint
        return endpoint

    request_id = 0

    def on_arrival(created_at: float) -> None:
        nonlocal request_id
        request_id += 1

        if not limiter.try_acquire():
            metrics.record(
                success=False, latency=engine.now - created_at, completed_at=engine.now
            )
            return

        max_depth = 64

        def execute_operation(
            operation_ref: str, depth: int, on_done: Callable[[bool], None]
        ) -> None:
            if depth > max_depth:
                on_done(False)
                return

            operation = scenario.service_graph.get(operation_ref)
            if active_instances.get(operation.service, 0) <= 0:
                on_done(False)
                return
            dependencies = operation.dependencies
            dep_index = 0

            def run_next_dependency() -> None:
                nonlocal dep_index
                if dep_index >= len(dependencies):
                    on_done(True)
                    return

                dependency = dependencies[dep_index]
                dep_index += 1

                attempts = 1

                def attempt_dependency_call() -> None:
                    nonlocal attempts
                    if not breaker.allow_request(engine.now):
                        on_done(False)
                        return

                    endpoint = endpoint_for(dependency)

                    def on_transport_done(transport_success: bool) -> None:
                        nonlocal attempts
                        if not transport_success:
                            breaker.record(engine.now, False)
                            attempts += 1
                            if attempts > retry_policy.max_attempts:
                                on_done(False)
                                return
                            backoff = retry_policy.backoff_for_attempt(attempts)
                            engine.schedule(backoff, attempt_dependency_call)
                            return

                        def on_nested_complete(nested_success: bool) -> None:
                            nonlocal attempts
                            breaker.record(engine.now, nested_success)
                            if not nested_success:
                                attempts += 1
                                if attempts > retry_policy.max_attempts:
                                    on_done(False)
                                    return
                                backoff = retry_policy.backoff_for_attempt(attempts)
                                engine.schedule(backoff, attempt_dependency_call)
                                return
                            run_next_dependency()

                        execute_operation(
                            dependency.target_ref, depth + 1, on_nested_complete
                        )

                    endpoint.call(on_transport_done)

                attempt_dependency_call()

            run_next_dependency()

        def on_root_done(success: bool) -> None:
            limiter.release()
            metrics.record(
                success=success,
                latency=engine.now - created_at,
                completed_at=engine.now,
            )

        execute_operation(scenario.target_operation_ref, 0, on_root_done)

    workload = ConstantRateWorkload(
        interval=scenario.request_interval,
        duration=scenario.duration,
    )
    workload.start(engine, on_arrival)
    engine.run(until=scenario.duration)
    return metrics


def run_from_config(path: Path) -> dict[str, float | str]:
    scenario = load_scenario(path)
    metrics = run_scenario(scenario)
    return {
        "completed": float(metrics.completed),
        "failed": float(metrics.failed),
        "success_rate": metrics.success_rate,
        "p50_latency": metrics.percentile(0.50),
        "p95_latency": metrics.percentile(0.95),
        "p99_latency": metrics.percentile(0.99),
        "time_unit": scenario.time_unit,
    }


def compute_config_hash(path: Path) -> str:
    payload = path.read_bytes()
    return hashlib.sha256(payload).hexdigest()


def get_git_commit_hash(repo_root: Path) -> str:
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root,
            check=True,
            capture_output=True,
            text=True,
        )
    except (subprocess.SubprocessError, FileNotFoundError):
        return "unknown"
    return completed.stdout.strip() or "unknown"


def write_run_artifacts(
    *,
    config_path: Path,
    result: dict[str, float | str],
    output_dir: Path,
    seed: int,
) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)

    config_hash = compute_config_hash(config_path)
    repo_root = Path(__file__).resolve().parents[2]
    metadata = {
        "seed": seed,
        "config_path": str(config_path),
        "config_hash": config_hash,
        "git_commit_hash": get_git_commit_hash(repo_root),
    }

    metadata_path = output_dir / "run_metadata.json"
    metrics_path = output_dir / "run_metrics.json"
    metadata_path.write_text(
        json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8"
    )
    metrics_path.write_text(
        json.dumps(result, indent=2, sort_keys=True), encoding="utf-8"
    )
    return metadata_path, metrics_path


def format_human_summary(result: dict[str, float | str], unit: str = "STU") -> str:
    completed = int(float(result["completed"]))
    failed = int(float(result["failed"]))
    success_rate_pct = float(result["success_rate"]) * 100.0
    failure_rate_pct = 100.0 - success_rate_pct
    time_unit = str(result.get("time_unit", "second"))

    lines = [
        "Run Summary",
        f"- Requests completed: {completed}",
        f"- Requests failed: {failed} ({failure_rate_pct:.2f}%)",
        f"- Success rate: {success_rate_pct:.2f}%",
        f"- Time unit mapping: 1 {unit} = 1 {time_unit}",
        f"- Latency p50: {float(result['p50_latency']):.3f} {unit}",
        f"- Latency p95: {float(result['p95_latency']):.3f} {unit}",
        f"- Latency p99: {float(result['p99_latency']):.3f} {unit}",
    ]
    return "\n".join(lines)


if __name__ == "__main__":
    config = Path("experiments/configs/smoke_scenario.json")
    scenario = load_scenario(config)
    metrics = run_scenario(scenario)
    result = {
        "completed": float(metrics.completed),
        "failed": float(metrics.failed),
        "success_rate": metrics.success_rate,
        "p50_latency": metrics.percentile(0.50),
        "p95_latency": metrics.percentile(0.95),
        "p99_latency": metrics.percentile(0.99),
        "time_unit": scenario.time_unit,
    }
    artifacts_dir = Path("analysis/metrics/smoke_run")
    metadata_path, metrics_path = write_run_artifacts(
        config_path=config,
        result=result,
        output_dir=artifacts_dir,
        seed=scenario.seed,
    )
    csv_paths = export_misim_compatible_csv(metrics, artifacts_dir)
    print(format_human_summary(result))
    print(f"- Metadata artifact: {metadata_path}")
    print(f"- Metrics artifact: {metrics_path}")
    print("- MiSim-style CSV artifacts:")
    for csv_path in csv_paths:
        print(f"  - {csv_path}")
    print()
    print("Raw JSON")
    print(json.dumps(result, indent=2, sort_keys=True))
