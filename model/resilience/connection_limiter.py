from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ConnectionLimiter:
    """Simple in-flight cap for dependency calls."""

    max_inflight: int
    inflight: int = 0

    def try_acquire(self) -> bool:
        if self.inflight >= self.max_inflight:
            return False
        self.inflight += 1
        return True

    def release(self) -> None:
        if self.inflight > 0:
            self.inflight -= 1
