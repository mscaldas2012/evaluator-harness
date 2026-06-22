from __future__ import annotations

from pathlib import Path

import pytest

from evaluator_harness.annotation_queues import AnnotationQueueReferenceStore
from evaluator_harness.errors import ConfigError
from evaluator_harness.langfuse_default_gateway import DefaultLangfuseGateway
from evaluator_harness.langfuse_records import DatasetSyncResult
from evaluator_harness.providers.base import ModelResponse
from evaluator_harness.runner import ExperimentRunner
from tests.fixtures.fake_provider import FakeModelProvider

SHARED_TRACE_METADATA_KEYS = {
    "project",
    "project_version",
    "run_type",
    "dataset_name",
    "dataset_version",
    "dataset_compatibility_version",
    "dataset_item_id",
    "trace_id",
    "trace_name",
    "item_comparison_session_id",
    "item_comparison_session_inputs",
    "prompt_version",
    "prompt_shape",
    "prompt_roles",
    "prompt_identity",
    "baseline_prompt_identity",
    "evaluator_set_id",
    "ground_truth",
    "provider",
    "model",
    "model_name",
    "temperature",
    "parameter_hash",
    "parameter_identity",
    "generation_parameter_hash",
    "variant_identity",
    "retry_count",
    "provider_tracing_strategy",
}


def assert_shared_trace_evidence(trace: dict, *, run_type: str) -> None:
    metadata = trace["metadata"]

    assert SHARED_TRACE_METADATA_KEYS <= set(metadata)
    assert metadata["run_type"] == run_type
    assert metadata["trace_id"] == trace["trace_id"]
    assert metadata["trace_name"] == trace["name"]
    assert metadata["dataset_item_id"]
    assert metadata["item_comparison_session_id"]
    assert (
        metadata["item_comparison_session_inputs"]["dataset_item_id"]
        == metadata["dataset_item_id"]
    )
    assert metadata["prompt_identity"]["version"] == metadata["prompt_version"]
    assert (
        metadata["baseline_prompt_identity"]["version"]
        == metadata["baseline_prompt_version"]
    )
    assert metadata["provider_tracing_strategy"]["provider"] == metadata["provider"]


def assert_shared_failure_evidence(trace: dict, *, run_type: str) -> None:
    assert_shared_trace_evidence(trace, run_type=run_type)
    assert trace["error"]
    assert trace["output"] is None
    assert trace["rendered_prompt"]
    assert trace["metadata"]["retry_count"] == 0


def test_run_baseline_records_traces_and_reference() -> None:
    langfuse = DefaultLangfuseGateway()
    provider = FakeModelProvider(
        response=ModelResponse(
            output="baseline output",
            latency_ms=100,
            input_tokens=5,
            output_tokens=7,
            cost_usd=0.01,
        )
    )
    runner = ExperimentRunner(
        langfuse_gateway=langfuse,
        provider_factory=lambda _config: provider,
    )

    result = runner.run(Path("configs/projects/rewrite_quality.yaml"), "baseline")

    assert result.run_type == "baseline"
    assert result.baseline_reference is not None
    assert result.completed_count == 2
    assert result.review_selection is not None
    assert result.review_selection.queued_count >= 1
    assert_shared_trace_evidence(langfuse.traces[0], run_type="baseline")
    assert langfuse.traces[0]["metadata"]["project"] == "rewrite-quality"
    assert langfuse.traces[0]["metadata"]["prompt_version"] == "v1"
    assert langfuse.traces[0]["metadata"]["ground_truth"]
    assert langfuse.baseline_evaluator_payloads[0]["output"] == "baseline output"
    assert langfuse.baseline_evaluator_payloads[0]["evaluators"] == [
        {
            "name": "clarity",
            "version": "v1",
            "score_config": "eh_rewrite_quality_clarity",
        }
    ]
    assert langfuse.annotation_queue_items


def test_run_baseline_can_skip_automatic_review_selection() -> None:
    langfuse = DefaultLangfuseGateway()
    provider = FakeModelProvider(response=ModelResponse(output="baseline output"))
    runner = ExperimentRunner(
        langfuse_gateway=langfuse,
        provider_factory=lambda _config: provider,
    )

    result = runner.run(
        Path("configs/projects/rewrite_quality.yaml"),
        "baseline",
        select_human_review=False,
    )

    assert result.completed_count == 2
    assert result.review_selection is None
    assert langfuse.annotation_queue_items == []


def test_run_baseline_can_skip_sync_calls() -> None:
    langfuse = DefaultLangfuseGateway()
    provider = FakeModelProvider(response=ModelResponse(output="baseline output"))
    runner = ExperimentRunner(
        langfuse_gateway=langfuse,
        provider_factory=lambda _config: provider,
    )

    result = runner.run(
        Path("configs/projects/rewrite_quality.yaml"),
        "baseline",
        select_human_review=False,
        skip_sync=True,
    )

    call_names = [name for name, _payload in langfuse.calls]
    assert result.completed_count == 2
    assert "sync_dataset" not in call_names
    assert "sync_score_configs" not in call_names
    assert langfuse.traces[0]["metadata"]["dataset_name"] == "rewrite-quality/v1"


def test_run_baseline_blocks_missing_required_dataset_identity() -> None:
    class MissingDatasetIdentityRunner(ExperimentRunner):
        def _skip_sync_dataset_result(self, config, items):
            return DatasetSyncResult(
                name="",
                version="latest",
                compatibility_version="v1",
                item_count=len(items),
                status="resolved",
            )

    provider = FakeModelProvider(response=ModelResponse(output="baseline output"))
    runner = MissingDatasetIdentityRunner(
        langfuse_gateway=DefaultLangfuseGateway(),
        provider_factory=lambda _config: provider,
    )

    with pytest.raises(ConfigError, match="Dataset identity"):
        runner.run(
            Path("configs/projects/rewrite_quality.yaml"),
            "baseline",
            skip_sync=True,
        )

    assert provider.calls == []


def test_run_baseline_skip_sync_applies_to_automatic_review_selection(tmp_path) -> None:
    langfuse = DefaultLangfuseGateway()
    provider = FakeModelProvider(response=ModelResponse(output="baseline output"))
    runner = ExperimentRunner(
        langfuse_gateway=langfuse,
        provider_factory=lambda _config: provider,
    )
    runner.annotation_queue_store = AnnotationQueueReferenceStore(tmp_path)

    runner.run(Path("configs/projects/rewrite_quality.yaml"), "baseline")
    langfuse.calls.clear()

    result = runner.run(
        Path("configs/projects/rewrite_quality.yaml"),
        "baseline",
        skip_sync=True,
    )

    call_names = [name for name, _payload in langfuse.calls]
    assert result.review_selection is not None
    assert "sync_dataset" not in call_names
    assert "sync_score_configs" not in call_names


def test_role_based_baseline_passes_ordered_messages_to_provider() -> None:
    provider = FakeModelProvider()
    runner = ExperimentRunner(
        langfuse_gateway=DefaultLangfuseGateway(),
        provider_factory=lambda _config: provider,
    )

    runner.run(
        Path("tests/fixtures/projects/valid_role_prompt_project.yaml"), "baseline"
    )

    rendered = provider.calls[0].rendered_prompt
    assert rendered.shape == "messages"
    assert [message.role for message in rendered.messages] == [
        "system",
        "user",
        "reviewer-note",
    ]
    assert "Rewrite this text" in rendered.messages[1].content


def test_unsupported_role_provider_fails_before_generate() -> None:
    provider = FakeModelProvider()
    runner = ExperimentRunner(
        langfuse_gateway=DefaultLangfuseGateway(),
        provider_factory=lambda _config: provider,
    )

    with pytest.raises(ConfigError, match="ollama"):
        runner.run(
            Path("tests/fixtures/projects/invalid_role_prompt_ollama.yaml"),
            "baseline",
        )

    assert provider.calls == []


def test_run_baseline_records_failed_call_context() -> None:
    langfuse = DefaultLangfuseGateway()
    provider = FakeModelProvider(scenario="timeout")
    runner = ExperimentRunner(
        langfuse_gateway=langfuse,
        provider_factory=lambda _config: provider,
    )

    result = runner.run(Path("configs/projects/rewrite_quality.yaml"), "baseline")

    assert result.failed_count == 2
    assert_shared_failure_evidence(langfuse.traces[0], run_type="baseline")
    assert langfuse.traces[0]["error"]
    assert langfuse.traces[0]["metadata"]["provider"] == "openai_compatible"
    assert langfuse.traces[0]["metadata"]["retry_count"] >= 0
