from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from enum import Enum


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitBreaker:
    """Failure-rate circuit breaker with CLOSED/OPEN/HALF_OPEN states."""

    failure_threshold: float = 0.5
    rolling_window: float = 10.0
    min_calls: int = 10
    open_timeout: float = 5.0

    state: CircuitState = CircuitState.CLOSED
    _open_until: float = 0.0
    _half_open_trial_in_flight: bool = False
    _samples: deque[tuple[float, bool]] = field(default_factory=deque)

    def allow_request(self, now: float) -> bool:
        if self.state == CircuitState.OPEN:
            if now >= self._open_until:
                self.state = CircuitState.HALF_OPEN
                self._half_open_trial_in_flight = False
            else:
                return False

        if self.state == CircuitState.HALF_OPEN:
            if self._half_open_trial_in_flight:
                return False
            self._half_open_trial_in_flight = True
            return True

        return True

    def record(self, now: float, success: bool) -> None:
        if self.state == CircuitState.HALF_OPEN:
            self._half_open_trial_in_flight = False
            if success:
                self.state = CircuitState.CLOSED
                self._samples.clear()
            else:
                self.state = CircuitState.OPEN
                self._open_until = now + self.open_timeout
            return

        if self.state == CircuitState.OPEN:
            return

        self._samples.append((now, success))
        self._trim_window(now)
        if len(self._samples) < self.min_calls:
            return

        failures = sum(1 for _, ok in self._samples if not ok)
        failure_rate = failures / len(self._samples)
        if failure_rate >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self._open_until = now + self.open_timeout

    def _trim_window(self, now: float) -> None:
        while self._samples and (now - self._samples[0][0]) > self.rolling_window:
            self._samples.popleft()
