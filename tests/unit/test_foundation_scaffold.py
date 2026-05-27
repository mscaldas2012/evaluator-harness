from __future__ import annotations

from pathlib import Path

from evaluator_harness.config import (
    AuthMode,
    DatasetSource,
    EvaluationProject,
    ModelConfig,
    ModelParameters,
    ProviderName,
)
from evaluator_harness.providers.base import ModelRequest
from evaluator_harness.providers import create_provider
from tests.fixtures.fake_langfuse import FakeLangfuseClient
from tests.fixtures.fake_provider import FakeModelProvider


def test_project_model_accepts_repo_safe_secret_references() -> None:
    baseline = ModelConfig(
        name="baseline",
        provider=ProviderName.OPENAI_COMPATIBLE,
        auth_mode=AuthMode.API_KEY,
        model="gpt-4.1",
        parameters=ModelParameters(temperature=0.2),
    )

    project = EvaluationProject(
        name="rewrite-quality",
        version="v1",
        score_config_prefix="eh_rewrite_quality_",
    )

    assert project.score_config_prefix == "eh_rewrite_quality_"
    assert baseline.auth_mode == AuthMode.API_KEY


def test_foundation_fakes_record_langfuse_and_provider_calls() -> None:
    langfuse = FakeLangfuseClient()
    provider = FakeModelProvider(scenario="usage_metadata")

    dataset = langfuse.sync_dataset("rewrite-quality/v1", [{"id": "1"}])
    response = provider.generate(
        request=ModelRequest(prompt="rewrite", params={"temperature": 0.2})
    )

    assert dataset["version"] == "fake-version"
    assert response.output == "rewritten output"
    assert provider.calls


def test_provider_factory_returns_configured_skeleton_provider() -> None:
    config = ModelConfig(
        name="llama3-local",
        provider=ProviderName.OLLAMA,
        auth_mode=AuthMode.NONE,
        model="llama3",
        parameters=ModelParameters(temperature=0.2),
    )

    provider = create_provider(config)

    assert provider.config.name == "llama3-local"


def test_dataset_source_defaults_to_local_csv() -> None:
    source = DatasetSource(path=Path("datasets/rewrite_quality.csv"))

    assert source.kind.value == "local_csv"
