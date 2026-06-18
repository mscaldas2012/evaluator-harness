from __future__ import annotations

import pytest

from evaluator_harness.config import load_project_config
from evaluator_harness.errors import ProviderError
from evaluator_harness.providers.base import ModelRequest
from evaluator_harness.providers.openai_compatible import OpenAICompatibleProvider
from evaluator_harness.prompts import RenderedPrompt, RenderedPromptMessage


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
                "trace_name": "test/rewrite-quality/baseline-gpt5.2-dgw-default",
                "parent_observation_id": "abcdef1234567890",
            },
        )
    )

    call = FakeAzureOpenAIWithCompletions.completions.calls[0]
    assert "trace_name" not in call
    assert "trace_id" not in call
    assert "parent_observation_id" not in call
    assert "name" not in call


def test_openai_rest_sends_rendered_role_messages(
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
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return FakeHttpResponse()

    monkeypatch.setattr("httpx.post", fake_post)

    OpenAICompatibleProvider(config, credential_class=FakeCredential).generate(
        ModelRequest(
            prompt="fallback text",
            params={},
            metadata={},
            rendered_prompt=RenderedPrompt(
                shape="messages",
                text="",
                messages=[
                    RenderedPromptMessage(role="system", content="System instructions"),
                    RenderedPromptMessage(role="user", content="User request"),
                ],
            ),
        )
    )

    assert calls[0]["json"]["messages"] == [
        {"role": "system", "content": "System instructions"},
        {"role": "user", "content": "User request"},
    ]


def test_openai_rest_merges_final_assistant_instruction_into_user_message(
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
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return FakeHttpResponse()

    monkeypatch.setattr("httpx.post", fake_post)

    OpenAICompatibleProvider(config, credential_class=FakeCredential).generate(
        ModelRequest(
            prompt="fallback text",
            params={},
            metadata={},
            rendered_prompt=RenderedPrompt(
                shape="messages",
                text="",
                messages=[
                    RenderedPromptMessage(role="system", content="System instructions"),
                    RenderedPromptMessage(role="user", content="User request"),
                    RenderedPromptMessage(role="assistant", content="Output only HTML."),
                ],
            ),
        )
    )

    assert calls[0]["json"]["messages"] == [
        {"role": "system", "content": "System instructions"},
        {
            "role": "user",
            "content": "User request\n\nAssistant response instruction:\nOutput only HTML.",
        },
    ]


def test_openai_sdk_sends_rendered_role_messages(
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

    OpenAICompatibleProvider(
        config,
        credential_class=FakeCredential,
        azure_openai_class=FakeAzureOpenAIWithCompletions,
    ).generate(
        ModelRequest(
            prompt="fallback text",
            params={},
            metadata={},
            rendered_prompt=RenderedPrompt(
                shape="messages",
                text="",
                messages=[
                    RenderedPromptMessage(role="system", content="System instructions"),
                    RenderedPromptMessage(role="user", content="User request"),
                ],
            ),
        )
    )

    call = FakeAzureOpenAIWithCompletions.completions.calls[0]
    assert call["messages"] == [
        {"role": "system", "content": "System instructions"},
        {"role": "user", "content": "User request"},
    ]


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


def test_api_key_auth_uses_api_key_rest_headers_without_token_acquisition(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = load_project_config(
        "tests/fixtures/projects/valid_azure_api_key_candidate.yaml"
    ).candidates[0]
    monkeypatch.setenv("API_KEY_PROJECT_MISTRAL_LARGE_3_API_KEY", "api-secret")
    monkeypatch.setenv("API_KEY_PROJECT_MISTRAL_LARGE_3_ENDPOINT", "https://api.example.test")
    monkeypatch.setenv("API_KEY_PROJECT_MISTRAL_LARGE_3_API_VERSION", "2024-12-01-preview")
    calls: list[dict[str, object]] = []

    class ExplodingCredential:
        def __init__(self, **_kwargs):
            raise AssertionError("tenant/client credentials should not be used")

    class FakeHttpResponse:
        status_code = 200

        def json(self):
            return {
                "id": "api-key-completion-1",
                "choices": [{"message": {"content": "api key ok"}}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 2},
            }

    def fake_post(url, *, headers, json, timeout):
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return FakeHttpResponse()

    monkeypatch.setattr("httpx.post", fake_post)
    provider = OpenAICompatibleProvider(config, credential_class=ExplodingCredential)

    response = provider.generate(ModelRequest(prompt="hello", params={}, metadata={}))

    assert response.output == "api key ok"
    assert response.input_tokens == 3
    assert response.output_tokens == 2
    assert response.raw["completion_id"] == "api-key-completion-1"
    assert response.raw["retry_count"] == 0
    assert calls[0]["url"] == (
        "https://api.example.test/openai/deployments/mistral-large-3/chat/completions"
        "?api-version=2024-12-01-preview"
    )
    assert calls[0]["headers"]["api-key"] == "api-secret"
    assert "Authorization" not in calls[0]["headers"]
    assert "Ocp-Apim-Subscription-Key" not in calls[0]["headers"]
    assert calls[0]["json"]["messages"] == [{"role": "user", "content": "hello"}]
    assert calls[0]["json"]["max_completion_tokens"] == 2048


def test_api_key_auth_uses_full_chat_completions_endpoint_without_azure_path(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = load_project_config(
        "tests/fixtures/projects/valid_azure_api_key_candidate.yaml"
    ).candidates[0]
    monkeypatch.setenv("API_KEY_PROJECT_MISTRAL_LARGE_3_API_KEY", "api-secret")
    monkeypatch.setenv(
        "API_KEY_PROJECT_MISTRAL_LARGE_3_ENDPOINT",
        "https://foundry.example.test/models/chat/completions",
    )
    monkeypatch.setenv("API_KEY_PROJECT_MISTRAL_LARGE_3_API_VERSION", "2024-12-01-preview")
    calls: list[dict[str, object]] = []

    class FakeHttpResponse:
        status_code = 200

        def json(self):
            return {
                "id": "completion-1",
                "choices": [{"message": {"content": "ok"}}],
                "usage": {"prompt_tokens": 3, "completion_tokens": 2},
            }

    def fake_post(url, *, headers, json, timeout):
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return FakeHttpResponse()

    monkeypatch.setattr("httpx.post", fake_post)

    response = OpenAICompatibleProvider(config).generate(
        ModelRequest(prompt="hello", params={}, metadata={})
    )

    assert response.output == "ok"
    assert calls[0]["url"] == "https://foundry.example.test/models/chat/completions"
    assert calls[0]["headers"]["api-key"] == "api-secret"
    assert calls[0]["json"]["model"] == "mistral-large-3"
    assert "api-version" not in calls[0]["url"]


def test_api_key_auth_supports_optional_subscription_key_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = load_project_config(
        "tests/fixtures/projects/valid_mixed_azure_auth_project.yaml"
    ).candidates[0]
    monkeypatch.setenv("MIXED_CANDIDATE_MISTRAL_LARGE_3_API_KEY", "api-secret")
    monkeypatch.setenv("MIXED_CANDIDATE_MISTRAL_LARGE_3_ENDPOINT", "https://api.example.test")
    monkeypatch.setenv("MIXED_CANDIDATE_MISTRAL_LARGE_3_API_VERSION", "2024-12-01-preview")
    monkeypatch.setenv("MIXED_CANDIDATE_MISTRAL_LARGE_3_SUBSCRIPTION_KEY", "sub-secret")
    calls: list[dict[str, object]] = []

    class FakeHttpResponse:
        status_code = 200

        def json(self):
            return {"choices": [{"message": {"content": "ok"}}], "usage": {}}

    def fake_post(url, *, headers, json, timeout):
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        return FakeHttpResponse()

    monkeypatch.setattr("httpx.post", fake_post)

    OpenAICompatibleProvider(config).generate(
        ModelRequest(prompt="hello", params={}, metadata={})
    )

    assert calls[0]["headers"]["api-key"] == "api-secret"
    assert calls[0]["headers"]["Ocp-Apim-Subscription-Key"] == "sub-secret"


def test_api_key_path_falls_back_to_max_completion_tokens(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = load_project_config(
        "tests/fixtures/projects/valid_azure_api_key_candidate.yaml"
    ).candidates[0]
    config = config.model_copy(
        update={
            "parameters": config.parameters.model_copy(
                update={"token_limit_parameter": "max_tokens"}
            )
        }
    )
    monkeypatch.setenv("API_KEY_PROJECT_MISTRAL_LARGE_3_API_KEY", "api-secret")
    monkeypatch.setenv("API_KEY_PROJECT_MISTRAL_LARGE_3_ENDPOINT", "https://api.example.test")
    monkeypatch.setenv("API_KEY_PROJECT_MISTRAL_LARGE_3_API_VERSION", "2024-12-01-preview")
    calls: list[dict[str, object]] = []

    class FakeHttpResponse:
        def __init__(self, *, status_code: int, text: str, payload: dict[str, object]):
            self.status_code = status_code
            self.text = text
            self._payload = payload

        def json(self):
            return self._payload

    def fake_post(url, *, headers, json, timeout):
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        if "max_tokens" in json:
            return FakeHttpResponse(
                status_code=400,
                text="Use max_completion_tokens instead of max_tokens",
                payload={},
            )
        return FakeHttpResponse(
            status_code=200,
            text="",
            payload={"choices": [{"message": {"content": "ok"}}], "usage": {}},
        )

    monkeypatch.setattr("httpx.post", fake_post)

    response = OpenAICompatibleProvider(config).generate(
        ModelRequest(prompt="hello", params={}, metadata={})
    )

    assert response.output == "ok"
    assert "max_tokens" in calls[0]["json"]
    assert "max_completion_tokens" in calls[1]["json"]


def test_api_key_path_falls_back_to_max_tokens_when_max_completion_tokens_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = load_project_config(
        "tests/fixtures/projects/valid_azure_api_key_candidate.yaml"
    ).candidates[0]
    monkeypatch.setenv("API_KEY_PROJECT_MISTRAL_LARGE_3_API_KEY", "api-secret")
    monkeypatch.setenv(
        "API_KEY_PROJECT_MISTRAL_LARGE_3_ENDPOINT",
        "https://foundry.example.test/models/chat/completions",
    )
    monkeypatch.setenv("API_KEY_PROJECT_MISTRAL_LARGE_3_API_VERSION", "2024-12-01-preview")
    calls: list[dict[str, object]] = []

    class FakeHttpResponse:
        def __init__(self, *, status_code: int, text: str, payload: dict[str, object]):
            self.status_code = status_code
            self.text = text
            self._payload = payload

        def json(self):
            return self._payload

    def fake_post(url, *, headers, json, timeout):
        calls.append({"url": url, "headers": headers, "json": json, "timeout": timeout})
        if "max_completion_tokens" in json:
            return FakeHttpResponse(
                status_code=422,
                text="extra_forbidden max_completion_tokens",
                payload={},
            )
        return FakeHttpResponse(
            status_code=200,
            text="",
            payload={"choices": [{"message": {"content": "ok"}}], "usage": {}},
        )

    monkeypatch.setattr("httpx.post", fake_post)

    response = OpenAICompatibleProvider(config).generate(
        ModelRequest(prompt="hello", params={}, metadata={})
    )

    assert response.output == "ok"
    assert "max_completion_tokens" in calls[0]["json"]
    assert "max_tokens" in calls[1]["json"]
    assert "max_completion_tokens" not in calls[1]["json"]


def test_api_key_missing_environment_reports_variable_name(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = load_project_config(
        "tests/fixtures/projects/valid_azure_api_key_candidate.yaml"
    ).candidates[0]
    monkeypatch.delenv("API_KEY_PROJECT_MISTRAL_LARGE_3_API_KEY", raising=False)
    provider = OpenAICompatibleProvider(config, max_attempts=1)

    with pytest.raises(ProviderError, match="API_KEY_PROJECT_MISTRAL_LARGE_3_API_KEY"):
        provider.generate(ModelRequest(prompt="hello", params={}, metadata={}))


def test_provider_instances_do_not_share_resolved_credentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = load_project_config("tests/fixtures/projects/valid_mixed_azure_auth_project.yaml")
    baseline = config.baseline
    candidate = config.candidates[0]
    monkeypatch.setenv("MIXED_BASELINE_AZURE_TENANT_ID", "tenant")
    monkeypatch.setenv("MIXED_BASELINE_AZURE_CLIENT_ID", "client")
    monkeypatch.setenv("MIXED_BASELINE_AZURE_CLIENT_SECRET", "client-secret")
    monkeypatch.setenv("MIXED_BASELINE_AZURE_SCOPE", "scope")
    monkeypatch.setenv("MIXED_BASELINE_AZURE_SUBSCRIPTION_KEY", "baseline-sub")
    monkeypatch.setenv("MIXED_BASELINE_AZURE_API_VERSION", "2024-12-01-preview")
    monkeypatch.setenv("MIXED_BASELINE_AZURE_ENDPOINT", "https://baseline.example.test")
    monkeypatch.setenv("MIXED_CANDIDATE_MISTRAL_LARGE_3_API_KEY", "candidate-key")
    monkeypatch.setenv("MIXED_CANDIDATE_MISTRAL_LARGE_3_ENDPOINT", "https://candidate.example.test")
    monkeypatch.setenv("MIXED_CANDIDATE_MISTRAL_LARGE_3_API_VERSION", "2024-12-01-preview")
    monkeypatch.setenv("MIXED_CANDIDATE_MISTRAL_LARGE_3_SUBSCRIPTION_KEY", "candidate-sub")

    baseline_auth = OpenAICompatibleProvider(
        baseline,
        credential_class=FakeCredential,
    )._azure_auth_config()
    candidate_auth = OpenAICompatibleProvider(candidate)._azure_api_key_auth_config()

    assert baseline_auth["azure_endpoint"] == "https://baseline.example.test"
    assert baseline_auth["subscription_key"] == "baseline-sub"
    assert candidate_auth["azure_endpoint"] == "https://candidate.example.test"
    assert candidate_auth["api_key"] == "candidate-key"
    assert candidate_auth["subscription_key"] == "candidate-sub"
