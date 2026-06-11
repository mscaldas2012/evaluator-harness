from __future__ import annotations

import os
from pathlib import Path

import pytest

from evaluator_harness.config import (
    LiveSettings,
    load_env_file,
    load_layered_env_files,
    project_env_file_path,
)
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


def test_layered_env_files_parse_valid_lines_without_leaking_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in (
        "PROJECT_ENV_SHARED",
        "PROJECT_ENV_ROOT_ONLY",
        "PROJECT_ENV_PROJECT_ONLY",
        "1INVALID",
        "INVALID-NAME",
    ):
        monkeypatch.delenv(name, raising=False)

    result = load_layered_env_files(
        root_env_file="tests/fixtures/env/project_env_root.env",
        project_env_file="tests/fixtures/env/project_env_project.env",
    )

    assert os.getenv("PROJECT_ENV_ROOT_ONLY") == "root-only"
    assert os.getenv("PROJECT_ENV_PROJECT_ONLY") == "project-only"
    assert os.getenv("1INVALID") is None
    assert os.getenv("INVALID-NAME") is None
    assert "root-secret" not in str(result)
    assert "project-secret" not in str(result)


def test_layered_env_files_apply_shell_project_root_precedence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    for name in (
        "PROJECT_ENV_SHARED",
        "PROJECT_ENV_ROOT_ONLY",
        "PROJECT_ENV_PROJECT_ONLY",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("PROJECT_ENV_SHELL_OVERRIDE", "shell-wins")

    load_layered_env_files(
        root_env_file="tests/fixtures/env/project_env_root.env",
        project_env_file="tests/fixtures/env/project_env_project.env",
    )

    assert os.getenv("PROJECT_ENV_SHARED") == "project-shared"
    assert os.getenv("PROJECT_ENV_ROOT_ONLY") == "root-only"
    assert os.getenv("PROJECT_ENV_PROJECT_ONLY") == "project-only"
    assert os.getenv("PROJECT_ENV_SHELL_OVERRIDE") == "shell-wins"


def test_live_settings_can_use_layered_env_files(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST", "LANGFUSE_BASE_URL"):
        monkeypatch.delenv(name, raising=False)

    settings = LiveSettings.from_env(
        env_file="tests/fixtures/env/project_env_root.env",
        project_env_file="tests/fixtures/env/project_env_project.env",
    )

    assert settings.langfuse_public_key == "project-public"
    assert settings.langfuse_secret_key == "project-secret"
    assert settings.langfuse_host == "https://project-langfuse.test"


def test_live_settings_load_file_false_skips_env_files(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST", "LANGFUSE_BASE_URL"):
        monkeypatch.delenv(name, raising=False)

    settings = LiveSettings.from_env(
        env_file="tests/fixtures/env/project_env_root.env",
        project_env_file="tests/fixtures/env/project_env_project.env",
        load_file=False,
    )

    assert settings.langfuse_public_key is None
    assert settings.langfuse_secret_key is None
    assert settings.langfuse_host is None


def test_missing_project_env_file_is_ignored(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST"):
        monkeypatch.delenv(name, raising=False)

    LiveSettings.from_env(
        env_file="tests/fixtures/env/project_env_root.env",
        project_env_file="tests/fixtures/env/missing-project.env",
    )

    assert os.getenv("LANGFUSE_HOST") == "https://root-langfuse.test"


def test_root_only_env_loading_keeps_existing_behavior(monkeypatch: pytest.MonkeyPatch) -> None:
    for name in ("LANGFUSE_PUBLIC_KEY", "LANGFUSE_SECRET_KEY", "LANGFUSE_HOST"):
        monkeypatch.delenv(name, raising=False)

    settings = LiveSettings.from_env(env_file="tests/fixtures/env/project_env_root.env")

    assert settings.langfuse_public_key == "root-public"
    assert settings.langfuse_secret_key == "root-secret"
    assert settings.langfuse_host == "https://root-langfuse.test"


def test_project_env_file_path_uses_project_name() -> None:
    assert project_env_file_path("dfe-general-public") == Path(".env.dfe-general-public")
