from __future__ import annotations

from collections.abc import Callable
from typing import Any

from evaluator_harness.errors import ConfigError, LangfuseError
from evaluator_harness.langfuse_mappers import object_to_queue_dict

AnnotationRoutingResultFactory = Callable[..., Any]


def route_annotation_items_workflow(
    owner: Any,
    queue_id: str,
    items: list[dict[str, Any]],
    *,
    result_factory: AnnotationRoutingResultFactory,
) -> Any:
    owner.check_reachable(operation="route-annotation-items")
    queued_count = 0
    skipped_duplicate_count = 0
    existing_live_object_ids = (
        live_annotation_queue_object_ids(owner, queue_id)
        if owner.client is not None
        else set()
    )
    for item in items:
        routed = _route_one_annotation_item(
            owner,
            queue_id=queue_id,
            item=item,
            existing_live_object_ids=existing_live_object_ids,
        )
        if routed is None:
            skipped_duplicate_count += 1
            continue
        owner.annotation_queue_items.append(routed)
        queued_count += 1
    owner.calls.append(
        (
            "route_annotation_items",
            {
                "queue_id": queue_id,
                "queued_count": queued_count,
                "skipped_duplicate_count": skipped_duplicate_count,
            },
        )
    )
    return result_factory(
        queue_id=queue_id,
        queued_count=queued_count,
        skipped_duplicate_count=skipped_duplicate_count,
    )


def annotation_queue_object_ids_workflow(owner: Any, queue_id: str) -> set[str]:
    owner.check_reachable(operation="list-annotation-queue-items")
    if owner.client is not None:
        return live_annotation_queue_object_ids(owner, queue_id)
    return {
        str(item.get("object_id"))
        for item in owner.annotation_queue_items
        if item.get("queue_id") == queue_id and item.get("object_id") is not None
    }


def create_annotation_queue_workflow(
    owner: Any,
    *,
    name: str,
    score_config_ids: list[str],
    description: str | None = None,
) -> dict[str, Any]:
    owner.check_reachable(operation="create-annotation-queue")
    owner.calls.append(
        (
            "create_annotation_queue",
            {
                "name": name,
                "score_config_ids": score_config_ids,
                "description": description,
            },
        )
    )
    if owner.client is not None:
        live_queue = create_live_annotation_queue(
            owner,
            name=name,
            score_config_ids=score_config_ids,
            description=description,
        )
        if live_queue is not None:
            owner.annotation_queues[str(live_queue["id"])] = live_queue
            return live_queue
    queue = {
        "id": f"annotation-queue-{len(owner.annotation_queues) + 1}",
        "name": name,
        "score_config_ids": list(score_config_ids),
        "description": description,
    }
    owner.annotation_queues[queue["id"]] = queue
    return queue


def list_annotation_queues_workflow(owner: Any) -> list[dict[str, Any]]:
    owner.check_reachable(operation="list-annotation-queues")
    owner.calls.append(("list_annotation_queues", {}))
    if owner.client is not None:
        live_queues = list_live_annotation_queues(owner)
        if live_queues is not None:
            for queue in live_queues:
                owner.annotation_queues[str(queue["id"])] = queue
            return live_queues
    return list(owner.annotation_queues.values())


def get_annotation_queue_workflow(owner: Any, queue_id: str) -> dict[str, Any]:
    owner.check_reachable(operation="get-annotation-queue")
    owner.calls.append(("get_annotation_queue", {"queue_id": queue_id}))
    if owner.client is not None:
        live_queue = get_live_annotation_queue(owner, queue_id)
        if live_queue is not None:
            owner.annotation_queues[str(live_queue["id"])] = live_queue
            return live_queue
    queue = owner.annotation_queues.get(queue_id)
    if queue is None:
        raise ConfigError(f"Annotation queue not found: {queue_id}")
    return queue


def build_annotation_queue_payload_workflow(
    owner: Any,
    config: Any,
    selection: Any,
) -> dict[str, Any]:
    trace = owner.trace_by_id(selection.trace_id)
    metadata = trace.get("metadata", {})
    baseline_reference = metadata.get("baseline_reference") or {}
    baseline_run_id = baseline_reference.get("baseline_run_id")
    baseline_output = (
        owner.output_for(run_id=baseline_run_id, item_id=selection.item_id)
        if baseline_run_id
        else trace.get("output")
    )
    return {
        "queue_item_id": f"{selection.run_id}:{selection.trace_id}",
        "run_id": selection.run_id,
        "trace_id": selection.trace_id,
        "item_id": selection.item_id,
        "selection_reason": selection.selection_reason,
        "selection_bucket": selection.selection_bucket,
        "input": trace.get("input"),
        "baseline_output": baseline_output,
        "candidate_output": trace.get("output") if baseline_run_id else None,
        "ground_truth": metadata.get("ground_truth"),
        "trace_context": _trace_context(selection, metadata),
        "evaluators": [
            _evaluator_payload(evaluator, metadata) for evaluator in config.evaluators
        ],
    }


def create_live_annotation_queue(
    owner: Any,
    *,
    name: str,
    score_config_ids: list[str],
    description: str | None,
) -> dict[str, Any] | None:
    annotation_queues = _annotation_queues_api(owner)
    create_queue = getattr(annotation_queues, "create_queue", None)
    if not callable(create_queue):
        return None
    try:
        queue = create_queue(
            name=name,
            score_config_ids=score_config_ids,
            description=description,
        )
    except Exception as exc:
        raise LangfuseError(f"Unable to create annotation queue {name}: {exc}") from exc
    return object_to_queue_dict(queue)


def list_live_annotation_queues(owner: Any) -> list[dict[str, Any]] | None:
    annotation_queues = _annotation_queues_api(owner)
    list_queues = getattr(annotation_queues, "list_queues", None)
    if not callable(list_queues):
        return None
    try:
        page = list_queues(limit=100)
    except Exception as exc:
        raise LangfuseError(f"Unable to list annotation queues: {exc}") from exc
    return [object_to_queue_dict(queue) for queue in getattr(page, "data", [])]


def get_live_annotation_queue(owner: Any, queue_id: str) -> dict[str, Any] | None:
    annotation_queues = _annotation_queues_api(owner)
    get_queue = getattr(annotation_queues, "get_queue", None)
    if not callable(get_queue):
        return None
    try:
        queue = get_queue(queue_id)
    except Exception as exc:
        raise LangfuseError(
            f"Unable to get annotation queue {queue_id}: {exc}"
        ) from exc
    return object_to_queue_dict(queue)


def create_live_annotation_queue_item(
    owner: Any,
    queue_id: str,
    *,
    object_id: str,
) -> dict[str, Any] | None:
    annotation_queues = _annotation_queues_api(owner)
    create_queue_item = getattr(annotation_queues, "create_queue_item", None)
    if not callable(create_queue_item):
        return None
    try:
        from langfuse.api.annotation_queues.types.annotation_queue_object_type import (
            AnnotationQueueObjectType,
        )
        from langfuse.api.annotation_queues.types.annotation_queue_status import (
            AnnotationQueueStatus,
        )

        item = create_queue_item(
            queue_id,
            object_id=object_id,
            object_type=AnnotationQueueObjectType.TRACE,
            status=AnnotationQueueStatus.PENDING,
        )
    except Exception as exc:
        message = str(exc).lower()
        if "duplicate" in message or "already" in message:
            return {"_duplicate": True}
        raise LangfuseError(
            f"Unable to create annotation queue item for trace {object_id}: {exc}"
        ) from exc
    return object_to_queue_dict(item)


def live_annotation_queue_object_ids(owner: Any, queue_id: str) -> set[str]:
    annotation_queues = _annotation_queues_api(owner)
    list_queue_items = getattr(annotation_queues, "list_queue_items", None)
    if not callable(list_queue_items):
        return set()
    object_ids: set[str] = set()
    page_number = 1
    while True:
        try:
            page = list_queue_items(queue_id, page=page_number, limit=100)
        except Exception as exc:
            raise LangfuseError(
                f"Unable to list annotation queue items for {queue_id}: {exc}"
            ) from exc
        for item in getattr(page, "data", None) or []:
            queue_item = object_to_queue_dict(item)
            object_id = queue_item.get("object_id") or queue_item.get("objectId")
            if object_id is not None:
                object_ids.add(str(object_id))
        meta = getattr(page, "meta", None)
        total_pages = int(getattr(meta, "total_pages", page_number) or page_number)
        if page_number >= total_pages:
            break
        page_number += 1
    return object_ids


def _route_one_annotation_item(
    owner: Any,
    *,
    queue_id: str,
    item: dict[str, Any],
    existing_live_object_ids: set[str],
) -> dict[str, Any] | None:
    object_id = str(item.get("trace_id"))
    if object_id in existing_live_object_ids:
        return None
    queue_item_id = str(
        item.get("queue_item_id") or f"{item.get('run_id')}:{item.get('trace_id')}"
    )
    key = (queue_id, queue_item_id)
    if key in owner._annotation_queue_keys:
        return None
    owner._annotation_queue_keys.add(key)
    routed_item = {
        "queue_id": queue_id,
        "queue_item_id": queue_item_id,
        "object_id": item.get("trace_id"),
        "object_type": "TRACE",
        **item,
    }
    if owner.client is None:
        return routed_item
    live_item = create_live_annotation_queue_item(owner, queue_id, object_id=object_id)
    if live_item is not None and live_item.get("_duplicate"):
        return None
    if live_item is not None:
        routed_item["langfuse_queue_item_id"] = live_item.get("id")
        existing_live_object_ids.add(object_id)
    return routed_item


def _annotation_queues_api(owner: Any) -> Any:
    return getattr(getattr(owner.client, "api", None), "annotation_queues", None)


def _trace_context(selection: Any, metadata: dict[str, Any]) -> dict[str, Any]:
    context = {
        "trace_id": selection.trace_id,
        "run_id": selection.run_id,
        "item_comparison_session_id": metadata.get("item_comparison_session_id"),
        "prompt_shape": metadata.get("prompt_shape"),
        "prompt_roles": metadata.get("prompt_roles"),
        "prompt_identity": metadata.get("prompt_identity"),
        "baseline_prompt_identity": metadata.get("baseline_prompt_identity"),
        "candidate_prompt_identity": metadata.get("candidate_prompt_identity"),
        "parameter_identity": metadata.get("parameter_identity"),
        "generation_parameter_hash": metadata.get("generation_parameter_hash"),
        "variant_identity": metadata.get("variant_identity"),
    }
    if metadata.get("scenario_name") is not None:
        context.update(
            {
                "scenario_group": metadata.get("scenario_group"),
                "scenario_name": metadata.get("scenario_name"),
                "scenario_display_name": metadata.get("scenario_display_name"),
            }
        )
    return context


def _evaluator_payload(evaluator: Any, metadata: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "name": evaluator.name,
        "version": evaluator.version,
        "type": evaluator.type,
    }
    if evaluator.blind:
        return payload
    return {
        **payload,
        "provider": metadata.get("provider"),
        "model": metadata.get("model"),
    }
