from __future__ import annotations

import inspect
from typing import Any

from evaluator_harness.config import DatasetItem, DatasetKind, DatasetSource
from evaluator_harness.langfuse_client import (
    AnnotationRoutingResult,
    DatasetSyncResult,
    LangfuseClient,
    ScoreConfigSyncResult,
)
from evaluator_harness.langfuse_in_memory import InMemoryLangfuseGateway


class RecordingGateway:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def sync_dataset(self, *args: Any, **kwargs: Any) -> DatasetSyncResult:
        self.calls.append(("sync_dataset", args, kwargs))
        return DatasetSyncResult(
            name="rewrite/v1",
            version="latest",
            compatibility_version="compat",
            item_count=1,
            status="synced",
        )

    def record_dataset_run_item(self, **kwargs: Any) -> None:
        self.calls.append(("record_dataset_run_item", (), kwargs))

    def sync_score_configs(
        self,
        *args: Any,
        **kwargs: Any,
    ) -> list[ScoreConfigSyncResult]:
        self.calls.append(("sync_score_configs", args, kwargs))
        return [
            ScoreConfigSyncResult(
                evaluator_name="clarity",
                name="eh_clarity",
                score_config_id="score-config-1",
                status="reused",
                ownership="managed_by_harness",
            )
        ]

    def list_prompt_versions(self, name: str | None = None) -> list[dict[str, Any]]:
        self.calls.append(("list_prompt_versions", (name,), {}))
        return [{"name": name, "version": 1, "labels": ["prod"], "config": {}}]

    def traces_for_run(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        self.calls.append(("traces_for_run", args, kwargs))
        return [{"id": "trace-1", "run_id": args[0]}]

    def fetch_scores(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        self.calls.append(("fetch_scores", args, kwargs))
        return [{"trace_id": "trace-1", "name": "clarity", "value": 1}]

    def lookup_baseline(self, *args: Any, **kwargs: Any) -> str:
        self.calls.append(("lookup_baseline", args, kwargs))
        return "baseline-reference"

    def list_evaluators(self) -> list[dict[str, Any]]:
        self.calls.append(("list_evaluators", (), {}))
        return [{"id": "eval-1", "name": "clarity"}]

    def get_evaluator(self, evaluator_id: str) -> dict[str, Any]:
        self.calls.append(("get_evaluator", (evaluator_id,), {}))
        return {"id": evaluator_id, "name": "clarity"}

    def create_evaluator(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(("create_evaluator", (payload,), {}))
        return {"id": "eval-1", **payload}

    def update_evaluator(
        self,
        evaluator_id: str,
        changes: dict[str, Any],
    ) -> dict[str, Any]:
        self.calls.append(("update_evaluator", (evaluator_id, changes), {}))
        return {"id": evaluator_id, **changes}

    def create_prompt_version(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(("create_prompt_version", (payload,), {}))
        return {"version": 1, **payload}

    def create_annotation_queue(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("create_annotation_queue", args, kwargs))
        return {"id": "queue-1", **kwargs}

    def list_annotation_queues(self) -> list[dict[str, Any]]:
        self.calls.append(("list_annotation_queues", (), {}))
        return [{"id": "queue-1", "name": "Review"}]

    def get_annotation_queue(self, queue_id: str) -> dict[str, Any]:
        self.calls.append(("get_annotation_queue", (queue_id,), {}))
        return {"id": queue_id, "name": "Review"}

    def annotation_queue_object_ids(self, queue_id: str) -> set[str]:
        self.calls.append(("annotation_queue_object_ids", (queue_id,), {}))
        return {"trace-1"}

    def route_annotation_items(
        self,
        queue_id: str,
        items: list[dict[str, Any]],
    ) -> AnnotationRoutingResult:
        self.calls.append(("route_annotation_items", (queue_id, items), {}))
        return AnnotationRoutingResult(
            queue_id=queue_id,
            queued_count=len(items),
            skipped_duplicate_count=0,
        )


def test_langfuse_client_preserves_public_constructor_and_workflow_signatures() -> None:
    constructor = inspect.signature(LangfuseClient)
    assert "client" in constructor.parameters
    assert "settings" in constructor.parameters
    assert "http_transport" in constructor.parameters

    workflow_methods = [
        "sync_dataset",
        "record_dataset_run_item",
        "sync_score_configs",
        "list_prompt_versions",
        "create_prompt_version",
        "traces_for_run",
        "fetch_scores",
        "lookup_baseline",
        "list_evaluators",
        "get_evaluator",
        "create_evaluator",
        "update_evaluator",
        "create_annotation_queue",
        "list_annotation_queues",
        "get_annotation_queue",
        "annotation_queue_object_ids",
        "route_annotation_items",
    ]
    for method_name in workflow_methods:
        assert callable(getattr(LangfuseClient(), method_name))


def test_langfuse_client_facade_delegates_workflows_to_gateway() -> None:
    client = LangfuseClient()
    gateway = RecordingGateway()
    client._gateway = gateway
    source = DatasetSource(
        kind=DatasetKind.LOCAL_CSV,
        langfuse_dataset_name="rewrite/v1",
    )

    dataset = client.sync_dataset(source, [DatasetItem(item_id="1", input="Rewrite")])
    client.record_dataset_run_item(
        dataset_sync=dataset,
        item_id="1",
        run_name="baseline-1",
        trace_id="trace-1",
        observation_id=None,
        metadata={},
    )
    client.sync_score_configs(object())  # type: ignore[arg-type]
    assert client.find_prompt_version("prompt-a", label="prod") is not None
    client.create_prompt_version({"name": "prompt-a", "prompt": "Hello"})
    client.traces_for_run("run-1", expected_count=1)
    client.fetch_scores("run-1", trace_ids=["trace-1"])
    assert client.lookup_baseline(selector="latest-compatible") == "baseline-reference"
    client.list_evaluators()
    client.get_evaluator("eval-1")
    client.create_evaluator({"name": "clarity"})
    client.update_evaluator("eval-1", {"active": False})
    queue = client.create_annotation_queue(name="Review", score_config_ids=["score-1"])
    client.list_annotation_queues()
    client.get_annotation_queue(str(queue["id"]))
    client.annotation_queue_object_ids(str(queue["id"]))
    client.route_annotation_items(str(queue["id"]), [{"trace_id": "trace-1"}])

    call_names = [name for name, _args, _kwargs in gateway.calls]
    assert call_names == [
        "sync_dataset",
        "record_dataset_run_item",
        "sync_score_configs",
        "list_prompt_versions",
        "create_prompt_version",
        "traces_for_run",
        "fetch_scores",
        "lookup_baseline",
        "list_evaluators",
        "get_evaluator",
        "create_evaluator",
        "update_evaluator",
        "create_annotation_queue",
        "list_annotation_queues",
        "get_annotation_queue",
        "annotation_queue_object_ids",
        "route_annotation_items",
    ]


def test_langfuse_client_dry_run_uses_in_memory_gateway_without_credentials(
    monkeypatch,
) -> None:
    monkeypatch.delenv("LANGFUSE_PUBLIC_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_SECRET_KEY", raising=False)
    monkeypatch.delenv("LANGFUSE_HOST", raising=False)
    client = LangfuseClient()
    source = DatasetSource(
        kind=DatasetKind.LOCAL_CSV,
        langfuse_dataset_name="rewrite/v1",
    )

    result = client.sync_dataset(
        source,
        [DatasetItem(item_id="1", input="Rewrite")],
        dry_run=True,
    )

    assert isinstance(client._gateway, InMemoryLangfuseGateway)
    assert result.status == "planned"
    assert result.item_count == 1
