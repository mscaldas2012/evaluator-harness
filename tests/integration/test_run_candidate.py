from __future__ import annotations

from pathlib import Path

from evaluator_harness.langfuse_client import LangfuseClient
from evaluator_harness.providers.base import ModelResponse
from evaluator_harness.runner import ExperimentRunner
from tests.fixtures.fake_provider import FakeModelProvider


def test_candidate_run_links_metadata_to_compatible_baseline() -> None:
    langfuse = LangfuseClient()
    baseline_provider = FakeModelProvider(response=ModelResponse(output="baseline output"))
    candidate_provider = FakeModelProvider(
        response=ModelResponse(
            output="candidate output",
            latency_ms=50,
            input_tokens=None,
            output_tokens=None,
            cost_usd=None,
            raw={"retry_count": 1, "tracing_strategy": "manual"},
        )
    )

    def provider_factory(config):
        return baseline_provider if config.name == "gpt-4.1-baseline" else candidate_provider

    runner = ExperimentRunner(langfuse_client=langfuse, provider_factory=provider_factory)
    baseline = runner.run(Path("configs/projects/rewrite_quality.yaml"), "baseline")

    candidate = runner.run(
        Path("configs/projects/rewrite_quality.yaml"),
        "candidate",
        candidate="dry-run-candidate",
        baseline="latest-compatible",
    )

    assert candidate.run_type == "candidate"
    assert candidate.baseline_reference == baseline.baseline_reference
    assert candidate.completed_count == 2
    trace = [trace for trace in langfuse.traces if trace["run_id"] == candidate.run_id][0]
    assert trace["metadata"]["project"] == "rewrite-quality"
    assert trace["metadata"]["environment"] == "local"
    assert trace["metadata"]["project_tags"] == ["rewrite", "mvp"]
    assert "dry-run-candidate" in trace["metadata"]["run_tags"]
    assert trace["metadata"]["dataset_version"] == "latest"
    assert trace["metadata"]["prompt_version"] == "v1"
    assert trace["metadata"]["evaluator_set_id"] == "clarity:v1"
    assert trace["metadata"]["model_name"] == "dry-run-candidate"
    assert trace["metadata"]["baseline_reference"]["baseline_run_id"] == baseline.run_id
    assert trace["metadata"]["ground_truth"]
    assert trace["metadata"]["input_tokens"] is None
    assert trace["metadata"]["cost_usd"] is None


def test_api_key_candidate_run_preserves_baseline_reference_metadata() -> None:
    langfuse = LangfuseClient()
    provider = FakeModelProvider(
        response=ModelResponse(
            output="api key candidate output",
            latency_ms=25,
            input_tokens=10,
            output_tokens=5,
            raw={"tracing_strategy": "manual_langfuse_generation", "retry_count": 0},
        )
    )
    runner = ExperimentRunner(
        langfuse_client=langfuse,
        provider_factory=lambda _config: provider,
    )

    baseline = runner.run(
        Path("tests/fixtures/projects/valid_azure_api_key_candidate.yaml"),
        "baseline",
    )
    candidate = runner.run(
        Path("tests/fixtures/projects/valid_azure_api_key_candidate.yaml"),
        "candidate",
        candidate="azure-api-key-candidate",
        baseline=baseline.run_id,
    )

    trace = [trace for trace in langfuse.traces if trace["run_id"] == candidate.run_id][0]
    assert candidate.completed_count == 2
    assert trace["metadata"]["provider"] == "openai_compatible"
    assert trace["metadata"]["model"] == "mistral-large-3"
    assert trace["metadata"]["model_name"] == "azure-api-key-candidate"
    assert trace["metadata"]["baseline_reference"]["baseline_run_id"] == baseline.run_id
    assert trace["metadata"]["observation_role"] == "model_output"
    assert trace["metadata"]["tracing_strategy"] == "manual_langfuse_generation"
