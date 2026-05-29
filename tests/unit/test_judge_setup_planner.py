from __future__ import annotations

from evaluator_harness.config import load_project_config
from evaluator_harness.evaluator_bindings import EvaluatorBindingStore
from evaluator_harness.langfuse_client import LangfuseClient, ScoreConfigSyncResult
from evaluator_harness.langfuse_evaluator_setup import (
    BackfillStatus,
    EvaluatorOperation,
    safe_update_changes,
    plan_judge_evaluator_setup,
)


def _score_result() -> ScoreConfigSyncResult:
    return ScoreConfigSyncResult(
        evaluator_name="clarity",
        name="eh_rewrite_quality_clarity",
        score_config_id="score-config-1",
        status="reused",
        ownership="managed_by_harness",
    )


def test_planner_creates_missing_managed_evaluator() -> None:
    config = load_project_config("tests/fixtures/projects/valid_rewrite_quality.yaml")

    result = plan_judge_evaluator_setup(
        config,
        LangfuseClient(),
        [_score_result()],
        bindings=EvaluatorBindingStore(),
    )

    assert result.evaluators[0].operation == EvaluatorOperation.CREATE
    assert result.evaluators[0].activation_state == "active-on-apply"
    assert result.evaluators[0].binding_status == "will-create"


def test_safe_update_changes_only_operational_fields() -> None:
    changes = safe_update_changes(
        expected={
            "filters": {"project": "rewrite-quality"},
            "sampling_percent": 100,
            "variables": {"input": "observation.input"},
            "prompt_version": "v1",
        },
        remote={
            "filters": {"project": "rewrite-quality", "environment": "local"},
            "sampling_percent": 10,
            "variables": {"input": "observation.input"},
            "prompt_version": "v1",
        },
    )

    assert changes == {"sampling_percent": 100}


def test_safe_update_filters_ignore_non_rest_round_trip_fields() -> None:
    changes = safe_update_changes(
        expected={
            "filters": {
                "target": "observation",
                "observation_role": "model_output",
                "project": "rewrite-quality",
                "project_version": "v1",
                "evaluator_set_id": "clarity:v1",
                "environment": "local",
                "run_types": ["baseline", "candidate"],
            }
        },
        remote={
            "filters": {
                "observation_role": "model_output",
                "project": "rewrite-quality",
                "project_version": "v1",
                "evaluator_set_id": "clarity:v1",
                "environment": "local",
            }
        },
    )

    assert changes == {}


def test_safe_update_filters_replace_existing_provider_specific_top_level_filters() -> None:
    changes = safe_update_changes(
        expected={
            "filters": {
                "observation_role": "model_output",
                "observation_name": "OpenAI-generation",
                "project": "rewrite-quality",
                "project_version": "v1",
                "evaluator_set_id": "clarity:v1",
                "environment": "local",
            }
        },
        remote={
            "filters": {
                "observation_role": "model_output",
                "observation_name": "OpenAI-generation",
                "project": "rewrite-quality",
                "project_version": "v1",
                "evaluator_set_id": "clarity:v1",
                "_has_top_level_environment_filter": True,
                "_has_top_level_name_filter": True,
                "_has_top_level_type_filter": True,
            }
        },
    )

    assert changes == {
        "filters": {
            "observation_role": "model_output",
            "observation_name": "OpenAI-generation",
            "project": "rewrite-quality",
            "project_version": "v1",
            "evaluator_set_id": "clarity:v1",
            "environment": "local",
        }
    }


def test_safe_update_filters_replace_exact_evaluator_set_id_operator() -> None:
    changes = safe_update_changes(
        expected={
            "filters": {
                "observation_role": "model_output",
                "project": "dfe",
                "project_version": "v1",
                "evaluator_set_id": "jargon_minimized:v1",
            }
        },
        remote={
            "filters": {
                "observation_role": "model_output",
                "project": "dfe",
                "project_version": "v1",
                "evaluator_set_id": "jargon_minimized:v1",
                "_evaluator_set_id_operator": "=",
            }
        },
    )

    assert changes == {
        "filters": {
            "observation_role": "model_output",
            "project": "dfe",
            "project_version": "v1",
            "evaluator_set_id": "jargon_minimized:v1",
        }
    }


def test_backfill_request_blocks_when_unsupported() -> None:
    config = load_project_config("tests/fixtures/projects/invalid_judge_setup_unsafe_backfill.yaml")

    result = plan_judge_evaluator_setup(
        config,
        LangfuseClient(),
        [_score_result()],
        bindings=EvaluatorBindingStore(),
    )

    assert result.evaluators[0].operation == EvaluatorOperation.BLOCK
    assert result.evaluators[0].backfill_status == BackfillStatus.UNSUPPORTED


def test_broad_filter_blocks_setup() -> None:
    config = load_project_config("tests/fixtures/projects/invalid_evaluator_broad_filter.yaml")

    result = plan_judge_evaluator_setup(
        config,
        LangfuseClient(),
        [_score_result()],
        bindings=EvaluatorBindingStore(),
        validate_config=False,
    )

    assert result.evaluators[0].operation == EvaluatorOperation.BLOCK
    assert "filter" in str(result.evaluators[0].remediation).lower()
