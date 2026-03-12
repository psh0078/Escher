from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from analysis.metrics.comparison import compare_misim_csv_dirs
from analysis.metrics.exporter import export_misim_compatible_csv
from experiments.runners.smoke_runner import (
    format_human_summary,
    parse_canonical_config,
    run_scenario,
    summarize_metrics,
    write_run_artifacts,
)


@dataclass(frozen=True)
class BenchmarkCase:
    name: str
    config_path: Path
    overrides: dict[str, Any]
    determinism_repeats: int = 1
    misim_csv_dir: Path | None = None


@dataclass(frozen=True)
class BenchmarkSuite:
    suite_name: str
    output_dir: Path
    cases: tuple[BenchmarkCase, ...]


def load_benchmark_suite(path: Path) -> BenchmarkSuite:
    payload = json.loads(path.read_text(encoding="utf-8"))
    suite_name = str(payload.get("suite_name", "escher-benchmark"))
    output_dir = Path(str(payload.get("output_dir", "analysis/metrics/benchmark_run")))

    case_payloads = payload.get("cases", [])
    if not isinstance(case_payloads, list) or not case_payloads:
        raise ValueError("benchmark suite must include a non-empty cases list")

    cases: list[BenchmarkCase] = []
    for item in case_payloads:
        if not isinstance(item, dict):
            continue
        config_path = Path(_required_str(item, "config_path"))
        misim_csv_dir = item.get("misim_csv_dir")
        cases.append(
            BenchmarkCase(
                name=_required_str(item, "name"),
                config_path=config_path,
                overrides=_as_dict(item.get("overrides", {})),
                determinism_repeats=int(item.get("determinism_repeats", 1)),
                misim_csv_dir=Path(str(misim_csv_dir)) if misim_csv_dir else None,
            )
        )

    if not cases:
        raise ValueError("no benchmark cases were parsed")
    return BenchmarkSuite(
        suite_name=suite_name, output_dir=output_dir, cases=tuple(cases)
    )


def run_benchmark_suite(suite: BenchmarkSuite) -> dict[str, Any]:
    suite.output_dir.mkdir(parents=True, exist_ok=True)
    case_reports: list[dict[str, Any]] = []

    for case in suite.cases:
        case_output_dir = suite.output_dir / case.name
        case_output_dir.mkdir(parents=True, exist_ok=True)

        raw_payload = json.loads(case.config_path.read_text(encoding="utf-8"))
        effective_payload = _deep_merge(raw_payload, case.overrides)

        effective_config_path = case_output_dir / "effective_config.json"
        effective_config_path.write_text(
            json.dumps(effective_payload, indent=2, sort_keys=True), encoding="utf-8"
        )

        scenario = parse_canonical_config(effective_payload)

        metrics_runs = []
        runtime_seconds: list[float] = []
        repeats = max(1, case.determinism_repeats)
        for _ in range(repeats):
            started = time.perf_counter()
            metrics = run_scenario(scenario)
            elapsed = time.perf_counter() - started
            runtime_seconds.append(elapsed)
            metrics_runs.append(metrics)

        deterministic = _is_deterministic(metrics_runs)
        metrics = metrics_runs[0]
        summary = summarize_metrics(metrics, time_unit=scenario.time_unit)

        write_run_artifacts(
            config_path=effective_config_path,
            result=summary,
            output_dir=case_output_dir,
            seed=scenario.seed,
        )
        csv_paths = export_misim_compatible_csv(metrics, case_output_dir)

        comparison: dict[str, Any] | None = None
        if case.misim_csv_dir is not None:
            report = compare_misim_csv_dirs(case_output_dir, case.misim_csv_dir)
            comparison = {
                "ok": report.ok,
                "compared_files": report.compared_files,
                "matched_files": report.matched_files,
                "mismatches": [
                    {"file_name": m.file_name, "reason": m.reason}
                    for m in report.mismatches
                ],
            }

        case_reports.append(
            {
                "name": case.name,
                "runtime_seconds": runtime_seconds,
                "throughput_rps": [
                    (metrics.completed / value) if value > 0 else 0.0
                    for value in runtime_seconds
                ],
                "determinism_repeats": repeats,
                "deterministic": deterministic,
                "summary": summary,
                "human_summary": format_human_summary(summary),
                "csv_artifacts": [str(path) for path in csv_paths],
                "comparison": comparison,
            }
        )

    suite_report = {
        "suite_name": suite.suite_name,
        "cases": case_reports,
    }
    report_path = suite.output_dir / "benchmark_report.json"
    report_path.write_text(
        json.dumps(suite_report, indent=2, sort_keys=True), encoding="utf-8"
    )
    return suite_report


def _required_str(payload: dict[str, Any], key: str) -> str:
    if key not in payload:
        raise ValueError(f"missing required field: {key}")
    return str(payload[key])


def _as_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    raise ValueError("overrides must be an object")


def _deep_merge(base: Any, overrides: Any) -> Any:
    if isinstance(base, dict) and isinstance(overrides, dict):
        merged: dict[str, Any] = {k: v for k, v in base.items()}
        for key, value in overrides.items():
            if key in merged:
                merged[key] = _deep_merge(merged[key], value)
            else:
                merged[key] = value
        return merged

    if isinstance(overrides, list):
        return list(overrides)

    return overrides


def _is_deterministic(metrics_runs: list[Any]) -> bool:
    if len(metrics_runs) <= 1:
        return True
    first = metrics_runs[0]
    for other in metrics_runs[1:]:
        if first.completed != other.completed:
            return False
        if first.failed != other.failed:
            return False
        if first.latencies != other.latencies:
            return False
    return True


if __name__ == "__main__":
    suite_path = Path("experiments/configs/benchmark_suite.json")
    report = run_benchmark_suite(load_benchmark_suite(suite_path))
    print(f"Benchmark suite: {report['suite_name']}")
    for case in report["cases"]:
        print(f"- {case['name']}: deterministic={case['deterministic']}")
