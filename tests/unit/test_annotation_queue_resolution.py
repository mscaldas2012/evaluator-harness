from __future__ import annotations

from pathlib import Path
from uuid import uuid4

from evaluator_harness.annotation_queues import (
    AnnotationQueueReferenceStore,
    resolve_annotation_queue,
    sync_annotation_queue,
)
from evaluator_harness.config import load_project_config
from evaluator_harness.langfuse_default_gateway import DefaultLangfuseGateway, ScoreConfigSyncResult


def _store() -> AnnotationQueueReferenceStore:
    return AnnotationQueueReferenceStore(
        Path(".evaluator-harness/test-artifacts") / uuid4().hex / "queue-references"
    )


def _score_results() -> list[ScoreConfigSyncResult]:
    return [
        ScoreConfigSyncResult(
            evaluator_name="clarity",
            name="eh_rewrite_quality_clarity",
            score_config_id="score-config-1",
            status="created",
            ownership="managed_by_harness",
        )
    ]


def test_resolve_annotation_queue_uses_environment_override(monkeypatch) -> None:
    config = load_project_config("tests/fixtures/projects/managed_annotation_queue.yaml")
    client = DefaultLangfuseGateway()
    client.annotation_queues["queue-env"] = {"id": "queue-env", "name": "env-queue"}
    monkeypatch.setenv("LANGFUSE_ANNOTATION_QUEUE_ID", "queue-env")

    result = resolve_annotation_queue(config, client, _score_results(), store=_store())

    assert result.queue_id == "queue-env"
    assert result.ownership == "environment_override"


def test_resolve_annotation_queue_uses_local_managed_reference(monkeypatch) -> None:
    config = load_project_config("tests/fixtures/projects/managed_annotation_queue.yaml")
    client = DefaultLangfuseGateway()
    store = _store()
    monkeypatch.delenv("LANGFUSE_ANNOTATION_QUEUE_ID", raising=False)
    created = sync_annotation_queue(config, client, _score_results(), store=store)

    result = resolve_annotation_queue(config, client, _score_results(), store=store)

    assert result.queue_id == created.queue_id
    assert result.status == "reused"
