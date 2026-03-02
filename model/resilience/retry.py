from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RetryPolicy:
    """Retry policy with bounded attempts and deterministic backoff."""

    max_attempts: int = 3
    base_backoff: float = 0.1
    multiplier: float = 2.0
    max_backoff: float = 2.0

    def backoff_for_attempt(self, attempt: int) -> float:
        """Returns backoff before attempt N, where N starts at 2."""
        if attempt <= 1:
            return 0.0
        value = self.base_backoff * (self.multiplier ** (attempt - 2))
        return min(value, self.max_backoff)
