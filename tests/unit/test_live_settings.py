from __future__ import annotations

import os

import pytest

from evaluator_harness.config import LiveSettings, load_env_file
from evaluator_harness.errors import ConfigError


def test_live_settings_prefers_langfuse_host(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LANGFUSE_HOST", "https://preferred.test")
    monkeypatch.setenv("LANGFUSE_BASE_URL", "https://legacy.test")

    settings = LiveSettings.from_env(load_file=False)

    assert settings.langfuse_host == "https://preferred.test"


def test_live_settings_uses_base_url_alias(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("LANGFUSE_HOST", raising=False)
    monkeypatch.setenv("LANGFUSE_BASE_URL", "https://legacy.test")

    settings = LiveSettings.from_env(load_file=False)

    assert settings.langfuse_host == "https://legacy.test"
    assert os.environ["LANGFUSE_HOST"] == "https://legacy.test"


def test_load_env_file_does_not_override_existing_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("LANGFUSE_HOST", "https://shell.test")

    load_env_file("tests/fixtures/env/langfuse_host.env")

    assert LiveSettings.from_env(load_file=False).langfuse_host == "https://shell.test"


def test_require_langfuse_reports_missing_vars(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST", "LANGFUSE_BASE_URL"):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(ConfigError, match="Missing Langfuse"):
        LiveSettings.from_env(load_file=False).require_langfuse()
