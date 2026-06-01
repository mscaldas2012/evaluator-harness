from __future__ import annotations

from pathlib import Path

from evaluator_harness.annotation_queues import (
    AnnotationQueueReference,
    AnnotationQueueReferenceStore,
)
from evaluator_harness.langfuse_client import LangfuseClient
from scripts.reset_annotation_queue_for_project import (
    build_reset_plan,
    delete_local_reference,
    format_score_config_ids,
    reset_queue,
    score_config_names_by_reference_order,
)
from tests.fixtures.annotation_queues import MANAGED_QUEUE_REFERENCE


def test_build_reset_plan_points_to_target_project_reference(tmp_path: Path) -> None:
    reference_dir = tmp_path / "queue-references"
    store = AnnotationQueueReferenceStore(reference_dir)
    store.save(AnnotationQueueReference.model_validate(MANAGED_QUEUE_REFERENCE))

    plan = build_reset_plan(
        Path("tests/fixtures/projects/managed_annotation_queue.yaml"),
        reference_dir=reference_dir,
    )

    assert plan.project_name == "rewrite-quality"
    assert plan.project_version == "v1"
    assert plan.review_policy_version == "default"
    assert plan.reference_path == reference_dir / "rewrite-quality__v1__default.json"
    assert plan.existing_reference is not None
    assert plan.existing_reference.queue_id == "queue-managed-1"


def test_delete_local_reference_unlinks_existing_path() -> None:
    class FakePath:
        def __init__(self) -> None:
            self.unlinked = False

        def exists(self) -> bool:
            return True

        def unlink(self) -> None:
            self.unlinked = True

    target = FakePath()

    deleted = delete_local_reference(target)  # type: ignore[arg-type]

    assert deleted is True
    assert target.unlinked is True


def test_format_score_config_ids_includes_names_when_known() -> None:
    text = format_score_config_ids(
        ["score-1", "score-2"],
        {"score-1": "eh_rewrite_quality_clarity"},
    )

    assert text == "eh_rewrite_quality_clarity (score-1), score-2"


def test_score_config_names_by_reference_order_uses_project_evaluator_order() -> None:
    plan = build_reset_plan(Path("tests/fixtures/projects/managed_annotation_queue.yaml"))
    names_by_id = score_config_names_by_reference_order(
        type(
            "Config",
            (),
            {
                "project": type("Project", (), {"score_config_prefix": "eh_test_"})(),
                "evaluators": [
                    type("Evaluator", (), {"score": type("Score", (), {"name": "clarity"})()})()
                ],
            },
        )(),
        ["score-1"],
    )

    assert plan.project_name == "rewrite-quality"
    assert names_by_id == {"score-1": "eh_test_clarity"}


def test_reset_queue_syncs_scores_and_recreates_reference(tmp_path: Path) -> None:
    reference_dir = tmp_path / "queue-references"
    client = LangfuseClient()

    score_results, queue_result = reset_queue(
        Path("tests/fixtures/projects/managed_annotation_queue.yaml"),
        client=client,
        reference_dir=reference_dir,
    )

    assert score_results
    assert score_results[0].status == "created"
    assert queue_result.status == "created"
    assert (reference_dir / "rewrite-quality__v1__default.json").exists()
