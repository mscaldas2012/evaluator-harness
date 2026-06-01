from __future__ import annotations

from types import SimpleNamespace

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


def test_route_annotation_items_skips_existing_live_queue_item() -> None:
    class FakeAnnotationQueuesApi:
        def list_queue_items(self, queue_id, *, page, limit):
            return SimpleNamespace(
                data=[SimpleNamespace(id="item-1", object_id="trace-1")],
                meta=SimpleNamespace(total_pages=1),
            )

        def create_queue_item(self, *args, **kwargs):
            raise AssertionError("duplicate live queue item should not be created")

    client = LangfuseClient(
        client=SimpleNamespace(
            api=SimpleNamespace(annotation_queues=FakeAnnotationQueuesApi())
        )
    )
    payload = {"trace_id": "trace-1", "item_id": "1", "run_id": "run-1"}

    result = client.route_annotation_items("queue-1", [payload])

    assert result.queued_count == 0
    assert result.skipped_duplicate_count == 1
    assert client.annotation_queue_items == []


def test_route_annotation_items_creates_new_live_queue_item_once() -> None:
    class FakeAnnotationQueuesApi:
        def __init__(self) -> None:
            self.created = []

        def list_queue_items(self, queue_id, *, page, limit):
            return SimpleNamespace(data=[], meta=SimpleNamespace(total_pages=1))

        def create_queue_item(self, queue_id, **kwargs):
            self.created.append((queue_id, kwargs))
            return SimpleNamespace(id="item-1", object_id=kwargs["object_id"])

    api = FakeAnnotationQueuesApi()
    client = LangfuseClient(
        client=SimpleNamespace(api=SimpleNamespace(annotation_queues=api))
    )
    payload = {"trace_id": "trace-1", "item_id": "1", "run_id": "run-1"}

    result = client.route_annotation_items("queue-1", [payload, payload])

    assert result.queued_count == 1
    assert result.skipped_duplicate_count == 1
    assert api.created[0][1]["object_id"] == "trace-1"


def test_annotation_queue_object_ids_reads_fake_queue_items() -> None:
    client = LangfuseClient()
    client.annotation_queue_items.append(
        {
            "queue_id": "queue-1",
            "object_id": "trace-1",
        }
    )
    client.annotation_queue_items.append(
        {
            "queue_id": "queue-2",
            "object_id": "trace-2",
        }
    )

    assert client.annotation_queue_object_ids("queue-1") == {"trace-1"}
