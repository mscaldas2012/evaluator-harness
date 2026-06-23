from __future__ import annotations

from evaluator_harness.baseline_registry import BaselineFingerprint
from evaluator_harness.config import (
    BaselineReference,
    DatasetItem,
    load_project_config,
)
from evaluator_harness.langfuse_records import DatasetSyncResult
from evaluator_harness.prompts import RenderedPrompt
from evaluator_harness.providers.base import ModelResponse
from evaluator_harness.run_metadata import build_request_metadata, build_trace_payload
from evaluator_harness.session_identity import SessionIdentityInputs


def test_build_trace_payload_preserves_candidate_metadata_shape() -> None:
    config = load_project_config(
        "tests/fixtures/projects/config_refs/valid_scenario_project.yaml"
    )
    dataset_sync = DatasetSyncResult(
        name="dataset",
        version="v1",
        compatibility_version="sha256:dataset",
        item_count=1,
        status="created",
    )
    fingerprint = BaselineFingerprint(
        project_name=config.project.name,
        project_version=config.project.version,
        dataset_name=dataset_sync.name,
        dataset_version=dataset_sync.version,
        prompt_version=config.task_prompt.version,
        evaluator_set_id="clarity:v1",
        baseline_model=config.baseline.model,
        baseline_parameters_hash="baseline-params",
    )
    baseline_reference = BaselineReference(
        baseline_run_id="baseline-1",
        langfuse_run_name="baseline",
        project_name=config.project.name,
        project_version=config.project.version,
        dataset_name=dataset_sync.name,
        dataset_version=dataset_sync.version,
        prompt_version=config.task_prompt.version,
        evaluator_set_id=fingerprint.evaluator_set_id,
        baseline_model=config.baseline.model,
        baseline_parameters_hash=fingerprint.baseline_parameters_hash,
        created_at="2026-01-01T00:00:00+00:00",
    )
    item = DatasetItem(item_id="item-1", input="Input", ground_truth="Expected")
    response = ModelResponse(
        output="Candidate",
        latency_ms=123,
        input_tokens=10,
        output_tokens=20,
        cost_usd=0.01,
        raw={"tracing_strategy": "manual", "manual_fallback_reason": "fixture"},
    )
    session_inputs = SessionIdentityInputs(
        project=config.project.name,
        project_version=config.project.version,
        dataset_name=dataset_sync.name,
        dataset_version=dataset_sync.compatibility_version,
        baseline_anchor=baseline_reference.baseline_run_id,
        dataset_item_id=item.item_id,
    )

    payload = build_trace_payload(
        config=config,
        item=item,
        run_id="candidate-1",
        trace_id="trace-1",
        trace_name="trace name",
        response=response,
        prompt="Rendered prompt",
        retry_count=2,
        error=None,
        model_config=config.candidates[0],
        dataset_sync=dataset_sync,
        fingerprint=fingerprint,
        baseline_reference=baseline_reference,
        parameter_hash="candidate-params",
        rendered_prompt=RenderedPrompt(shape="text", text="Rendered prompt"),
        session_id="session-1",
        session_inputs=session_inputs,
    )

    metadata = payload["metadata"]
    assert payload["output"] == "Candidate"
    assert metadata["run_id"] == "candidate-1"
    assert metadata["run_type"] == "candidate"
    assert metadata["scenario_group"] == "fixture"
    assert metadata["baseline_reference"]["baseline_run_id"] == "baseline-1"
    assert metadata["candidate_prompt_identity"] is not None
    assert metadata["parameter_hash"] == "candidate-params"
    assert metadata["latency_ms"] == 123
    assert metadata["item_comparison_session_inputs"] == session_inputs.metadata()
    assert payload["rendered_prompt"]["text"] == "Rendered prompt"


def test_build_request_metadata_preserves_baseline_metadata_shape() -> None:
    config = load_project_config(
        "tests/fixtures/projects/config_refs/valid_scenario_project.yaml"
    )
    dataset_sync = DatasetSyncResult(
        name="dataset",
        version="v1",
        compatibility_version="sha256:dataset",
        item_count=1,
        status="created",
    )
    fingerprint = BaselineFingerprint(
        project_name=config.project.name,
        project_version=config.project.version,
        dataset_name=dataset_sync.name,
        dataset_version=dataset_sync.version,
        prompt_version=config.task_prompt.version,
        evaluator_set_id="clarity:v1",
        baseline_model=config.baseline.model,
        baseline_parameters_hash="baseline-params",
    )
    item = DatasetItem(item_id="item-1", input="Input", ground_truth="Expected")

    metadata = build_request_metadata(
        config=config,
        model_config=config.baseline,
        item=item,
        run_id="baseline-1",
        run_type="baseline",
        trace_id="trace-1",
        trace_name="trace name",
        dataset_sync=dataset_sync,
        fingerprint=fingerprint,
        rendered_prompt=RenderedPrompt(shape="text", text="Rendered prompt"),
    )

    assert metadata["run_type"] == "baseline"
    assert metadata["scenario_name"] == "scenario_one"
    assert metadata["candidate_prompt_identity"] is None
    assert metadata["dataset_name"] == dataset_sync.name
    assert metadata["dataset_item_id"] == item.item_id
    assert metadata["evaluator_set_id"] == fingerprint.evaluator_set_id
    assert metadata["rendered_prompt"]["text"] == "Rendered prompt"
