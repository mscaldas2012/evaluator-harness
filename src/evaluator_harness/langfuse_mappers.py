from __future__ import annotations

from typing import Any


def _raw_object_dict(value: Any, keys: tuple[str, ...]) -> dict[str, Any]:
    if isinstance(value, dict):
        return dict(value)
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "dict"):
        return value.dict()
    return {key: getattr(value, key) for key in keys if hasattr(value, key)}


def object_to_queue_dict(value: Any) -> dict[str, Any]:
    raw = _raw_object_dict(
        value,
        (
            "id",
            "name",
            "description",
            "score_config_ids",
            "scoreConfigIds",
            "object_id",
            "objectId",
            "object_type",
            "objectType",
            "status",
        ),
    )
    _copy_alias(raw, "scoreConfigIds", "score_config_ids")
    _copy_alias(raw, "objectId", "object_id")
    _copy_alias(raw, "objectType", "object_type")
    return raw


def object_to_score_config_dict(value: Any) -> dict[str, Any]:
    raw = _raw_object_dict(
        value,
        (
            "id",
            "name",
            "data_type",
            "dataType",
            "min_value",
            "minValue",
            "max_value",
            "maxValue",
            "categories",
            "description",
            "archived",
            "is_archived",
            "isArchived",
        ),
    )
    _copy_alias(raw, "is_archived", "archived")
    _copy_alias(raw, "isArchived", "archived")
    _copy_alias(raw, "dataType", "data_type")
    _copy_alias(raw, "minValue", "min_value")
    _copy_alias(raw, "maxValue", "max_value")
    if hasattr(raw.get("data_type"), "value"):
        raw["data_type"] = raw["data_type"].value
    raw["categories"] = normalize_score_categories(raw.get("categories"))
    return raw


def object_to_score_dict(value: Any) -> dict[str, Any]:
    raw = _raw_object_dict(
        value,
        (
            "id",
            "name",
            "value",
            "score",
            "string_value",
            "stringValue",
            "trace_id",
            "traceId",
            "observation_id",
            "observationId",
            "dataset_run_id",
            "datasetRunId",
            "comment",
            "source",
            "timestamp",
            "metadata",
        ),
    )
    _copy_alias(raw, "traceId", "trace_id")
    _copy_alias(raw, "observationId", "observation_id")
    _copy_alias(raw, "datasetRunId", "dataset_run_id")
    _copy_alias(raw, "stringValue", "string_value")
    if "source" in raw and hasattr(raw["source"], "value"):
        raw["source"] = raw["source"].value
    for key in ("trace_id", "observation_id", "dataset_run_id"):
        if raw.get(key) is not None:
            raw[key] = str(raw[key])
    return raw


def object_to_prompt_dict(value: Any) -> dict[str, Any]:
    raw = _raw_object_dict(
        value,
        (
            "name",
            "version",
            "prompt",
            "type",
            "config",
            "labels",
            "tags",
            "commit_message",
            "commitMessage",
            "versions",
        ),
    )
    _copy_alias(raw, "commitMessage", "commit_message")
    if raw.get("version") is not None:
        raw["version"] = int(raw["version"])
    raw.setdefault("labels", [])
    raw.setdefault("tags", [])
    return raw


def extract_rest_collection(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in ("data", "items", "evaluationRules", "evaluation_rules"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return []


def rest_custom_evaluator_payload(payload: dict[str, Any]) -> dict[str, Any]:
    name = str(payload.get("name") or payload.get("display_name"))
    output_definition = (
        payload.get("outputDefinition")
        or payload.get("output_definition")
        or {
            "dataType": "NUMERIC",
            "reasoning": {"description": "Explain the score."},
            "score": {"description": "Score."},
        }
    )
    result: dict[str, Any] = {
        "name": name,
        "prompt": str(payload.get("prompt") or ""),
        "outputDefinition": output_definition,
    }
    model_config = (
        payload.get("modelConfig")
        or payload.get("model_config")
        or rest_model_config(payload)
    )
    if model_config:
        result["modelConfig"] = model_config
    return result


def rest_model_config(payload: dict[str, Any]) -> dict[str, str]:
    model_config: dict[str, str] = {}
    if payload.get("llm_connection"):
        model_config["provider"] = str(payload["llm_connection"])
    if payload.get("judge_model"):
        model_config["model"] = str(payload["judge_model"])
    if {"provider", "model"} <= set(model_config):
        return model_config
    return {}


def rest_evaluation_rule_payload(
    payload: dict[str, Any],
    *,
    evaluator_ref: dict[str, str],
) -> dict[str, Any]:
    result = {
        "name": str(payload.get("name") or payload.get("display_name")),
        "evaluator": evaluator_ref,
        "target": str(payload.get("target") or "observation"),
        "enabled": bool(payload.get("enabled", payload.get("active", True))),
        "sampling": sampling_fraction(payload.get("sampling_percent")),
        "filter": rest_evaluation_rule_filters(payload.get("filters") or {}),
        "mapping": rest_evaluation_rule_mapping(payload.get("variables") or {}),
    }
    if payload.get("score_config_id"):
        result["scoreConfigId"] = str(payload["score_config_id"])
    return result


def rest_evaluation_rule_update_payload(changes: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if "display_name" in changes or "name" in changes:
        payload["name"] = str(changes.get("name") or changes.get("display_name"))
    if "active" in changes or "enabled" in changes:
        payload["enabled"] = bool(changes.get("enabled", changes.get("active")))
    if "sampling_percent" in changes:
        payload["sampling"] = sampling_fraction(changes.get("sampling_percent"))
    if "score_config_id" in changes:
        payload["scoreConfigId"] = str(changes["score_config_id"])
    if "target" in changes:
        payload["target"] = str(changes["target"])
    if "filters" in changes:
        filters = changes.get("filters") or {}
        payload["target"] = str(
            filters.get("target") or changes.get("target") or "observation"
        )
        payload["filter"] = rest_evaluation_rule_filters(filters)
    if "variables" in changes:
        payload["mapping"] = rest_evaluation_rule_mapping(
            changes.get("variables") or {}
        )
    return payload


def sampling_fraction(value: Any) -> float:
    if value is None:
        return 1.0
    numeric = float(value)
    return numeric / 100 if numeric > 1 else numeric


def rest_evaluation_rule_mapping(variables: dict[str, str]) -> list[dict[str, Any]]:
    mapping: list[dict[str, Any]] = []
    for variable, path in variables.items():
        if path.endswith(".input"):
            mapping.append({"variable": variable, "source": "input"})
        elif path.endswith(".output"):
            mapping.append({"variable": variable, "source": "output"})
        elif ".metadata." in path:
            metadata_key = path.rsplit(".metadata.", 1)[1]
            mapping.append(
                {
                    "variable": variable,
                    "source": "metadata",
                    "jsonPath": f"$.{metadata_key}",
                }
            )
    return mapping


def rest_evaluation_rule_filters(filters: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for key in ("project", "project_version", "evaluator_set_id", "observation_role"):
        if filters.get(key):
            result.append(
                {
                    "type": "stringObject",
                    "column": "metadata",
                    "key": key,
                    "operator": "contains" if key == "evaluator_set_id" else "=",
                    "value": str(filters[key]),
                }
            )
    return result


def object_to_evaluator_dict(value: Any) -> dict[str, Any]:
    raw = _raw_object_dict(
        value,
        (
            "id",
            "evaluationRuleId",
            "name",
            "display_name",
            "displayName",
            "active",
            "enabled",
            "filters",
            "variables",
            "score_config_id",
            "scoreConfigId",
            "sampling_percent",
            "samplingPercent",
            "sampling",
            "target",
            "mapping",
            "filter",
        ),
    )
    _copy_alias(raw, "evaluationRuleId", "id")
    _copy_alias(raw, "displayName", "display_name")
    _copy_alias(raw, "scoreConfigId", "score_config_id")
    _copy_alias(raw, "samplingPercent", "sampling_percent")
    if "sampling" in raw and "sampling_percent" not in raw:
        raw["sampling_percent"] = int(float(raw["sampling"]) * 100)
    if "mapping" in raw and "variables" not in raw:
        raw["variables"] = rest_mapping_to_variables(raw["mapping"])
    if "filter" in raw and "filters" not in raw:
        raw["filters"] = rest_filters_to_internal(raw["filter"])
    _copy_alias(raw, "enabled", "active")
    return raw


def rest_mapping_to_variables(mapping: Any) -> dict[str, str]:
    if not isinstance(mapping, list):
        return {}
    variables: dict[str, str] = {}
    for item in mapping:
        if not isinstance(item, dict) or not item.get("variable"):
            continue
        source = item.get("source")
        variable = str(item["variable"])
        if source == "input":
            variables[variable] = "observation.input"
        elif source == "output":
            variables[variable] = "observation.output"
        elif source == "metadata":
            json_path = str(item.get("jsonPath") or "")
            metadata_key = json_path[2:] if json_path.startswith("$.") else variable
            variables[variable] = f"trace.metadata.{metadata_key}"
    return variables


def rest_filters_to_internal(filters: Any) -> dict[str, Any]:
    if not isinstance(filters, list):
        return {}
    internal: dict[str, Any] = {}
    for item in filters:
        if not isinstance(item, dict):
            continue
        column = item.get("column")
        value = item.get("value")
        if column == "name" and isinstance(value, list) and value:
            internal["_has_top_level_name_filter"] = True
        elif column == "environment":
            internal["_has_top_level_environment_filter"] = True
        elif column == "type":
            internal["_has_top_level_type_filter"] = True
        elif column == "metadata" and item.get("key"):
            key = str(item["key"])
            internal[key] = value
            if key == "evaluator_set_id":
                internal["_evaluator_set_id_operator"] = item.get("operator")
    return internal


def normalize_score_categories(value: Any) -> list[str] | None:
    if value is None:
        return None
    categories: list[str] = []
    for category in value:
        if isinstance(category, str):
            categories.append(category)
        elif isinstance(category, dict):
            categories.append(str(category.get("label") or category.get("value")))
        else:
            categories.append(
                str(getattr(category, "label", getattr(category, "value", category)))
            )
    return categories


def score_config_is_compatible(
    existing: dict[str, Any],
    expected: dict[str, Any],
) -> bool:
    compared_fields = ["name", "data_type", "min_value", "max_value", "categories"]
    return all(existing.get(field) == expected.get(field) for field in compared_fields)


def _copy_alias(raw: dict[str, Any], source: str, target: str) -> None:
    if source in raw and target not in raw:
        raw[target] = raw[source]
