from __future__ import annotations

from evaluator_harness.config import load_project_config
from evaluator_harness.providers.openai_compatible import OpenAICompatibleProvider


def test_secret_values_are_redacted_from_provider_error(monkeypatch) -> None:
    config = load_project_config("configs/projects/rewrite_quality.yaml").baseline
    monkeypatch.setenv("EDAV_TENANT_ID", "tenant")
    monkeypatch.setenv("EDAV_CLIENT_ID", "client")
    monkeypatch.setenv("EDAV_CLIENT_SECRET", "super-secret")
    monkeypatch.setenv("EDAV_SCOPE_TOKEN_AUDIENCE", "scope")
    monkeypatch.setenv("EDAV_SUBSCRIPTION_KEY", "subscription-secret")
    monkeypatch.setenv("EDAV_AZURE_OPENAI_API_VERSION", "2024-12-01-preview")
    monkeypatch.setenv("EDAV_AZURE_OPENAI_ENDPOINT", "https://example.test")

    provider = OpenAICompatibleProvider(config, credential_class=FailingCredential)

    try:
        provider._build_azure_openai_client(timeout=10)
    except Exception as exc:
        message = str(exc)

    assert "super-secret" not in message
    assert "subscription-secret" not in message


def test_api_key_secret_values_are_redacted_from_provider_error(monkeypatch) -> None:
    config = load_project_config(
        "tests/fixtures/projects/valid_mixed_azure_auth_project.yaml"
    ).candidates[0]
    monkeypatch.setenv("MIXED_CANDIDATE_MISTRAL_LARGE_3_API_KEY", "api-secret")
    monkeypatch.setenv(
        "MIXED_CANDIDATE_MISTRAL_LARGE_3_ENDPOINT",
        "https://sensitive.example.test",
    )
    monkeypatch.setenv("MIXED_CANDIDATE_MISTRAL_LARGE_3_API_VERSION", "2024-12-01-preview")
    monkeypatch.setenv("MIXED_CANDIDATE_MISTRAL_LARGE_3_SUBSCRIPTION_KEY", "sub-secret")

    provider = OpenAICompatibleProvider(config)
    message = provider._redact(
        "boom api-secret sub-secret https://sensitive.example.test"
    )

    assert "api-secret" not in message
    assert "sub-secret" not in message
    assert "https://sensitive.example.test" not in message
    assert message.count("[REDACTED]") == 3


class FailingCredential:
    def __init__(self, **_kwargs):
        pass

    def get_token(self, _scope: str):
        raise RuntimeError("boom super-secret subscription-secret")
