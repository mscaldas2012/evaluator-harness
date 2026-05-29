from __future__ import annotations

import pytest

from evaluator_harness.config import ProviderName
from evaluator_harness.errors import ConfigError
from evaluator_harness.providers.base import validate_provider_roles


def test_openai_compatible_accepts_common_chat_roles() -> None:
    validate_provider_roles(
        ProviderName.OPENAI_COMPATIBLE,
        ["system", "user", "assistant"],
    )


def test_ollama_rejects_role_based_prompts_before_model_call() -> None:
    with pytest.raises(ConfigError, match="ollama.*role"):
        validate_provider_roles(ProviderName.OLLAMA, ["system", "user"])


def test_openai_compatible_rejects_custom_roles_without_mapping() -> None:
    with pytest.raises(ConfigError, match="reviewer-note"):
        validate_provider_roles(ProviderName.OPENAI_COMPATIBLE, ["user", "reviewer-note"])
