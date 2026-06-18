from __future__ import annotations

from typing import Any

import httpx

from evaluator_harness.errors import ConfigError, LangfuseError
from evaluator_harness.langfuse_mappers import (
    extract_rest_collection,
    object_to_evaluator_dict,
    rest_custom_evaluator_payload,
    rest_evaluation_rule_payload,
    rest_evaluation_rule_update_payload,
)

UNSTABLE_EVALUATION_RULES_PATH = "/api/public/unstable/evaluation-rules"
UNSTABLE_EVALUATORS_PATH = "/api/public/unstable/evaluators"


def list_evaluators_workflow(owner: Any) -> list[dict[str, Any]]:
    owner.check_reachable(operation="list-evaluators")
    owner.calls.append(("list_evaluators", {}))
    if owner.client is not None:
        return list_live_evaluators(owner)
    return list(owner.evaluators.values())


def get_evaluator_workflow(owner: Any, evaluator_id: str) -> dict[str, Any] | None:
    owner.check_reachable(operation="get-evaluator")
    owner.calls.append(("get_evaluator", {"evaluator_id": evaluator_id}))
    if owner.client is not None:
        try:
            return get_live_evaluator(owner, evaluator_id)
        except NotImplementedError:
            return None
    return owner.evaluators.get(evaluator_id)


def create_evaluator_workflow(owner: Any, payload: dict[str, Any]) -> dict[str, Any]:
    owner.check_reachable(operation="create-evaluator")
    owner.calls.append(("create_evaluator", payload))
    if owner.client is not None:
        return create_live_evaluator(owner, payload)
    evaluator_id = f"eval-{len(owner.evaluators) + 1}"
    evaluator = {"id": evaluator_id, **payload, "active": True}
    owner.evaluators[evaluator_id] = evaluator
    return evaluator


def update_evaluator_workflow(
    owner: Any,
    evaluator_id: str,
    changes: dict[str, Any],
) -> dict[str, Any]:
    owner.check_reachable(operation="update-evaluator")
    owner.calls.append(
        ("update_evaluator", {"evaluator_id": evaluator_id, "changes": changes})
    )
    if owner.client is not None:
        return update_live_evaluator(owner, evaluator_id, changes)
    if evaluator_id not in owner.evaluators:
        raise ConfigError(f"Evaluator not found: {evaluator_id}")
    owner.evaluators[evaluator_id].update(changes)
    return owner.evaluators[evaluator_id]


def inactivate_evaluator_workflow(
    owner: Any,
    evaluator_id: str,
    *,
    comment: str | None = None,
) -> dict[str, Any]:
    owner.check_reachable(operation="inactivate-evaluator")
    owner.calls.append(
        (
            "inactivate_evaluator",
            {"evaluator_id": evaluator_id, "comment": comment},
        )
    )
    changes: dict[str, Any] = {"active": False}
    if comment:
        changes["comment"] = comment
    return owner.update_evaluator(evaluator_id, changes)


def supports_evaluator_backfill(owner: Any, target: str) -> bool:
    return target in owner.evaluator_backfill_targets


def list_live_evaluators(owner: Any) -> list[dict[str, Any]]:
    evaluators = _sdk_evaluators(owner)
    list_evaluators = getattr(evaluators, "list", None) or getattr(
        evaluators,
        "get",
        None,
    )
    if not callable(list_evaluators):
        return list_rest_evaluators(owner)
    try:
        page = list_evaluators(limit=100)
    except Exception as exc:
        raise LangfuseError(f"Unable to list Langfuse evaluators: {exc}") from exc
    return [object_to_evaluator_dict(item) for item in getattr(page, "data", [])]


def get_live_evaluator(owner: Any, evaluator_id: str) -> dict[str, Any]:
    evaluators = _sdk_evaluators(owner)
    get_by_id = getattr(evaluators, "get_by_id", None) or getattr(
        evaluators,
        "get",
        None,
    )
    if not callable(get_by_id):
        return get_rest_evaluator(owner, evaluator_id)
    try:
        return object_to_evaluator_dict(get_by_id(evaluator_id))
    except Exception as exc:
        raise LangfuseError(
            f"Unable to get Langfuse evaluator {evaluator_id}: {exc}"
        ) from exc


def create_live_evaluator(owner: Any, payload: dict[str, Any]) -> dict[str, Any]:
    evaluators = _sdk_evaluators(owner)
    create = getattr(evaluators, "create", None)
    if not callable(create):
        return create_rest_evaluator(owner, payload)
    try:
        return object_to_evaluator_dict(create(**payload))
    except Exception as exc:
        raise LangfuseError(
            f"Unable to create Langfuse evaluator {payload.get('display_name')}: {exc}"
        ) from exc


def update_live_evaluator(
    owner: Any,
    evaluator_id: str,
    changes: dict[str, Any],
) -> dict[str, Any]:
    evaluators = _sdk_evaluators(owner)
    update = getattr(evaluators, "update", None)
    if not callable(update):
        return update_rest_evaluator(owner, evaluator_id, changes)
    try:
        return object_to_evaluator_dict(update(evaluator_id, **changes))
    except Exception as exc:
        raise LangfuseError(
            f"Unable to update Langfuse evaluator {evaluator_id}: {exc}"
        ) from exc


def list_rest_evaluators(owner: Any) -> list[dict[str, Any]]:
    payload = rest_evaluator_request(
        owner,
        "GET",
        UNSTABLE_EVALUATION_RULES_PATH,
        operation="list Langfuse evaluators",
    )
    return [object_to_evaluator_dict(item) for item in extract_rest_collection(payload)]


def get_rest_evaluator(owner: Any, evaluator_id: str) -> dict[str, Any] | None:
    try:
        payload = rest_evaluator_request(
            owner,
            "GET",
            f"{UNSTABLE_EVALUATION_RULES_PATH}/{evaluator_id}",
            operation=f"get Langfuse evaluator {evaluator_id}",
        )
    except LangfuseError as exc:
        if "404" in str(exc):
            return None
        raise
    return object_to_evaluator_dict(payload)


def create_rest_evaluator(owner: Any, payload: dict[str, Any]) -> dict[str, Any]:
    evaluator_ref = resolve_rest_evaluator_reference(owner, payload)
    response = rest_evaluator_request(
        owner,
        "POST",
        UNSTABLE_EVALUATION_RULES_PATH,
        json_payload=rest_evaluation_rule_payload(payload, evaluator_ref=evaluator_ref),
        operation=f"create Langfuse evaluator {payload.get('display_name')}",
    )
    return object_to_evaluator_dict(response)


def update_rest_evaluator(
    owner: Any,
    evaluator_id: str,
    changes: dict[str, Any],
) -> dict[str, Any]:
    json_payload = rest_evaluation_rule_update_payload(changes)
    if not json_payload:
        fields = ", ".join(sorted(changes)) or "<none>"
        raise ConfigError(
            "No Langfuse evaluator update fields can be sent via the "
            f"evaluation-rules REST API. Requested fields: {fields}."
        )
    response = rest_evaluator_request(
        owner,
        "PATCH",
        f"{UNSTABLE_EVALUATION_RULES_PATH}/{evaluator_id}",
        json_payload=json_payload,
        operation=f"update Langfuse evaluator {evaluator_id}",
    )
    return object_to_evaluator_dict(response)


def resolve_rest_evaluator_reference(
    owner: Any,
    payload: dict[str, Any],
) -> dict[str, str]:
    source_type = payload.get("source_type")
    if source_type == "catalog":
        name = str(
            payload.get("catalog_ref")
            or payload.get("name")
            or payload.get("display_name")
        )
        return {"name": name, "scope": "managed"}
    evaluator_name = str(payload.get("name") or payload.get("display_name"))
    if source_type == "custom" or payload.get("prompt"):
        created = rest_evaluator_request(
            owner,
            "POST",
            UNSTABLE_EVALUATORS_PATH,
            json_payload=rest_custom_evaluator_payload(payload),
            operation=f"create Langfuse evaluator template {evaluator_name}",
        )
        return {
            "name": str(created.get("name") or evaluator_name),
            "scope": str(created.get("scope") or "project"),
        }
    return {
        "name": evaluator_name,
        "scope": str(payload.get("evaluator_scope") or "project"),
    }


def rest_evaluator_request(
    owner: Any,
    method: str,
    path: str,
    *,
    operation: str,
    json_payload: dict[str, Any] | None = None,
) -> Any:
    if owner.settings is None:
        raise NotImplementedError(
            "Installed Langfuse SDK/API does not expose evaluator operations "
            "and REST credentials are unavailable"
        )
    owner.settings.require_langfuse()
    try:
        with httpx.Client(
            base_url=str(owner.settings.langfuse_host).rstrip("/"),
            auth=(
                str(owner.settings.langfuse_public_key),
                str(owner.settings.langfuse_secret_key),
            ),
            timeout=30.0,
            transport=owner.http_transport,
        ) as http_client:

            def request_once() -> Any:
                response = http_client.request(method, path, json=json_payload)
                response.raise_for_status()
                if not response.content:
                    return {}
                return response.json()

            return owner._with_langfuse_retries(
                operation=operation,
                callback=request_once,
            )
    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:500]
        raise LangfuseError(
            f"Unable to {operation} via unstable evaluation-rules REST API: "
            f"HTTP {exc.response.status_code} {body}"
        ) from exc
    except httpx.HTTPError as exc:
        raise LangfuseError(
            f"Unable to {operation} via unstable evaluation-rules REST API: {exc}"
        ) from exc


def _sdk_evaluators(owner: Any) -> Any:
    return getattr(getattr(owner.client, "api", None), "evaluators", None)
