from __future__ import annotations

import os

import pytest

from evaluator_harness.config import LiveSettings, load_env_file


LANGFUSE_ENV_VARS = (
    "LANGFUSE_PUBLIC_KEY",
    "LANGFUSE_SECRET_KEY",
)

AZURE_OPENAI_ENV_VARS = (
    "EDAV_TENANT_ID",
    "EDAV_CLIENT_ID",
    "EDAV_CLIENT_SECRET",
    "EDAV_SCOPE_TOKEN_AUDIENCE",
    "EDAV_SUBSCRIPTION_KEY",
    "EDAV_AZURE_OPENAI_API_VERSION",
    "EDAV_AZURE_OPENAI_ENDPOINT",
)


def missing_env_vars(names: tuple[str, ...]) -> list[str]:
    return [name for name in names if not os.getenv(name)]


def require_live_langfuse() -> None:
    load_env_file()
    if os.getenv("RUN_LIVE_TESTS") not in {"1", "true", "TRUE", "yes"}:
        pytest.skip("set RUN_LIVE_TESTS=1 to run live integration tests")
    settings = LiveSettings.from_env(load_file=False)
    missing = [
        name
        for name, value in {
            "LANGFUSE_PUBLIC_KEY": settings.langfuse_public_key,
            "LANGFUSE_SECRET_KEY": settings.langfuse_secret_key,
            "LANGFUSE_HOST or LANGFUSE_BASE_URL": settings.langfuse_host,
        }.items()
        if not value
    ]
    if missing:
        pytest.skip("missing live Langfuse env vars: " + ", ".join(missing))


def require_live_azure_openai() -> None:
    load_env_file()
    missing = missing_env_vars(AZURE_OPENAI_ENV_VARS)
    if missing:
        pytest.skip("missing live Azure OpenAI env vars: " + ", ".join(missing))
