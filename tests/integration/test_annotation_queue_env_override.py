from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from evaluator_harness.annotation_queues import AnnotationQueueReferenceStore
from evaluator_harness.langfuse_default_gateway import DefaultLangfuseGateway
from evaluator_harness.runner import ExperimentRunner


def test_select_review_routes_to_environment_override(monkeypatch) -> None:
    monkeypatch.setenv("LANGFUSE_ANNOTATION_QUEUE_ID", "queue-env")
    langfuse = DefaultLangfuseGateway()
    langfuse.annotation_queues["queue-env"] = {"id": "queue-env", "name": "env"}
    langfuse.traces.append(
        {
            "trace_id": "trace-1",
            "run_id": "baseline-1",
            "input": "Source",
            "output": "Baseline",
            "metadata": {"dataset_item_id": "1", "dataset_name": "rewrite-quality/v1"},
        }
    )
    runner = ExperimentRunner(langfuse_gateway=langfuse)
    runner.annotation_queue_store = AnnotationQueueReferenceStore(
        Path(".evaluator-harness/test-artifacts") / uuid4().hex / "queue-references"
    )

    result = runner.select_review(
        Path("tests/fixtures/projects/managed_annotation_queue.yaml"),
        "baseline-1",
    )

    assert result.queue_id == "queue-env"
    assert result.queue_ownership == "environment_override"
    assert len(langfuse.annotation_queues) == 1
