from __future__ import annotations

from enum import Enum
from types import SimpleNamespace

from evaluator_harness.langfuse_mappers import (
    normalize_score_categories,
    object_to_evaluator_dict,
    object_to_prompt_dict,
    object_to_queue_dict,
    object_to_score_config_dict,
    object_to_score_dict,
    rest_evaluation_rule_payload,
    rest_evaluation_rule_update_payload,
    rest_filters_to_internal,
)


class DataType(Enum):
    NUMERIC = "NUMERIC"


def test_score_config_mapper_normalizes_camel_case_and_categories() -> None:
    result = object_to_score_config_dict(
        {
            "id": "score-1",
            "name": "quality",
            "dataType": DataType.NUMERIC,
            "minValue": 0,
            "maxValue": 1,
            "isArchived": False,
            "categories": [{"label": "good"}, {"value": "bad"}],
        }
    )

    assert result["data_type"] == "NUMERIC"
    assert result["min_value"] == 0
    assert result["max_value"] == 1
    assert result["archived"] is False
    assert result["categories"] == ["good", "bad"]


def test_score_category_normalization_handles_partial_and_scalar_values() -> None:
    assert normalize_score_categories(None) is None
    categories = ["good", 2, {"label": "great"}, {"value": 3}]

    assert normalize_score_categories(categories) == [
        "good",
        "2",
        "great",
        "3",
    ]


def test_evaluator_mapper_tolerates_missing_optional_rest_fields() -> None:
    result = object_to_evaluator_dict({"evaluationRuleId": "rule-1"})

    assert result["id"] == "rule-1"
    assert result.get("filters", {}) == {}
    assert result.get("variables", {}) == {}
    assert result.get("sampling_percent") is None


def test_rest_filter_normalization_ignores_unrecognized_filter_shapes() -> None:
    result = rest_filters_to_internal(
        [
            {"column": "metadata", "key": "project_name", "value": "rewrite"},
            {"column": "name", "value": ["generation"]},
            {"column": "metadata", "operator": "contains"},
            "not-a-filter",
        ]
    )

    assert result == {
        "project_name": "rewrite",
        "_has_top_level_name_filter": True,
    }


def test_score_mapper_normalizes_ids_and_enum_source() -> None:
    source = SimpleNamespace(value="API")

    result = object_to_score_dict(
        {
            "traceId": 123,
            "observationId": 456,
            "datasetRunId": 789,
            "stringValue": "pass",
            "source": source,
        }
    )

    assert result["trace_id"] == "123"
    assert result["observation_id"] == "456"
    assert result["dataset_run_id"] == "789"
    assert result["string_value"] == "pass"
    assert result["source"] == "API"


def test_prompt_and_queue_mappers_normalize_aliases_and_defaults() -> None:
    prompt = object_to_prompt_dict({"name": "judge", "version": "7"})
    queue = object_to_queue_dict({"id": "queue-1", "scoreConfigIds": ["score-1"]})

    assert prompt["version"] == 7
    assert prompt["labels"] == []
    assert prompt["tags"] == []
    assert queue["score_config_ids"] == ["score-1"]


def test_evaluator_mapper_round_trips_rest_mapping_and_filters() -> None:
    result = object_to_evaluator_dict(
        {
            "evaluationRuleId": "rule-1",
            "enabled": True,
            "sampling": 0.5,
            "scoreConfigId": "score-1",
            "mapping": [
                {"variable": "input", "source": "input"},
                {
                    "variable": "ground_truth",
                    "source": "metadata",
                    "jsonPath": "$.ground_truth",
                },
            ],
            "filter": [
                {
                    "column": "metadata",
                    "key": "evaluator_set_id",
                    "operator": "contains",
                    "value": "set-1",
                }
            ],
        }
    )

    assert result["id"] == "rule-1"
    assert result["active"] is True
    assert result["sampling_percent"] == 50
    assert result["score_config_id"] == "score-1"
    assert result["variables"] == {
        "input": "observation.input",
        "ground_truth": "trace.metadata.ground_truth",
    }
    assert result["filters"]["evaluator_set_id"] == "set-1"


def test_rest_evaluation_rule_payloads_use_expected_langfuse_shape() -> None:
    payload = rest_evaluation_rule_payload(
        {
            "name": "rule",
            "target": "observation",
            "sampling_percent": 25,
            "score_config_id": "score-1",
            "variables": {"output": "observation.output"},
            "filters": {"evaluator_set_id": "set-1"},
        },
        evaluator_ref={"name": "template", "scope": "project"},
    )
    update = rest_evaluation_rule_update_payload(
        {
            "display_name": "renamed",
            "sampling_percent": 50,
            "variables": {"input": "observation.input"},
        }
    )

    assert payload["sampling"] == 0.25
    assert payload["scoreConfigId"] == "score-1"
    assert payload["mapping"] == [{"variable": "output", "source": "output"}]
    assert payload["filter"][0]["operator"] == "contains"
    assert update["name"] == "renamed"
    assert update["sampling"] == 0.5
    assert update["mapping"] == [{"variable": "input", "source": "input"}]
