from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True)
class ModelRequest:
    prompt: str
    params: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ModelResponse:
    output: str
    latency_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None
    raw: dict[str, Any] = field(default_factory=dict)


class ModelProvider(Protocol):
    def generate(self, request: ModelRequest) -> ModelResponse:
        """Generate a model response for one request."""
