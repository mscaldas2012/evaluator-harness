from __future__ import annotations

import pytest

from evaluator_harness.config import load_project_config
from evaluator_harness.errors import ConfigError
from evaluator_harness.providers import create_provider, provider_tracing_metadata
from evaluator_harness.providers.ollama import OllamaProvider
from evaluator_harness.providers.openai_compatible import OpenAICompatibleProvider


def test_provider_factory_selects_openai_compatible_provider() -> None:
    config = load_project_config("configs/projects/rewrite_quality.yaml")

    provider = create_provider(config.baseline)

    assert isinstance(provider, OpenAICompatibleProvider)


def test_provider_factory_selects_ollama_provider() -> None:
    config = load_project_config("configs/projects/rewrite_quality.yaml")

    provider = create_provider(config.candidates[0])

    assert isinstance(provider, OllamaProvider)


def test_provider_factory_rejects_unsupported_provider() -> None:
    config = load_project_config("configs/projects/rewrite_quality.yaml")
    invalid = config.candidates[0].model_copy(update={"provider": "unsupported"})

    with pytest.raises(ConfigError, match="Unsupported provider"):
        create_provider(invalid)


def test_provider_tracing_metadata_prefers_langfuse_for_openai_compatible() -> None:
    config = load_project_config("configs/projects/rewrite_quality.yaml")

    metadata = provider_tracing_metadata(config.baseline)

    assert metadata["tracing_strategy"] == "langfuse_wrapped_client"
    assert metadata["manual_fallback_reason"] is None


def test_provider_tracing_metadata_documents_ollama_manual_fallback() -> None:
    config = load_project_config("configs/projects/rewrite_quality.yaml")

    metadata = provider_tracing_metadata(config.candidates[0])

    assert metadata["tracing_strategy"] == "manual"
    assert metadata["manual_fallback_reason"] == "ollama_has_no_langfuse_wrapped_client"
