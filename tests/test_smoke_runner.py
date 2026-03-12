from __future__ import annotations

import unittest

from experiments.runners.smoke_runner import parse_canonical_config, run_scenario


class SmokeRunnerTests(unittest.TestCase):
    def test_rejects_negative_duration_and_interval(self) -> None:
        with self.assertRaises(ValueError):
            parse_canonical_config(
                {
                    "simulation_metadata": {"duration": -1.0, "seed": 1},
                    "services": [
                        {
                            "name": "gateway",
                            "operations": [{"name": "GET", "dependencies": []}],
                        }
                    ],
                    "workloads": [
                        {
                            "type": "constant_rate",
                            "target": "gateway.GET",
                            "interval": 1.0,
                        }
                    ],
                    "faultloads": [],
                    "policies": {},
                }
            )

        with self.assertRaises(ValueError):
            parse_canonical_config(
                {
                    "simulation_metadata": {"duration": 1.0, "seed": 1},
                    "services": [
                        {
                            "name": "gateway",
                            "operations": [{"name": "GET", "dependencies": []}],
                        }
                    ],
                    "workloads": [
                        {
                            "type": "constant_rate",
                            "target": "gateway.GET",
                            "interval": 0.0,
                        }
                    ],
                    "faultloads": [],
                    "policies": {},
                }
            )

    def test_rejects_invalid_faultload_timings(self) -> None:
        with self.assertRaises(ValueError):
            parse_canonical_config(
                {
                    "simulation_metadata": {"duration": 10.0, "seed": 1},
                    "services": [
                        {
                            "name": "gateway",
                            "operations": [
                                {
                                    "name": "GET",
                                    "dependencies": [
                                        {"service": "service1", "operation": "calc"}
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
                            "interval": 1.0,
                        }
                    ],
                    "faultloads": [
                        {
                            "type": "delay_injection",
                            "target": "service1.calc",
                            "start": 5.0,
                            "end": 4.0,
                            "latency": 0.1,
                        }
                    ],
                    "policies": {},
                }
            )

    def test_kill_and_summon_instance_faultloads_update_timeline(self) -> None:
        scenario = parse_canonical_config(
            {
                "simulation_metadata": {
                    "name": "kill-and-summon-smoke",
                    "duration": 10.0,
                    "seed": 11,
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
                        "instances": 2,
                        "operations": [{"name": "calc", "dependencies": []}],
                    },
                ],
                "workloads": [
                    {"type": "constant_rate", "target": "gateway.GET", "interval": 1.0}
                ],
                "faultloads": [
                    {
                        "type": "kill_instance",
                        "target_service": "service1",
                        "instance_count": 1,
                        "at": 4.0,
                    },
                    {
                        "type": "summon_instance",
                        "target_service": "service1",
                        "instance_count": 2,
                        "at": 8.0,
                    },
                ],
                "policies": {
                    "retry": {"max_attempts": 1},
                    "circuit_breaker": {
                        "failure_threshold": 1.0,
                        "rolling_window": 5.0,
                        "min_calls": 1,
                        "open_timeout": 1.0,
                    },
                    "connection_limiter": {"max_inflight": 10},
                },
            }
        )

        result = run_scenario(scenario)
        self.assertEqual(
            result.instance_count_log["service1"],
            [(0.0, 2), (4.0, 1), (8.0, 3)],
        )

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

    def test_kill_all_instances_causes_failures(self) -> None:
        scenario = parse_canonical_config(
            {
                "simulation_metadata": {
                    "name": "kill-all-test",
                    "duration": 20.0,
                    "seed": 7,
                },
                "services": [
                    {
                        "name": "gateway",
                        "instances": 2,
                        "operations": [{"name": "GET", "dependencies": []}],
                    }
                ],
                "workloads": [
                    {"type": "constant_rate", "target": "gateway.GET", "interval": 1.0}
                ],
                "faultloads": [
                    {
                        "type": "kill_instance",
                        "target_service": "gateway",
                        "instance_count": 2,
                        "at": 1.5,
                    }
                ],
                "policies": {
                    "retry": {"max_attempts": 1},
                    "circuit_breaker": {
                        "failure_threshold": 1.0,
                        "rolling_window": 60.0,
                        "min_calls": 1000,
                        "open_timeout": 1.0,
                    },
                    "connection_limiter": {"max_inflight": 100},
                },
            }
        )
        result = run_scenario(scenario)
        # Kill fires at t=1.5; requests from t=2 onward (18 arrivals) all fail.
        self.assertGreater(result.failed, 15)
        # Instance count reaches zero after kill.
        self.assertEqual(result.instance_count_log["gateway"][-1][1], 0)

    def test_kill_partial_instances_still_routes(self) -> None:
        scenario = parse_canonical_config(
            {
                "simulation_metadata": {
                    "name": "kill-partial-test",
                    "duration": 20.0,
                    "seed": 5,
                },
                "services": [
                    {
                        "name": "gateway",
                        "instances": 3,
                        "operations": [{"name": "GET", "dependencies": []}],
                    }
                ],
                "workloads": [
                    {"type": "constant_rate", "target": "gateway.GET", "interval": 1.0}
                ],
                "faultloads": [
                    {
                        "type": "kill_instance",
                        "target_service": "gateway",
                        "instance_count": 2,
                        "at": 5.0,
                    }
                ],
                "policies": {
                    "retry": {"max_attempts": 1},
                    "circuit_breaker": {
                        "failure_threshold": 1.0,
                        "rolling_window": 60.0,
                        "min_calls": 1000,
                        "open_timeout": 1.0,
                    },
                    "connection_limiter": {"max_inflight": 100},
                },
            }
        )
        result = run_scenario(scenario)
        # 1 instance remains after kill; load balancer routes all requests to it.
        self.assertEqual(result.failed, 0)
        self.assertEqual(result.instance_count_log["gateway"][-1][1], 1)

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
