from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from experiments.runners.benchmark_runner import (
    load_benchmark_suite,
    run_benchmark_suite,
)


class BenchmarkRunnerTests(unittest.TestCase):
    def test_load_and_run_suite(self) -> None:
        config_payload = {
            "simulation_metadata": {
                "name": "benchmark-test",
                "duration": 5.0,
                "seed": 7,
            },
            "services": [
                {
                    "name": "gateway",
                    "instances": 1,
                    "operations": [
                        {
                            "name": "GET",
                            "dependencies": [
                                {
                                    "service": "service1",
                                    "operation": "calc",
                                    "failure_probability": 0.0,
                                }
                            ],
                        }
                    ],
                },
                {
                    "name": "service1",
                    "instances": 1,
                    "operations": [{"name": "calc", "dependencies": []}],
                },
            ],
            "workloads": [
                {"type": "constant_rate", "target": "gateway.GET", "interval": 1.0}
            ],
            "faultloads": [],
            "policies": {
                "retry": {"max_attempts": 1},
                "circuit_breaker": {
                    "failure_threshold": 1.0,
                    "rolling_window": 5.0,
                    "min_calls": 1,
                    "open_timeout": 1.0,
                },
                "connection_limiter": {"max_inflight": 100},
            },
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            config_path = tmp_path / "config.json"
            suite_path = tmp_path / "suite.json"
            output_dir = tmp_path / "benchmark_output"

            config_path.write_text(json.dumps(config_payload), encoding="utf-8")
            suite_path.write_text(
                json.dumps(
                    {
                        "suite_name": "test-suite",
                        "output_dir": str(output_dir),
                        "cases": [
                            {
                                "name": "tiny-case",
                                "config_path": str(config_path),
                                "determinism_repeats": 2,
                                "overrides": {},
                            }
                        ],
                    }
                ),
                encoding="utf-8",
            )

            suite = load_benchmark_suite(suite_path)
            report = run_benchmark_suite(suite)

            self.assertEqual(report["suite_name"], "test-suite")
            self.assertEqual(len(report["cases"]), 1)
            self.assertTrue(report["cases"][0]["deterministic"])
            self.assertTrue((output_dir / "benchmark_report.json").exists())


if __name__ == "__main__":
    unittest.main()
