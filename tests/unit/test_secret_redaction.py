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


class FailingCredential:
    def __init__(self, **_kwargs):
        pass

    def get_token(self, _scope: str):
        raise RuntimeError("boom super-secret subscription-secret")
