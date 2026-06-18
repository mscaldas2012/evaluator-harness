from __future__ import annotations

from typing import Any

from evaluator_harness.langfuse_gateways import (
    GatewayFactoryInput,
    build_langfuse_gateway,
    should_use_in_memory_gateway,
)
from evaluator_harness.langfuse_in_memory import InMemoryLangfuseGateway
from evaluator_harness.langfuse_mappers import (
    object_to_evaluator_dict,
    object_to_prompt_dict,
    object_to_score_config_dict,
    object_to_score_dict,
)
from evaluator_harness.langfuse_rest import LangfuseRestGateway
from evaluator_harness.langfuse_sdk import (
    LangfuseSdkGateway,
    callable_attribute,
    flush_if_supported,
    update_observation,
)


class GatewayOwner:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def _sync_dataset_impl(self, *args: Any, **kwargs: Any) -> str:
        self.calls.append(("sync_dataset", args, kwargs))
        return "dataset"

    def _record_dataset_run_item_impl(self, **kwargs: Any) -> None:
        self.calls.append(("record_dataset_run_item", (), kwargs))

    def _sync_score_configs_impl(self, *args: Any, **kwargs: Any) -> list[str]:
        self.calls.append(("sync_score_configs", args, kwargs))
        return ["score-config"]

    def _fetch_scores_impl(self, *args: Any, **kwargs: Any) -> list[str]:
        self.calls.append(("fetch_scores", args, kwargs))
        return ["score"]

    def _list_prompt_versions_impl(self, *args: Any, **kwargs: Any) -> list[str]:
        self.calls.append(("list_prompt_versions", args, kwargs))
        return ["prompt"]

    def _create_prompt_version_impl(self, *args: Any, **kwargs: Any) -> str:
        self.calls.append(("create_prompt_version", args, kwargs))
        return "created-prompt"

    def _traces_for_run_impl(self, *args: Any, **kwargs: Any) -> list[str]:
        self.calls.append(("traces_for_run", args, kwargs))
        return ["trace"]

    def _lookup_baseline_impl(self, *args: Any, **kwargs: Any) -> str:
        self.calls.append(("lookup_baseline", args, kwargs))
        return "baseline"

    def _list_evaluators_impl(self) -> list[str]:
        self.calls.append(("list_evaluators", (), {}))
        return ["evaluator"]

    def _create_annotation_queue_impl(self, *args: Any, **kwargs: Any) -> str:
        self.calls.append(("create_annotation_queue", args, kwargs))
        return "queue"

    def _route_annotation_items_impl(self, *args: Any, **kwargs: Any) -> str:
        self.calls.append(("route_annotation_items", args, kwargs))
        return "routed"

    def _annotation_queue_object_ids_impl(self, *args: Any, **kwargs: Any) -> set[str]:
        self.calls.append(("annotation_queue_object_ids", args, kwargs))
        return {"trace-1"}


class RestOwner:
    def __init__(self) -> None:
        self.calls: list[tuple[str, tuple[Any, ...], dict[str, Any]]] = []

    def _rest_evaluator_request(
        self,
        method: str,
        path: str,
        *,
        json_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.calls.append(("request", (method, path), {"json_payload": json_payload}))
        return {"ok": True}

    def _list_rest_evaluators(self) -> list[dict[str, str]]:
        self.calls.append(("list_evaluators", (), {}))
        return [{"id": "eval-1"}]

    def _get_rest_evaluator(self, evaluator_id: str) -> dict[str, str]:
        self.calls.append(("get_evaluator", (evaluator_id,), {}))
        return {"id": evaluator_id}

    def _create_rest_evaluator(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.calls.append(("create_evaluator", (payload,), {}))
        return {"id": "eval-1", **payload}

    def _update_rest_evaluator(
        self,
        evaluator_id: str,
        changes: dict[str, Any],
    ) -> dict[str, Any]:
        self.calls.append(("update_evaluator", (evaluator_id, changes), {}))
        return {"id": evaluator_id, **changes}

    def _list_live_annotation_queues(self) -> list[dict[str, str]]:
        self.calls.append(("list_annotation_queues", (), {}))
        return [{"id": "queue-1"}]

    def _get_live_annotation_queue(self, queue_id: str) -> dict[str, str]:
        self.calls.append(("get_annotation_queue", (queue_id,), {}))
        return {"id": queue_id}

    def _create_live_annotation_queue(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("create_annotation_queue", (), kwargs))
        return {"id": "queue-1", **kwargs}

    def _live_annotation_queue_object_ids(self, queue_id: str) -> set[str]:
        self.calls.append(("annotation_queue_object_ids", (queue_id,), {}))
        return {"trace-1"}

    def _create_live_annotation_queue_item(
        self,
        queue_id: str,
        *,
        object_id: str,
    ) -> dict[str, str]:
        self.calls.append(
            ("create_annotation_queue_item", (queue_id,), {"object_id": object_id})
        )
        return {"id": "queue-item-1"}


def test_gateway_factory_selects_in_memory_without_live_client() -> None:
    config = GatewayFactoryInput(client=None)

    assert should_use_in_memory_gateway(config) is True
    gateway = build_langfuse_gateway(owner=object(), config=config)
    assert isinstance(gateway, InMemoryLangfuseGateway)


def test_gateway_factory_selects_sdk_with_rest_fallback_for_live_client() -> None:
    gateway = build_langfuse_gateway(
        owner=GatewayOwner(),
        config=GatewayFactoryInput(client=object()),
    )

    assert isinstance(gateway, LangfuseSdkGateway)
    assert isinstance(gateway.rest, LangfuseRestGateway)


def test_sdk_gateway_delegates_live_capability_surfaces_to_owner() -> None:
    owner = GatewayOwner()
    gateway = LangfuseSdkGateway(owner=owner, client=object())

    assert gateway.sync_dataset("source", ["item"]) == "dataset"
    gateway.record_dataset_run_item(dataset_sync="dataset", item_id="1")
    assert gateway.sync_score_configs("config") == ["score-config"]
    assert gateway.fetch_scores("run-1", trace_ids=["trace-1"]) == ["score"]
    assert gateway.list_prompt_versions("prompt") == ["prompt"]
    assert gateway.create_prompt_version({"name": "prompt"}) == "created-prompt"
    assert gateway.traces_for_run("run-1") == ["trace"]
    assert gateway.lookup_baseline(selector="latest-compatible") == "baseline"
    assert gateway.list_evaluators() == ["evaluator"]
    assert gateway.create_annotation_queue(name="Review") == "queue"
    assert gateway.route_annotation_items("queue-1", []) == "routed"
    assert gateway.annotation_queue_object_ids("queue-1") == {"trace-1"}


def test_rest_gateway_delegates_fallback_evaluator_and_queue_operations() -> None:
    owner = RestOwner()
    gateway = LangfuseRestGateway(owner=owner, settings=None)

    assert gateway.request("GET", "/resource") == {"ok": True}
    assert gateway.list_evaluators() == [{"id": "eval-1"}]
    assert gateway.get_evaluator("eval-1") == {"id": "eval-1"}
    assert gateway.create_evaluator({"name": "clarity"}) == {
        "id": "eval-1",
        "name": "clarity",
    }
    assert gateway.update_evaluator("eval-1", {"active": False}) == {
        "id": "eval-1",
        "active": False,
    }
    assert gateway.list_annotation_queues() == [{"id": "queue-1"}]
    assert gateway.get_annotation_queue("queue-1") == {"id": "queue-1"}
    assert gateway.create_annotation_queue(name="Review") == {
        "id": "queue-1",
        "name": "Review",
    }
    assert gateway.annotation_queue_object_ids("queue-1") == {"trace-1"}
    assert gateway.create_annotation_queue_item("queue-1", object_id="trace-1") == {
        "id": "queue-item-1"
    }


def test_sdk_callable_guards_handle_missing_and_non_callable_attributes() -> None:
    assert callable_attribute(None, "flush") is None
    assert callable_attribute(object(), "flush") is None
    client = type("Client", (), {"flush": "not-callable"})()
    assert callable_attribute(client, "flush") is None


def test_sdk_callable_guards_flush_and_update_only_when_supported() -> None:
    calls: list[tuple[str, dict[str, Any]]] = []

    class Client:
        def flush(self) -> None:
            calls.append(("flush", {}))

    class Observation:
        def update(self, **kwargs: Any) -> None:
            calls.append(("update", kwargs))

    flush_if_supported(Client())
    assert update_observation(Observation(), output="ok") is True
    assert update_observation(None, output="ignored") is False
    assert calls == [
        ("flush", {}),
        ("update", {"output": "ok"}),
    ]


def test_in_memory_and_live_compatible_score_shapes_match() -> None:
    live_score = object_to_score_dict(
        {
            "id": "score-1",
            "name": "clarity",
            "value": 1,
            "traceId": "trace-1",
            "comment": "ok",
            "metadata": {"source": "test"},
        }
    )
    gateway = InMemoryLangfuseGateway()
    record = gateway.record_score(live_score)

    assert record.__dict__ == {
        "id": live_score["id"],
        "name": live_score["name"],
        "value": live_score["value"],
        "trace_id": live_score["trace_id"],
        "observation_id": None,
        "dataset_run_id": None,
        "comment": live_score["comment"],
        "source": None,
        "metadata": live_score["metadata"],
    }


def test_in_memory_and_live_compatible_prompt_evaluator_and_config_shapes_match() -> (
    None
):
    gateway = InMemoryLangfuseGateway()

    live_prompt = object_to_prompt_dict(
        {
            "name": "rewrite",
            "version": "2",
            "prompt": "Rewrite {{input}}",
            "labels": ["prod"],
            "config": {"artifact_version": "v2"},
        }
    )
    prompt = gateway.create_prompt_version(live_prompt)

    live_evaluator = object_to_evaluator_dict(
        {
            "evaluationRuleId": "eval-1",
            "name": "clarity",
            "enabled": True,
            "scoreConfigId": "score-config-1",
            "sampling": 0.25,
        }
    )
    evaluator = gateway.create_evaluator(live_evaluator)

    live_score_config = object_to_score_config_dict(
        {
            "id": "score-config-1",
            "name": "clarity",
            "dataType": "NUMERIC",
            "minValue": 0,
            "maxValue": 1,
            "isArchived": False,
        }
    )
    gateway.record_score_config(live_score_config)

    assert prompt.name == live_prompt["name"]
    assert prompt.version == live_prompt["version"]
    assert evaluator.id == live_evaluator["id"]
    assert evaluator.active == live_evaluator["active"]
    assert gateway.list_score_configs()[0].__dict__ == {
        "id": live_score_config["id"],
        "name": live_score_config["name"],
        "data_type": live_score_config["data_type"],
        "min_value": live_score_config["min_value"],
        "max_value": live_score_config["max_value"],
        "categories": live_score_config["categories"],
        "description": None,
        "archived": live_score_config["archived"],
        "metadata": {},
    }
