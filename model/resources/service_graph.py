from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DependencySpec:
    """Represents one dependency call from an operation to another."""

    target_service: str
    target_operation: str
    failure_probability: float = 0.0
    latency: float = 0.0

    @property
    def target_ref(self) -> str:
        return f"{self.target_service}.{self.target_operation}"


@dataclass(frozen=True)
class OperationSpec:
    """Operation definition with ordered dependency list."""

    service: str
    operation: str
    dependencies: tuple[DependencySpec, ...]

    @property
    def ref(self) -> str:
        return f"{self.service}.{self.operation}"


@dataclass(frozen=True)
class ServiceGraph:
    """Read-only operation graph for request execution.

    Lookup complexity is O(1) per operation reference.
    """

    operations: dict[str, OperationSpec]

    def get(self, operation_ref: str) -> OperationSpec:
        if operation_ref not in self.operations:
            raise ValueError(f"Unknown operation reference: {operation_ref}")
        return self.operations[operation_ref]
