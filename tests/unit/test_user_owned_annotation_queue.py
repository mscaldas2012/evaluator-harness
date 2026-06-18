from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from evaluator_harness.annotation_queues import AnnotationQueueReferenceStore, sync_annotation_queue
from evaluator_harness.config import load_project_config
from evaluator_harness.errors import ConfigError
from evaluator_harness.langfuse_default_gateway import DefaultLangfuseGateway, ScoreConfigSyncResult


def _store() -> AnnotationQueueReferenceStore:
    return AnnotationQueueReferenceStore(
        Path(".evaluator-harness/test-artifacts") / uuid4().hex / "queue-references"
    )


def test_user_owned_queue_sync_does_not_create_or_store_reference() -> None:
    config = load_project_config("tests/fixtures/projects/user_owned_annotation_queue.yaml")
    client = DefaultLangfuseGateway()
    client.annotation_queues["queue-user-owned-1"] = {
        "id": "queue-user-owned-1",
        "name": "shared-review-queue",
    }
    store = _store()

    result = sync_annotation_queue(config, client, [], store=store)

    assert result.status == "user_owned"
    assert result.queue_id == "queue-user-owned-1"
    assert len(client.annotation_queues) == 1
    assert store.load("rewrite-quality", "v1", "default") is None


def test_user_owned_queue_sync_fails_when_queue_missing() -> None:
    config = load_project_config("tests/fixtures/projects/user_owned_annotation_queue.yaml")

    with pytest.raises(ConfigError, match="Annotation queue not found"):
        sync_annotation_queue(config, DefaultLangfuseGateway(), [], store=_store())


def test_user_owned_queue_does_not_need_score_config_results() -> None:
    config = load_project_config("tests/fixtures/projects/user_owned_annotation_queue.yaml")
    client = DefaultLangfuseGateway()
    client.annotation_queues["queue-user-owned-1"] = {"id": "queue-user-owned-1"}

    result = sync_annotation_queue(
        config,
        client,
        [
            ScoreConfigSyncResult(
                evaluator_name="clarity",
                name="score",
                score_config_id="score-config-1",
                status="created",
                ownership="managed_by_harness",
            )
        ],
        store=_store(),
    )

    assert result.ownership == "user_owned"
