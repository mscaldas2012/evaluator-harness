from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FailureContext:
    operation: str
    dataset_item_id: str | None = None
    provider: str | None = None
    model: str | None = None
    details: dict[str, Any] | None = None


class HarnessError(Exception):
    """Base exception for expected user-facing harness failures."""

    def __init__(self, message: str, *, context: FailureContext | None = None) -> None:
        super().__init__(message)
        self.context = context


class ConfigError(HarnessError):
    """Project configuration is invalid."""


class RuntimeDependencyError(HarnessError):
    """An external runtime dependency failed or is unavailable."""


class ProviderError(HarnessError):
    """A model provider call failed."""


class LangfuseError(HarnessError):
    """A Langfuse operation failed."""
