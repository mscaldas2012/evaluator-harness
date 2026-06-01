from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest

from evaluator_harness.annotation_queues import (
    AnnotationQueueReferenceStore,
    managed_queue_name,
    sync_annotation_queue,
)
from evaluator_harness.config import load_project_config
from evaluator_harness.errors import ConfigError
from evaluator_harness.errors import LangfuseError
from evaluator_harness.langfuse_client import LangfuseClient, ScoreConfigSyncResult


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


def test_managed_queue_name_uses_eh_project_version_and_policy() -> None:
    assert (
        managed_queue_name("rewrite-quality", "v1", "default")
        == "EH_rewrite-quality_v1_review_default"
    )


def test_sync_annotation_queue_creates_and_persists_managed_reference() -> None:
    config = load_project_config("tests/fixtures/projects/managed_annotation_queue.yaml")
    client = LangfuseClient()
    store = _store()

    result = sync_annotation_queue(config, client, _score_results(), store=store)

    assert result.status == "created"
    assert result.queue_name == "EH_rewrite-quality_v1_review_default"
    assert result.queue_id == "annotation-queue-1"
    assert Path(result.reference_path or "").exists()


def test_sync_annotation_queue_dry_run_plans_create_without_reference_write() -> None:
    config = load_project_config("tests/fixtures/projects/managed_annotation_queue.yaml")
    client = LangfuseClient()
    store = _store()

    result = sync_annotation_queue(
        config,
        client,
        _score_results(),
        store=store,
        dry_run=True,
    )

    assert result.status == "planned"
    assert result.message == "annotation queue would be created"
    assert result.score_config_ids == ["score-config-1"]
    assert result.reference_path is None
    assert not store.path_for("rewrite-quality", "v1", "default").exists()


def test_sync_annotation_queue_dry_run_reuses_matching_existing_queue() -> None:
    config = load_project_config("tests/fixtures/projects/managed_annotation_queue.yaml")
    client = LangfuseClient()
    client.annotation_queues["annotation-queue-1"] = {
        "id": "annotation-queue-1",
        "name": "EH_rewrite-quality_v1_review_default",
        "score_config_ids": ["score-config-1"],
    }

    result = sync_annotation_queue(
        config,
        client,
        _score_results(),
        store=_store(),
        dry_run=True,
    )

    assert result.status == "reused"
    assert result.queue_id == "annotation-queue-1"
    assert result.message == "matching Langfuse annotation queue already exists"


def test_sync_annotation_queue_dry_run_conflicts_with_single_incompatible_queue() -> None:
    config = load_project_config("tests/fixtures/projects/managed_annotation_queue.yaml")
    client = LangfuseClient()
    client.annotation_queues["other-queue"] = {
        "id": "other-queue",
        "name": "EH_other_v1_review_default",
        "score_config_ids": ["other-score-config"],
    }

    result = sync_annotation_queue(
        config,
        client,
        _score_results(),
        store=_store(),
        dry_run=True,
    )

    assert result.status == "conflict"
    assert result.queue_id == "other-queue"
    assert result.score_config_ids == ["other-score-config"]
    assert "Delete the queue" in (result.message or "")


def test_sync_annotation_queue_reuses_local_managed_reference() -> None:
    config = load_project_config("tests/fixtures/projects/managed_annotation_queue.yaml")
    client = LangfuseClient()
    store = _store()

    first = sync_annotation_queue(config, client, _score_results(), store=store)
    second = sync_annotation_queue(config, client, _score_results(), store=store)

    assert first.queue_id == second.queue_id
    assert second.status == "reused"
    assert len(client.annotation_queues) == 1


def test_sync_annotation_queue_overwrites_stale_local_score_config_reference() -> None:
    config = load_project_config("tests/fixtures/projects/managed_annotation_queue.yaml")
    client = LangfuseClient()
    store = _store()

    first = sync_annotation_queue(config, client, _score_results(), store=store)
    changed_score_results = [
        ScoreConfigSyncResult(
            evaluator_name="clarity",
            name="eh_rewrite_quality_clarity",
            score_config_id="score-config-2",
            status="created",
            ownership="managed_by_harness",
        )
    ]

    second = sync_annotation_queue(config, client, changed_score_results, store=store)

    assert second.status == "reused"
    assert second.queue_id == first.queue_id
    assert second.score_config_ids == ["score-config-1"]
    assert len(client.annotation_queues) == 1


def test_sync_annotation_queue_aligns_queue_score_config_when_reusing_existing_queue() -> None:
    class AligningClient(LangfuseClient):
        def __init__(self) -> None:
            super().__init__()
            self.aligned: list[tuple[str, str]] = []

        def align_score_config_to_existing_id(
            self,
            *,
            target_score_config_id: str,
            managed_name: str,
        ) -> None:
            self.aligned.append((target_score_config_id, managed_name))

    config = load_project_config("tests/fixtures/projects/managed_annotation_queue.yaml")
    client = AligningClient()
    store = _store()
    sync_annotation_queue(config, client, _score_results(), store=store)
    changed_score_results = [
        ScoreConfigSyncResult(
            evaluator_name="clarity",
            name="eh_rewrite_quality_clarity",
            score_config_id="active-score-config",
            status="reused",
            ownership="managed_by_harness",
        )
    ]

    sync_annotation_queue(config, client, changed_score_results, store=store)

    assert client.aligned == [("score-config-1", "eh_rewrite_quality_clarity")]


def test_sync_annotation_queue_reuses_sole_existing_queue_when_plan_limit_is_reached() -> None:
    class PlanLimitedClient(LangfuseClient):
        def create_annotation_queue(self, **kwargs):  # type: ignore[no-untyped-def]
            raise LangfuseError("Maximum number of annotation queues reached on Hobby plan.")

    config = load_project_config("tests/fixtures/projects/managed_annotation_queue.yaml")
    client = PlanLimitedClient()
    client.annotation_queues["existing-live-queue"] = {
        "id": "existing-live-queue",
        "name": "EH_rewrite-quality_v1_review_live-smoke",
        "score_config_ids": ["score-config-1"],
    }
    store = _store()

    result = sync_annotation_queue(config, client, _score_results(), store=store)

    assert result.status == "reused"
    assert result.queue_id == "existing-live-queue"
    assert result.queue_name == "EH_rewrite-quality_v1_review_live-smoke"


def test_sync_annotation_queue_requires_score_config_ids() -> None:
    config = load_project_config("tests/fixtures/projects/managed_annotation_queue.yaml")

    with pytest.raises(ConfigError, match="score config"):
        sync_annotation_queue(config, LangfuseClient(), [], store=_store())
