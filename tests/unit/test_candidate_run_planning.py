from __future__ import annotations

from evaluator_harness.baseline_registry import build_baseline_fingerprint
from evaluator_harness.candidate_runs import build_candidate_run_context
from evaluator_harness.config import BaselineReference, load_project_config
from evaluator_harness.langfuse_default_gateway import DefaultLangfuseGateway
from evaluator_harness.langfuse_records import DatasetSyncResult


def test_build_candidate_run_context_resolves_baseline_reference_and_metadata() -> None:
    config = load_project_config("configs/projects/rewrite_quality.yaml")
    dataset_sync = DatasetSyncResult(
        name="rewrite-quality/v1",
        version="latest",
        compatibility_version="sha256:dataset",
        item_count=2,
        status="synced",
    )
    fingerprint = build_baseline_fingerprint(
        config,
        dataset_name=dataset_sync.name,
        dataset_version=dataset_sync.compatibility_version,
    )
    langfuse = DefaultLangfuseGateway()
    baseline = BaselineReference(
        baseline_run_id="baseline-1",
        langfuse_run_name="baseline",
        project_name=fingerprint.project_name,
        project_version=fingerprint.project_version,
        dataset_name=fingerprint.dataset_name,
        dataset_version=fingerprint.dataset_version,
        prompt_version=fingerprint.prompt_version,
        evaluator_set_id=fingerprint.evaluator_set_id,
        baseline_model=fingerprint.baseline_model,
        baseline_parameters_hash=fingerprint.baseline_parameters_hash,
        created_at="2026-01-01T00:00:00+00:00",
    )
    langfuse.record_baseline_reference("baseline-1", baseline)

    context = build_candidate_run_context(
        config=config,
        dataset_sync=dataset_sync,
        candidate_name="dry-run-candidate",
        baseline_selector="baseline-1",
        langfuse_gateway=langfuse,
        baseline_registry=None,
        warning_messages=(),
    )

    assert context.baseline_reference == baseline
    assert context.baseline_run_id == "baseline-1"
    assert context.run_id.startswith("candidate-")
    assert context.run_metadata["candidate"] == "dry-run-candidate"
    assert context.run_metadata["baseline_prompt_identity"]["version"] == "v1"
    assert context.run_metadata["candidate_prompt_identity"]["version"] == "v1"
