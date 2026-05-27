from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from evaluator_harness.providers.base import ModelRequest, ModelResponse


ProviderScenario = Literal["success", "timeout", "rate_limit", "invalid_output", "usage_metadata"]


@dataclass
class FakeModelProvider:
    scenario: ProviderScenario = "success"
    response: ModelResponse | None = None
    calls: list[ModelRequest] = field(default_factory=list)

    def generate(self, request: ModelRequest) -> ModelResponse:
        self.calls.append(request)
        if self.scenario == "timeout":
            raise TimeoutError("provider timeout")
        if self.scenario == "rate_limit":
            raise RuntimeError("provider rate limit")
        if self.scenario == "invalid_output":
            return ModelResponse(output="")
        if self.scenario == "usage_metadata":
            return ModelResponse(
                output="rewritten output",
                latency_ms=123,
                input_tokens=10,
                output_tokens=20,
                cost_usd=0.001,
            )
        if self.response is not None:
            return self.response
        return ModelResponse(output="rewritten output")
