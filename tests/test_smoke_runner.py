from __future__ import annotations

import unittest

from experiments.runners.smoke_runner import parse_canonical_config, run_scenario


class SmokeRunnerTests(unittest.TestCase):
    def test_deterministic_outputs_with_same_seed(self) -> None:
        scenario = parse_canonical_config(
            {
                "simulation_metadata": {
                    "name": "deterministic-smoke",
                    "duration": 30.0,
                    "seed": 123,
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
                                        "failure_probability": 0.2,
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
                    {"type": "constant_rate", "target": "gateway.GET", "interval": 0.5}
                ],
                "faultloads": [
                    {
                        "type": "delay_injection",
                        "target": "service1.calc",
                        "start": 10.0,
                        "end": 12.0,
                        "latency": 0.2,
                    }
                ],
                "policies": {
                    "retry": {"max_attempts": 3},
                    "circuit_breaker": {
                        "failure_threshold": 0.5,
                        "rolling_window": 5.0,
                        "min_calls": 8,
                        "open_timeout": 2.0,
                    },
                    "connection_limiter": {"max_inflight": 10},
                },
            }
        )

        result_a = run_scenario(scenario)
        result_b = run_scenario(scenario)

        self.assertEqual(result_a.completed, result_b.completed)
        self.assertEqual(result_a.failed, result_b.failed)
        self.assertEqual(result_a.latencies, result_b.latencies)

    def test_stress_more_than_100k_events(self) -> None:
        scenario = parse_canonical_config(
            {
                "simulation_metadata": {
                    "name": "stress-smoke",
                    "duration": 50.0,
                    "seed": 1,
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
                    {
                        "type": "constant_rate",
                        "target": "gateway.GET",
                        "interval": 0.0004,
                    }
                ],
                "faultloads": [],
                "policies": {
                    "retry": {"max_attempts": 1},
                    "circuit_breaker": {
                        "failure_threshold": 0.9,
                        "rolling_window": 5.0,
                        "min_calls": 100,
                        "open_timeout": 1.0,
                    },
                    "connection_limiter": {"max_inflight": 1000000},
                },
            }
        )

        result = run_scenario(scenario)
        self.assertGreater(result.completed, 100_000)
        self.assertEqual(result.failed, 0)


if __name__ == "__main__":
    unittest.main()
