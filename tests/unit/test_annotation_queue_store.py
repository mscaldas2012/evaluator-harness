from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from evaluator_harness.annotation_queues import (
    AnnotationQueueReference,
    AnnotationQueueReferenceStore,
    queue_reference_path,
)
from tests.fixtures.annotation_queues import MANAGED_QUEUE_REFERENCE


def test_queue_reference_path_uses_project_review_policy_key() -> None:
    path = queue_reference_path(
        "rewrite-quality",
        "v1",
        "default",
        base_dir=".evaluator-harness/queue-references",
    )

    assert str(path).endswith(
        ".evaluator-harness\\queue-references\\rewrite-quality__v1__default.json"
    ) or str(path).endswith(
        ".evaluator-harness/queue-references/rewrite-quality__v1__default.json"
    )


def test_queue_reference_round_trips_without_secrets() -> None:
    store = AnnotationQueueReferenceStore(
        Path(".evaluator-harness/test-artifacts") / uuid4().hex / "queue-references"
    )
    reference = AnnotationQueueReference.model_validate(MANAGED_QUEUE_REFERENCE)

    path = store.save(reference)
    loaded = store.load("rewrite-quality", "v1", "default")

    text = path.read_text(encoding="utf-8")
    assert loaded == reference
    assert "LANGFUSE_SECRET_KEY" not in text
    assert "sk-lf" not in text


def test_incompatible_queue_reference_returns_none() -> None:
    store = AnnotationQueueReferenceStore(
        Path(".evaluator-harness/test-artifacts") / uuid4().hex / "queue-references"
    )
    reference = AnnotationQueueReference.model_validate(MANAGED_QUEUE_REFERENCE)
    store.save(reference)

    assert store.load("rewrite-quality", "v2", "default") is None
