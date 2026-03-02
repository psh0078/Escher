from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ReactiveAutoscaler:
    """Threshold-based autoscaler policy."""

    min_instances: int = 1
    max_instances: int = 20
    upscale_threshold: float = 0.75
    downscale_threshold: float = 0.30
    cooldown: float = 5.0

    last_scale_time: float = -1e18

    def decide(self, now: float, utilization: float, current_instances: int) -> int:
        if now - self.last_scale_time < self.cooldown:
            return current_instances

        next_instances = current_instances
        if (
            utilization > self.upscale_threshold
            and current_instances < self.max_instances
        ):
            next_instances += 1
        elif (
            utilization < self.downscale_threshold
            and current_instances > self.min_instances
        ):
            next_instances -= 1

        if next_instances != current_instances:
            self.last_scale_time = now
        return next_instances
