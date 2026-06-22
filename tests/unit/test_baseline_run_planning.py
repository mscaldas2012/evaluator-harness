from __future__ import annotations

from evaluator_harness.baseline_runs import build_baseline_run_context
from evaluator_harness.config import load_project_config
from evaluator_harness.langfuse_records import DatasetSyncResult


def test_build_baseline_run_context_preserves_reference_and_metadata() -> None:
    config = load_project_config("configs/projects/rewrite_quality.yaml")
    dataset_sync = DatasetSyncResult(
        name="rewrite-quality/v1",
        version="latest",
        compatibility_version="sha256:dataset",
        item_count=2,
        status="synced",
    )

    context = build_baseline_run_context(config=config, dataset_sync=dataset_sync)

    assert context.run_id.startswith("baseline-")
    assert context.run_name.startswith("rewrite-quality-v1-baseline-")
    assert context.reference.baseline_run_id == context.run_id
    assert context.reference.langfuse_run_name == context.run_name
    assert context.reference.dataset_name == dataset_sync.name
    assert context.reference.dataset_version == dataset_sync.compatibility_version
    assert context.run_metadata["baseline_run_id"] == context.run_id
    assert context.run_metadata["project_name"] == config.project.name
    assert context.run_metadata["created_at"] == context.created_at
