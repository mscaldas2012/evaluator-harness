from __future__ import annotations

import pytest

from evaluator_harness.config import load_project_config
from evaluator_harness.errors import ProviderError
from evaluator_harness.providers.base import ModelRequest
from evaluator_harness.providers.ollama import OllamaProvider


class FakeResponse:
    def __init__(self, payload: dict[str, object]) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict[str, object]:
        return self._payload


class FakeHttpClient:
    def __init__(self, *, payload: dict[str, object] | None = None, error: Exception | None = None) -> None:
        self.payload = payload or {"response": "candidate output"}
        self.error = error
        self.calls: list[dict[str, object]] = []

    def post(self, url: str, *, json: dict[str, object], timeout: float):
        self.calls.append({"url": url, "json": json, "timeout": timeout})
        if self.error is not None:
            raise self.error
        return FakeResponse(self.payload)


def test_ollama_posts_generate_request_and_parses_response() -> None:
    config = load_project_config("configs/projects/rewrite_quality.yaml").candidates[0]
    client = FakeHttpClient(
        payload={
            "response": "local rewrite",
            "total_duration": 2_000_000,
            "prompt_eval_count": 3,
            "eval_count": 5,
        }
    )
    provider = OllamaProvider(config, http_client=client, timeout=7)

    response = provider.generate(ModelRequest(prompt="Rewrite", params={"temperature": 0.2}))

    assert response.output == "local rewrite"
    assert response.latency_ms == 2
    assert response.input_tokens == 3
    assert response.output_tokens == 5
    assert response.cost_usd is None
    assert response.raw["tracing_strategy"] == "manual"
    assert response.raw["manual_fallback_reason"] == "ollama_has_no_langfuse_wrapped_client"
    assert client.calls[0]["json"]["model"] == "llama3"


def test_ollama_records_unavailable_usage_metadata_explicitly() -> None:
    config = load_project_config("configs/projects/rewrite_quality.yaml").candidates[0]
    provider = OllamaProvider(config, http_client=FakeHttpClient())

    response = provider.generate(ModelRequest(prompt="Rewrite", params={}))

    assert response.input_tokens is None
    assert response.output_tokens is None
    assert response.raw["usage_metadata_available"] is False


def test_ollama_timeout_raises_provider_error_with_retry_count() -> None:
    config = load_project_config("configs/projects/rewrite_quality.yaml").candidates[0]
    provider = OllamaProvider(
        config,
        http_client=FakeHttpClient(error=TimeoutError("timeout")),
        max_attempts=2,
    )

    with pytest.raises(ProviderError, match="Ollama provider failed"):
        provider.generate(ModelRequest(prompt="Rewrite", params={}))
