from __future__ import annotations

from evaluator_harness.config import load_project_config
from evaluator_harness.providers import provider_tracing_metadata


def test_openai_compatible_tracing_metadata_declares_final_output_contract() -> None:
    config = load_project_config("configs/projects/rewrite_quality.yaml")

    metadata = provider_tracing_metadata(config.baseline)

    assert metadata["final_output_targeting"] == "inner_generation"
    assert metadata["standard_observation_role"] == "model_output"


def test_dry_run_tracing_metadata_declares_parent_span_contract() -> None:
    config = load_project_config("configs/projects/rewrite_quality.yaml")
    dry_run = next(
        candidate for candidate in config.candidates if candidate.name == "dry-run-candidate"
    )

    metadata = provider_tracing_metadata(dry_run)

    assert metadata["final_output_targeting"] == "parent_span"
    assert metadata["standard_observation_role"] == "model_output"


def test_ollama_tracing_metadata_declares_parent_span_contract() -> None:
    config = load_project_config("tests/fixtures/projects/valid_rewrite_quality.yaml")

    metadata = provider_tracing_metadata(config.candidates[0])

    assert metadata["final_output_targeting"] == "parent_span"
    assert metadata["standard_observation_role"] == "model_output"
