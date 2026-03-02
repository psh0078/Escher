from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from analysis.metrics.exporter import export_misim_compatible_csv
from experiments.runners.smoke_runner import (
    compute_config_hash,
    load_scenario,
    run_from_config,
    run_scenario,
    write_run_artifacts,
)


class RunArtifactsTests(unittest.TestCase):
    def test_writes_required_metadata_fields(self) -> None:
        config_payload = {
            "simulation_metadata": {
                "name": "artifact-test",
                "duration": 10.0,
                "seed": 99,
                "time_unit": "second",
            },
            "services": [
                {
                    "name": "gateway",
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
                    "min_calls": 5,
                    "open_timeout": 1.0,
                },
                "connection_limiter": {"max_inflight": 100},
            },
        }

        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            config_path = tmp_path / "config.json"
            config_path.write_text(json.dumps(config_payload), encoding="utf-8")

            result = run_from_config(config_path)
            metadata_path, metrics_path = write_run_artifacts(
                config_path=config_path,
                result=result,
                output_dir=tmp_path,
                seed=99,
            )

            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
            self.assertEqual(metadata["seed"], 99)
            self.assertEqual(metadata["config_hash"], compute_config_hash(config_path))
            self.assertIn("git_commit_hash", metadata)
            self.assertTrue(metrics_path.exists())

            scenario = load_scenario(config_path)
            metrics = run_scenario(scenario)
            csv_paths = export_misim_compatible_csv(metrics, tmp_path)
            self.assertEqual(len(csv_paths), 5)

            expected_names = {
                "GEN_ALL_SuccessfulRequests.csv",
                "GEN_ALL_FailedRequests.csv",
                "R[All]_ResponseTimes.csv",
                "S[gateway]_InstanceCount.csv",
                "S[service1]_InstanceCount.csv",
            }
            self.assertEqual({path.name for path in csv_paths}, expected_names)

            for csv_path in csv_paths:
                content = csv_path.read_text(encoding="utf-8").splitlines()
                self.assertGreaterEqual(len(content), 1)
                self.assertEqual(content[0], "SimulationTime,Value")


if __name__ == "__main__":
    unittest.main()
