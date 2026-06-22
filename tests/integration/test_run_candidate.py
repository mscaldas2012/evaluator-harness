from __future__ import annotations

from pathlib import Path

from evaluator_harness.langfuse_default_gateway import DefaultLangfuseGateway
from evaluator_harness.providers.base import ModelResponse
from evaluator_harness.runner import ExperimentRunner
from tests.fixtures.fake_provider import FakeModelProvider


class FailingDatasetRunItems:
    def create(self, **_kwargs):
        raise RuntimeError("dataset run item write failed")


class EmptyDatasetItems:
    def list(self, **_kwargs):
        return type("Page", (), {"data": []})()


class LiveClientWithFailingRunItems:
    api = type(
        "Api",
        (),
        {
            "dataset_run_items": FailingDatasetRunItems(),
            "dataset_items": EmptyDatasetItems(),
        },
    )()


def test_candidate_run_links_metadata_to_compatible_baseline() -> None:
    langfuse = DefaultLangfuseGateway()
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

    runner = ExperimentRunner(langfuse_gateway=langfuse, provider_factory=provider_factory)
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
    assert trace["name"] == "test/rewrite-quality/dry-run-candidate"
    assert "/item-" not in trace["name"]
    assert trace["metadata"]["baseline_reference"]["baseline_run_id"] == baseline.run_id
    assert trace["metadata"]["ground_truth"]
    assert trace["metadata"]["input_tokens"] is None
    assert trace["metadata"]["cost_usd"] is None


def test_api_key_candidate_run_preserves_baseline_reference_metadata() -> None:
    langfuse = DefaultLangfuseGateway()
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
        langfuse_gateway=langfuse,
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


def test_prompt_variant_candidate_reuses_existing_baseline_reference() -> None:
    langfuse = DefaultLangfuseGateway()
    provider = FakeModelProvider(response=ModelResponse(output="variant output"))
    runner = ExperimentRunner(
        langfuse_gateway=langfuse,
        provider_factory=lambda _config: provider,
    )

    baseline = runner.run(
        Path("tests/fixtures/projects/valid_prompt_variant_candidate.yaml"),
        "baseline",
    )
    candidate = runner.run(
        Path("tests/fixtures/projects/valid_prompt_variant_candidate.yaml"),
        "candidate",
        candidate="dry-run-prompt-v2",
        baseline=baseline.run_id,
    )

    assert candidate.baseline_reference == baseline.baseline_reference
    trace = [trace for trace in langfuse.traces if trace["run_id"] == candidate.run_id][0]
    assert trace["metadata"]["baseline_reference"]["prompt_version"] == "v1"
    assert trace["metadata"]["candidate_prompt_identity"]["version"] == "v2"
    assert trace["metadata"]["baseline_prompt_identity"]["version"] == "v1"


def test_prompt_variant_candidate_renders_candidate_prompt_override() -> None:
    langfuse = DefaultLangfuseGateway()
    baseline_provider = FakeModelProvider(response=ModelResponse(output="baseline output"))
    candidate_provider = FakeModelProvider(response=ModelResponse(output="candidate output"))

    def provider_factory(config):
        return candidate_provider if config.name == "dry-run-prompt-v2" else baseline_provider

    runner = ExperimentRunner(langfuse_gateway=langfuse, provider_factory=provider_factory)
    baseline = runner.run(
        Path("tests/fixtures/projects/valid_prompt_variant_candidate.yaml"),
        "baseline",
    )
    runner.run(
        Path("tests/fixtures/projects/valid_prompt_variant_candidate.yaml"),
        "candidate",
        candidate="dry-run-prompt-v2",
        baseline=baseline.run_id,
    )

    assert "clearer structure" in candidate_provider.calls[0].prompt
    assert "project instructions" in baseline_provider.calls[0].prompt


def test_role_prompt_candidate_override_replaces_full_prompt() -> None:
    langfuse = DefaultLangfuseGateway()
    baseline_provider = FakeModelProvider(response=ModelResponse(output="baseline output"))
    candidate_provider = FakeModelProvider(response=ModelResponse(output="candidate output"))

    def provider_factory(config):
        return candidate_provider if config.name == "dry-run-role-prompt-v2" else baseline_provider

    runner = ExperimentRunner(langfuse_gateway=langfuse, provider_factory=provider_factory)
    baseline = runner.run(
        Path("tests/fixtures/projects/valid_role_prompt_project.yaml"),
        "baseline",
    )
    runner.run(
        Path("tests/fixtures/projects/valid_role_prompt_project.yaml"),
        "candidate",
        candidate="dry-run-role-prompt-v2",
        baseline=baseline.run_id,
    )

    baseline_rendered = baseline_provider.calls[0].rendered_prompt
    candidate_rendered = candidate_provider.calls[0].rendered_prompt
    assert [message.role for message in baseline_rendered.messages] == [
        "system",
        "user",
        "reviewer-note",
    ]
    assert [message.role for message in candidate_rendered.messages] == ["system", "user"]
    assert "custom note" not in candidate_rendered.messages[1].content


def test_rewrite_quality_example_runs_same_model_with_prompt_v2_candidate() -> None:
    langfuse = DefaultLangfuseGateway()
    baseline_provider = FakeModelProvider(response=ModelResponse(output="baseline output"))
    candidate_provider = FakeModelProvider(response=ModelResponse(output="candidate output"))

    def provider_factory(config):
        if config.name == "gpt5.2-dgw-default-prompt-v2":
            return candidate_provider
        return baseline_provider

    runner = ExperimentRunner(langfuse_gateway=langfuse, provider_factory=provider_factory)
    baseline = runner.run(Path("configs/projects/rewrite_quality.yaml"), "baseline")
    candidate = runner.run(
        Path("configs/projects/rewrite_quality.yaml"),
        "candidate",
        candidate="gpt5.2-dgw-default-prompt-v2",
        baseline=baseline.run_id,
    )

    baseline_trace = langfuse.traces_for_run(baseline.run_id)[0]
    candidate_trace = langfuse.traces_for_run(candidate.run_id)[0]
    baseline_metadata = baseline_trace["metadata"]
    candidate_metadata = candidate_trace["metadata"]

    assert candidate.baseline_reference == baseline.baseline_reference
    assert baseline_metadata["model"] == "gpt5.2-dgw-default"
    assert candidate_metadata["model"] == "gpt5.2-dgw-default"
    assert baseline_metadata["prompt_version"] == "v1"
    assert candidate_metadata["prompt_version"] == "v2"
    assert candidate_metadata["baseline_prompt_identity"]["version"] == "v1"
    assert candidate_metadata["candidate_prompt_identity"]["version"] == "v2"
    assert (
        candidate_metadata["baseline_prompt_identity"]["content_hash"]
        != candidate_metadata["candidate_prompt_identity"]["content_hash"]
    )
    assert "project instructions" in baseline_provider.calls[0].prompt
    assert "clearer structure" in candidate_provider.calls[0].prompt


def test_prompt_variant_evaluator_payload_preserves_baseline_output_and_prompt_identity() -> None:
    langfuse = DefaultLangfuseGateway()
    runner = ExperimentRunner(
        langfuse_gateway=langfuse,
        provider_factory=lambda _config: FakeModelProvider(
            response=ModelResponse(output="generated output")
        ),
    )

    baseline = runner.run(
        Path("tests/fixtures/projects/valid_prompt_variant_candidate.yaml"),
        "baseline",
    )
    candidate = runner.run(
        Path("tests/fixtures/projects/valid_prompt_variant_candidate.yaml"),
        "candidate",
        candidate="dry-run-prompt-v2",
        baseline=baseline.run_id,
    )

    payload = [
        payload
        for payload in langfuse.candidate_evaluator_payloads
        if payload["run_id"] == candidate.run_id
    ][0]
    assert payload["baseline_output"] == "generated output"
    assert payload["candidate_prompt_identity"]["version"] == "v2"
    assert payload["baseline_prompt_identity"]["version"] == "v1"


def test_parameter_variant_evaluator_payload_preserves_parameter_identity() -> None:
    langfuse = DefaultLangfuseGateway()
    runner = ExperimentRunner(
        langfuse_gateway=langfuse,
        provider_factory=lambda _config: FakeModelProvider(
            response=ModelResponse(output="generated output")
        ),
    )

    baseline = runner.run(
        Path("tests/fixtures/projects/valid_parameter_variants.yaml"),
        "baseline",
    )
    candidate = runner.run(
        Path("tests/fixtures/projects/valid_parameter_variants.yaml"),
        "candidate",
        candidate="llama3-local-temp-high",
        baseline=baseline.run_id,
    )

    payload = [
        payload
        for payload in langfuse.candidate_evaluator_payloads
        if payload["run_id"] == candidate.run_id
    ][0]
    assert payload["parameter_identity"]["temperature"] == 0.8
    assert payload["generation_parameter_hash"]
    assert payload["variant_identity"]["generation_parameter_hash"] == payload["generation_parameter_hash"]


def test_candidate_outputs_survive_recoverable_langfuse_warning() -> None:
    langfuse = DefaultLangfuseGateway(client=LiveClientWithFailingRunItems())
    provider = FakeModelProvider(response=ModelResponse(output="candidate output"))
    runner = ExperimentRunner(
        langfuse_gateway=langfuse,
        provider_factory=lambda _config: provider,
    )
    baseline = runner.run(
        Path("configs/projects/rewrite_quality.yaml"),
        "baseline",
        skip_sync=True,
        select_human_review=False,
    )

    candidate = runner.run(
        Path("configs/projects/rewrite_quality.yaml"),
        "candidate",
        candidate="dry-run-candidate",
        baseline=baseline.run_id,
        skip_sync=True,
        select_human_review=False,
    )

    traces = langfuse.traces_for_run(candidate.run_id)
    assert candidate.completed_count == 2
    assert candidate.langfuse_status == "complete-with-warnings"
    assert all(trace["output"] == "candidate output" for trace in traces)
