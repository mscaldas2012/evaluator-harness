from __future__ import annotations

from typing import Any

import httpx

from evaluator_harness.config import ModelConfig
from evaluator_harness.errors import FailureContext, ProviderError
from evaluator_harness.providers.base import ModelRequest, ModelResponse


class OllamaProvider:
    def __init__(
        self,
        config: ModelConfig,
        *,
        http_client: Any | None = None,
        timeout: float = 60,
        max_attempts: int = 3,
    ) -> None:
        self.config = config
        self.http_client = http_client or httpx.Client()
        self.timeout = timeout
        self.max_attempts = max(1, max_attempts)

    def generate(self, request: ModelRequest) -> ModelResponse:
        last_error: Exception | None = None
        for attempt in range(1, self.max_attempts + 1):
            try:
                response = self.http_client.post(
                    self._generate_url(),
                    json={
                        "model": self.config.model,
                        "prompt": request.prompt,
                        "stream": False,
                        "options": request.params,
                    },
                    timeout=self.timeout,
                )
                response.raise_for_status()
                payload = response.json()
                output = str(payload.get("response") or "")
                input_tokens = _optional_int(payload.get("prompt_eval_count"))
                output_tokens = _optional_int(payload.get("eval_count"))
                return ModelResponse(
                    output=output,
                    latency_ms=_duration_to_ms(payload.get("total_duration")),
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    cost_usd=None,
                    raw={
                        "retry_count": attempt - 1,
                        "tracing_strategy": "manual",
                        "manual_fallback_reason": "ollama_has_no_langfuse_wrapped_client",
                        "usage_metadata_available": (
                            input_tokens is not None or output_tokens is not None
                        ),
                    },
                )
            except Exception as exc:
                last_error = exc

        raise ProviderError(
            f"Ollama provider failed after {self.max_attempts} attempts: {last_error}",
            context=FailureContext(
                operation="model-generate",
                provider=self.config.provider.value,
                model=self.config.model,
                details={"attempts": self.max_attempts},
            ),
        ) from last_error

    def _generate_url(self) -> str:
        endpoint = self.config.endpoint or "http://localhost:11434"
        return endpoint.rstrip("/") + "/api/generate"


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    return int(value)


def _duration_to_ms(value: object) -> int | None:
    if value is None:
        return None
    return int(int(value) / 1_000_000)
