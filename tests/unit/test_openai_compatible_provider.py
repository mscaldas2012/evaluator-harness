from __future__ import annotations

import pytest

from evaluator_harness.config import load_project_config
from evaluator_harness.providers.base import ModelRequest
from evaluator_harness.providers.openai_compatible import OpenAICompatibleProvider


class FakeCredential:
    def __init__(self, *, tenant_id: str, client_id: str, client_secret: str) -> None:
        self.tenant_id = tenant_id
        self.client_id = client_id
        self.client_secret = client_secret

    def get_token(self, scope: str):
        return type("Token", (), {"token": f"token-for-{scope}"})()


class FakeAzureOpenAI:
    def __init__(self, **kwargs):
        self.kwargs = kwargs


class FakeCompletions:
    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        return type(
            "Completion",
            (),
            {
                "id": "completion-1",
                "choices": [
                    type(
                        "Choice",
                        (),
                        {"message": type("Message", (), {"content": "ok"})()},
                    )()
                ],
                "usage": type(
                    "Usage",
                    (),
                    {"prompt_tokens": 2, "completion_tokens": 1},
                )(),
            },
        )()


class FakeRejectsMaxTokensCompletions(FakeCompletions):
    def create(self, **kwargs):
        if "max_tokens" in kwargs:
            self.calls.append(kwargs)
            raise RuntimeError(
                "Unsupported parameter: 'max_tokens' is not supported with this model. "
                "Use 'max_completion_tokens' instead."
            )
        return super().create(**kwargs)


class FakeAzureOpenAIWithCompletions(FakeAzureOpenAI):
    completions = FakeCompletions()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.chat = type(
            "Chat",
            (),
            {"completions": self.__class__.completions},
        )()


class FakeAzureOpenAIRejectsMaxTokens(FakeAzureOpenAIWithCompletions):
    completions = FakeRejectsMaxTokensCompletions()


def test_builds_azure_openai_client_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    config = load_project_config("configs/projects/rewrite_quality.yaml").baseline
    monkeypatch.setenv("EDAV_TENANT_ID", "tenant")
    monkeypatch.setenv("EDAV_CLIENT_ID", "client")
    monkeypatch.setenv("EDAV_CLIENT_SECRET", "secret")
    monkeypatch.setenv("EDAV_SCOPE_TOKEN_AUDIENCE", "scope")
    monkeypatch.setenv("EDAV_SUBSCRIPTION_KEY", "subscription")
    monkeypatch.setenv("EDAV_AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
    monkeypatch.setenv("EDAV_AZURE_OPENAI_ENDPOINT", "https://example.test")

    provider = OpenAICompatibleProvider(
        config,
        credential_class=FakeCredential,
        azure_openai_class=FakeAzureOpenAI,
    )

    client = provider._build_azure_openai_client(timeout=10)

    assert client.kwargs["azure_ad_token"] == "token-for-scope"
    assert client.kwargs["default_headers"]["Ocp-Apim-Subscription-Key"] == "subscription"
    assert client.kwargs["max_retries"] == 0


def test_falls_back_to_max_completion_tokens_for_newer_models(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = load_project_config("configs/projects/rewrite_quality.yaml").baseline
    config = config.model_copy(
        update={
            "parameters": config.parameters.model_copy(
                update={"token_limit_parameter": "max_tokens"}
            )
        }
    )
    monkeypatch.setenv("EDAV_TENANT_ID", "tenant")
    monkeypatch.setenv("EDAV_CLIENT_ID", "client")
    monkeypatch.setenv("EDAV_CLIENT_SECRET", "secret")
    monkeypatch.setenv("EDAV_SCOPE_TOKEN_AUDIENCE", "scope")
    monkeypatch.setenv("EDAV_SUBSCRIPTION_KEY", "subscription")
    monkeypatch.setenv("EDAV_AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
    monkeypatch.setenv("EDAV_AZURE_OPENAI_ENDPOINT", "https://example.test")
    FakeAzureOpenAIRejectsMaxTokens.completions = FakeRejectsMaxTokensCompletions()

    provider = OpenAICompatibleProvider(
        config,
        credential_class=FakeCredential,
        azure_openai_class=FakeAzureOpenAIRejectsMaxTokens,
    )

    response = provider.generate(type("Request", (), {"prompt": "hello"})())

    calls = FakeAzureOpenAIRejectsMaxTokens.completions.calls
    assert response.output == "ok"
    assert "max_tokens" in calls[0]
    assert "max_completion_tokens" in calls[-1]
    assert "max_tokens" not in calls[-1]


def test_uses_configured_max_completion_tokens_without_retry(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = load_project_config("configs/projects/rewrite_quality.yaml").baseline
    config = config.model_copy(
        update={
            "parameters": config.parameters.model_copy(
                update={"token_limit_parameter": "max_completion_tokens"}
            )
        }
    )
    monkeypatch.setenv("EDAV_TENANT_ID", "tenant")
    monkeypatch.setenv("EDAV_CLIENT_ID", "client")
    monkeypatch.setenv("EDAV_CLIENT_SECRET", "secret")
    monkeypatch.setenv("EDAV_SCOPE_TOKEN_AUDIENCE", "scope")
    monkeypatch.setenv("EDAV_SUBSCRIPTION_KEY", "subscription")
    monkeypatch.setenv("EDAV_AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
    monkeypatch.setenv("EDAV_AZURE_OPENAI_ENDPOINT", "https://example.test")
    FakeAzureOpenAIRejectsMaxTokens.completions = FakeRejectsMaxTokensCompletions()

    provider = OpenAICompatibleProvider(
        config,
        credential_class=FakeCredential,
        azure_openai_class=FakeAzureOpenAIRejectsMaxTokens,
    )

    response = provider.generate(type("Request", (), {"prompt": "hello"})())

    calls = FakeAzureOpenAIRejectsMaxTokens.completions.calls
    assert response.output == "ok"
    assert len(calls) == 1
    assert "max_completion_tokens" in calls[0]
    assert "max_tokens" not in calls[0]


def test_does_not_pass_langfuse_tracing_kwargs_to_raw_openai_client(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = load_project_config("configs/projects/rewrite_quality.yaml").baseline
    monkeypatch.setenv("EDAV_TENANT_ID", "tenant")
    monkeypatch.setenv("EDAV_CLIENT_ID", "client")
    monkeypatch.setenv("EDAV_CLIENT_SECRET", "secret")
    monkeypatch.setenv("EDAV_SCOPE_TOKEN_AUDIENCE", "scope")
    monkeypatch.setenv("EDAV_SUBSCRIPTION_KEY", "subscription")
    monkeypatch.setenv("EDAV_AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
    monkeypatch.setenv("EDAV_AZURE_OPENAI_ENDPOINT", "https://example.test")
    FakeAzureOpenAIWithCompletions.completions = FakeCompletions()

    provider = OpenAICompatibleProvider(
        config,
        credential_class=FakeCredential,
        azure_openai_class=FakeAzureOpenAIWithCompletions,
    )

    provider.generate(
        ModelRequest(
            prompt="hello",
            params={},
            metadata={
                "trace_id": "1234567890abcdef1234567890abcdef",
                "trace_name": "test/rewrite-quality/baseline/item-1",
                "parent_observation_id": "abcdef1234567890",
            },
        )
    )

    call = FakeAzureOpenAIWithCompletions.completions.calls[0]
    assert "trace_name" not in call
    assert "trace_id" not in call
    assert "parent_observation_id" not in call
    assert "name" not in call


def test_live_azure_path_uses_rest_not_openai_sdk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = load_project_config("configs/projects/rewrite_quality.yaml").baseline
    monkeypatch.setenv("EDAV_TENANT_ID", "tenant")
    monkeypatch.setenv("EDAV_CLIENT_ID", "client")
    monkeypatch.setenv("EDAV_CLIENT_SECRET", "secret")
    monkeypatch.setenv("EDAV_SCOPE_TOKEN_AUDIENCE", "scope")
    monkeypatch.setenv("EDAV_SUBSCRIPTION_KEY", "subscription")
    monkeypatch.setenv("EDAV_AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
    monkeypatch.setenv("EDAV_AZURE_OPENAI_ENDPOINT", "https://example.test")

    calls: list[dict[str, object]] = []

    class FakeHttpResponse:
        status_code = 200

        def json(self):
            return {
                "id": "completion-1",
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 2, "completion_tokens": 1},
            }

    def fake_post(url, *, headers, json, timeout):
        calls.append(
            {
                "url": url,
                "headers": headers,
                "json": json,
                "timeout": timeout,
            }
        )
        return FakeHttpResponse()

    monkeypatch.setattr("httpx.post", fake_post)
    provider = OpenAICompatibleProvider(
        config,
        credential_class=FakeCredential,
    )

    response = provider.generate(ModelRequest(prompt="hello", params={}, metadata={}))

    assert response.output == "ok"
    assert calls[0]["url"] == (
        f"https://example.test/openai/deployments/{config.model}/chat/completions"
        "?api-version=2024-12-01-preview"
    )
    assert calls[0]["headers"]["Authorization"] == "Bearer token-for-scope"
    assert calls[0]["headers"]["Ocp-Apim-Subscription-Key"] == "subscription"
    assert calls[0]["json"]["messages"] == [{"role": "user", "content": "hello"}]
    assert response.raw["tracing_strategy"] == "manual_langfuse_generation"
