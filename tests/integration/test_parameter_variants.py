from __future__ import annotations

from pathlib import Path

from evaluator_harness.langfuse_client import LangfuseClient
from evaluator_harness.providers.base import ModelResponse
from evaluator_harness.runner import ExperimentRunner, variant_identity
from tests.fixtures.fake_provider import FakeModelProvider


PROJECT_PATH = Path("tests/fixtures/projects/valid_parameter_variants.yaml")


def test_candidate_variants_and_repeated_runs_share_baseline_reference() -> None:
    langfuse = LangfuseClient()

    def provider_factory(_config):
        return FakeModelProvider(response=ModelResponse(output="output"))

    runner = ExperimentRunner(langfuse_client=langfuse, provider_factory=provider_factory)
    baseline = runner.run(PROJECT_PATH, "baseline")

    first = runner.run(
        PROJECT_PATH,
        "candidate",
        candidate="llama3-local",
        baseline=baseline.run_id,
    )
    second = runner.run(
        PROJECT_PATH,
        "candidate",
        candidate="llama3-local-temp-high",
        baseline="latest-compatible",
    )
    repeated = runner.run(
        PROJECT_PATH,
        "candidate",
        candidate="llama3-local",
        baseline="latest-compatible",
    )

    assert {first.run_id, second.run_id, repeated.run_id} == {
        first.run_id,
        second.run_id,
        repeated.run_id,
    }
    assert first.run_id != repeated.run_id
    assert first.baseline_reference == baseline.baseline_reference
    assert second.baseline_reference == baseline.baseline_reference
    assert repeated.baseline_reference == baseline.baseline_reference
    first_trace = [trace for trace in langfuse.traces if trace["run_id"] == first.run_id][0]
    second_trace = [trace for trace in langfuse.traces if trace["run_id"] == second.run_id][0]
    assert first_trace["metadata"]["parameter_hash"] != second_trace["metadata"]["parameter_hash"]
    assert first_trace["metadata"]["generation_parameter_hash"] != second_trace["metadata"]["generation_parameter_hash"]
    assert first_trace["metadata"]["parameter_identity"]["temperature"] == 0.2
    assert second_trace["metadata"]["parameter_identity"]["temperature"] == 0.8


def test_repeated_parameter_variant_runs_preserve_stable_variant_identity() -> None:
    langfuse = LangfuseClient()
    runner = ExperimentRunner(
        langfuse_client=langfuse,
        provider_factory=lambda _config: FakeModelProvider(
            response=ModelResponse(output="output")
        ),
    )

    baseline = runner.run(PROJECT_PATH, "baseline")
    first = runner.run(
        PROJECT_PATH,
        "candidate",
        candidate="llama3-local-temp-high",
        baseline=baseline.run_id,
    )
    second = runner.run(
        PROJECT_PATH,
        "candidate",
        candidate="llama3-local-temp-high",
        baseline=baseline.run_id,
    )

    first_trace = [trace for trace in langfuse.traces if trace["run_id"] == first.run_id][0]
    second_trace = [trace for trace in langfuse.traces if trace["run_id"] == second.run_id][0]
    assert first_trace["metadata"]["variant_identity"] == second_trace["metadata"]["variant_identity"]
    assert first_trace["metadata"]["generation_parameter_hash"] == second_trace["metadata"]["generation_parameter_hash"]


def test_mixed_variant_axes_identifies_model_and_parameter_changes() -> None:
    runner = ExperimentRunner()

    axes = runner.mixed_variant_axes(
        PROJECT_PATH,
        "llama3-local",
    )

    assert axes == ["model", "params"]


def test_mixed_variant_axes_identifies_model_prompt_and_parameter_changes() -> None:
    runner = ExperimentRunner()

    axes = runner.mixed_variant_axes(
        PROJECT_PATH,
        "llama3-local-prompt-v2-temp-high",
    )

    assert axes == ["model", "prompt", "params"]


def test_rewrite_quality_example_prompt_v2_candidate_changes_only_prompt_axis() -> None:
    runner = ExperimentRunner()

    axes = runner.mixed_variant_axes(
        Path("configs/projects/rewrite_quality.yaml"),
        "gpt5.2-dgw-default-prompt-v2",
    )

    assert axes == ["prompt"]


def test_variant_identity_is_stable_for_unchanged_candidate() -> None:
    from evaluator_harness.config import load_project_config

    config = load_project_config(PROJECT_PATH)

    assert variant_identity(config, config.candidates[0]) == variant_identity(
        config, config.candidates[0]
    )
    assert variant_identity(config, config.candidates[0]) != variant_identity(
        config, config.candidates[1]
    )
