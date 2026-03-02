from __future__ import annotations

import unittest

from core.simpy_engine import SimPyEngine


class SimPyEngineTests(unittest.TestCase):
    def test_zero_events(self) -> None:
        engine = SimPyEngine()
        engine.run(until=10.0)
        self.assertEqual(engine.now, 10.0)

    def test_same_timestamp_order_is_stable(self) -> None:
        engine = SimPyEngine()
        seen: list[str] = []

        engine.schedule(1.0, lambda: seen.append("a"))
        engine.schedule(1.0, lambda: seen.append("b"))
        engine.run(until=2.0)

        self.assertEqual(seen, ["a", "b"])

    def test_long_horizon_event(self) -> None:
        engine = SimPyEngine()
        marker = {"hit": False}
        engine.schedule(100_000.0, lambda: marker.update(hit=True))
        engine.run(until=100_001.0)
        self.assertTrue(marker["hit"])


if __name__ == "__main__":
    unittest.main()
