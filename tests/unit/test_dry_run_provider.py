from __future__ import annotations

import pytest
from pydantic import ValidationError

from evaluator_harness.config import AuthMode, ModelConfig, ModelParameters, ProviderName
from evaluator_harness.providers import create_provider, provider_tracing_metadata
from evaluator_harness.providers.base import ModelRequest
from evaluator_harness.providers.dry_run import DryRunProvider


def _dry_run_config() -> ModelConfig:
    return ModelConfig(
        name="dry-run-candidate",
        provider=ProviderName.DRY_RUN,
        auth_mode=AuthMode.NONE,
        model="dry-run",
        parameters=ModelParameters(temperature=0.0),
    )


def test_dry_run_provider_is_first_class_provider() -> None:
    provider = create_provider(_dry_run_config())

    assert isinstance(provider, DryRunProvider)
    response = provider.generate(
        ModelRequest(prompt="hello", params={}, metadata={"item_id": "item-1"})
    )
    assert response.output.startswith("[dry-run:dry-run-candidate:item-1:")
    assert response.raw["dry_run"] is True
    assert response.cost_usd == 0.0


def test_dry_run_provider_tracing_metadata_is_synthetic() -> None:
    metadata = provider_tracing_metadata(_dry_run_config())

    assert metadata["tracing_strategy"] == "synthetic"
    assert metadata["manual_fallback_reason"] is None


def test_dry_run_provider_rejects_auth_modes() -> None:
    with pytest.raises(ValidationError, match="dry_run provider"):
        ModelConfig(
            name="dry-run-candidate",
            provider=ProviderName.DRY_RUN,
            auth_mode=AuthMode.API_KEY,
            model="dry-run",
            parameters=ModelParameters(temperature=0.0),
        )
