from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ServiceInstance:
    """A single running instance of a named service."""

    service: str
    instance_id: int
    alive: bool = True
