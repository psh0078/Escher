from __future__ import annotations

import unittest

from experiments.runners.smoke_runner import SmokeScenario, run_scenario


class SmokeRunnerTests(unittest.TestCase):
    def test_deterministic_outputs_with_same_seed(self) -> None:
        scenario = SmokeScenario(
            duration=30.0,
            request_interval=0.5,
            dependency_latency=0.2,
            dependency_failure_probability=0.2,
            outage_start=10.0,
            outage_end=12.0,
            retry_max_attempts=3,
            breaker_failure_threshold=0.5,
            breaker_window=5.0,
            breaker_min_calls=8,
            breaker_open_timeout=2.0,
            connection_limit=10,
            seed=123,
        )

        result_a = run_scenario(scenario)
        result_b = run_scenario(scenario)

        self.assertEqual(result_a.completed, result_b.completed)
        self.assertEqual(result_a.failed, result_b.failed)
        self.assertEqual(result_a.latencies, result_b.latencies)

    def test_stress_more_than_100k_events(self) -> None:
        scenario = SmokeScenario(
            duration=50.0,
            request_interval=0.0004,
            dependency_latency=0.0,
            dependency_failure_probability=0.0,
            outage_start=1_000.0,
            outage_end=1_001.0,
            retry_max_attempts=1,
            breaker_failure_threshold=0.9,
            breaker_window=5.0,
            breaker_min_calls=100,
            breaker_open_timeout=1.0,
            connection_limit=1_000_000,
            seed=1,
        )

        result = run_scenario(scenario)
        self.assertGreater(result.completed, 100_000)
        self.assertEqual(result.failed, 0)


if __name__ == "__main__":
    unittest.main()
