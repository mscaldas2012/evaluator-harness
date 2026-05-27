from __future__ import annotations

from evaluator_harness.langfuse_client import LangfuseClient


def test_fake_langfuse_creates_and_lists_annotation_queue() -> None:
    client = LangfuseClient()

    created = client.create_annotation_queue(
        name="EH_rewrite-quality_v1_review_default",
        score_config_ids=["score-config-1"],
        description="Review queue",
    )

    queues = client.list_annotation_queues()
    assert created["id"] == "annotation-queue-1"
    assert queues[0]["name"] == "EH_rewrite-quality_v1_review_default"


def test_fake_langfuse_retrieves_annotation_queue() -> None:
    client = LangfuseClient()
    created = client.create_annotation_queue(
        name="EH_rewrite-quality_v1_review_default",
        score_config_ids=["score-config-1"],
        description="Review queue",
    )

    assert client.get_annotation_queue(created["id"])["id"] == created["id"]


def test_route_annotation_items_records_trace_object_ids() -> None:
    client = LangfuseClient()
    payload = {"trace_id": "trace-1", "item_id": "1", "run_id": "run-1"}

    result = client.route_annotation_items("queue-1", [payload])

    assert result.queued_count == 1
    assert client.annotation_queue_items[0]["object_id"] == "trace-1"
    assert client.annotation_queue_items[0]["object_type"] == "TRACE"
