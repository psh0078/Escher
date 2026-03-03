from __future__ import annotations

import csv
from pathlib import Path
from typing import Sequence

from analysis.metrics.collector import MetricsCollector


def export_misim_compatible_csv(
    metrics: MetricsCollector,
    output_dir: Path,
    bin_size: float = 1.0,
) -> list[Path]:
    """Writes a minimal MiSim-like CSV metric set.

    Produces these files:
    - GEN_ALL_SuccessfulRequests.csv
    - GEN_ALL_FailedRequests.csv
    - R[All]_ResponseTimes.csv
    - R[<EndpointRef>]_ResponseTimes.csv
    - S[<ServiceName>]_InstanceCount.csv
    - CB[<BreakerName>]_StateTimeline.csv
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    success_rows, failure_rows = metrics.binned_request_counts(bin_size=bin_size)

    successful_file = output_dir / "GEN_ALL_SuccessfulRequests.csv"
    failed_file = output_dir / "GEN_ALL_FailedRequests.csv"
    response_file = output_dir / "R[All]_ResponseTimes.csv"

    _write_rows(successful_file, success_rows)
    _write_rows(failed_file, failure_rows)
    _write_rows(response_file, metrics.response_time_log)

    artifact_paths: list[Path] = [successful_file, failed_file, response_file]

    for endpoint_ref, rows in sorted(metrics.endpoint_response_time_log.items()):
        path = output_dir / f"R[{endpoint_ref}]_ResponseTimes.csv"
        _write_rows(path, rows)
        artifact_paths.append(path)

    for service_name, rows in sorted(metrics.instance_count_log.items()):
        path = output_dir / f"S[{service_name}]_InstanceCount.csv"
        _write_rows(path, rows)
        artifact_paths.append(path)

    for breaker_name, rows in sorted(metrics.circuit_breaker_state_log.items()):
        path = output_dir / f"CB[{breaker_name}]_StateTimeline.csv"
        _write_rows(path, rows)
        artifact_paths.append(path)

    return artifact_paths


def _write_rows(path: Path, rows: Sequence[tuple[float, object]]) -> None:
    with path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow(["SimulationTime", "Value"])
        for simulation_time, value in rows:
            writer.writerow([simulation_time, value])
