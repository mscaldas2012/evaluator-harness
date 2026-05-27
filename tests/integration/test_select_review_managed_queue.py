from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from evaluator_harness.annotation_queues import AnnotationQueueReferenceStore
from evaluator_harness.langfuse_client import LangfuseClient
from evaluator_harness.runner import ExperimentRunner


def test_select_review_auto_resolves_managed_queue_without_env(monkeypatch) -> None:
    monkeypatch.delenv("LANGFUSE_ANNOTATION_QUEUE_ID", raising=False)
    langfuse = LangfuseClient()
    langfuse.traces.append(
        {
            "trace_id": "trace-1",
            "run_id": "baseline-1",
            "input": "Source",
            "output": "Baseline",
            "metadata": {"dataset_item_id": "1", "dataset_name": "rewrite-quality/v1"},
        }
    )
    runner = ExperimentRunner(langfuse_client=langfuse)
    runner.annotation_queue_store = AnnotationQueueReferenceStore(
        Path(".evaluator-harness/test-artifacts") / uuid4().hex / "queue-references"
    )

    result = runner.select_review(
        Path("tests/fixtures/projects/managed_annotation_queue.yaml"),
        "baseline-1",
    )

    assert result.selected_count == 1
    assert result.queued_count == 1
    assert result.queue_id == "annotation-queue-1"
    assert result.queue_ownership == "managed_by_harness"
