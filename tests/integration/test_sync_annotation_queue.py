from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from evaluator_harness.annotation_queues import AnnotationQueueReferenceStore
from evaluator_harness.langfuse_client import LangfuseClient
from evaluator_harness.runner import ExperimentRunner


def test_sync_annotation_queue_is_idempotent_with_fake_langfuse() -> None:
    client = LangfuseClient()
    runner = ExperimentRunner(langfuse_client=client)
    runner.annotation_queue_store = AnnotationQueueReferenceStore(
        Path(".evaluator-harness/test-artifacts") / uuid4().hex / "queue-references"
    )

    first = runner.sync_annotation_queue(
        Path("tests/fixtures/projects/managed_annotation_queue.yaml")
    )
    second = runner.sync_annotation_queue(
        Path("tests/fixtures/projects/managed_annotation_queue.yaml")
    )

    assert first.queue_id == second.queue_id
    assert second.status == "reused"
    assert len(client.annotation_queues) == 1
