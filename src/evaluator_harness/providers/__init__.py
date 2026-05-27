from __future__ import annotations

from typing import Any

from evaluator_harness.config import ModelConfig, ProviderName
from evaluator_harness.errors import ConfigError
from evaluator_harness.providers.base import ModelProvider


def create_provider(config: ModelConfig) -> ModelProvider:
    if config.provider == ProviderName.OPENAI_COMPATIBLE:
        from evaluator_harness.providers.openai_compatible import OpenAICompatibleProvider

        return OpenAICompatibleProvider(config)
    if config.provider == ProviderName.OLLAMA:
        from evaluator_harness.providers.ollama import OllamaProvider

        return OllamaProvider(config)
    if config.provider == ProviderName.DRY_RUN:
        from evaluator_harness.providers.dry_run import DryRunProvider

        return DryRunProvider(config)
    raise ConfigError(f"Unsupported provider: {config.provider}")


def provider_tracing_metadata(config: ModelConfig) -> dict[str, Any]:
    if config.provider == ProviderName.OPENAI_COMPATIBLE:
        return {
            "provider": config.provider.value,
            "tracing_strategy": "langfuse_wrapped_client",
            "manual_fallback_reason": None,
        }
    if config.provider == ProviderName.OLLAMA:
        return {
            "provider": config.provider.value,
            "tracing_strategy": "manual",
            "manual_fallback_reason": "ollama_has_no_langfuse_wrapped_client",
        }
    if config.provider == ProviderName.DRY_RUN:
        return {
            "provider": config.provider.value,
            "tracing_strategy": "synthetic",
            "manual_fallback_reason": None,
        }
    raise ConfigError(f"Unsupported provider: {config.provider}")
