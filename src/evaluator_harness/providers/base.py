from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol

from evaluator_harness.config import ProviderName
from evaluator_harness.errors import ConfigError


@dataclass(frozen=True)
class ModelRequest:
    prompt: str
    params: dict[str, Any]
    metadata: dict[str, Any] = field(default_factory=dict)
    rendered_prompt: Any | None = None


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


def validate_provider_roles(provider: ProviderName, roles: list[str]) -> None:
    if not roles:
        return
    if provider == ProviderName.DRY_RUN:
        return
    if provider == ProviderName.OPENAI_COMPATIBLE:
        unsupported = [role for role in roles if role not in {"system", "user", "assistant"}]
        if unsupported:
            raise ConfigError(
                "Provider openai_compatible cannot faithfully send role labels: "
                + ", ".join(unsupported)
            )
        return
    raise ConfigError(
        f"Provider {provider.value} cannot faithfully send role-based prompts"
    )
