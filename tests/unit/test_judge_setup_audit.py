from __future__ import annotations

from evaluator_harness.config import load_project_config
from evaluator_harness.evaluator_bindings import EvaluatorBindingRecord, EvaluatorBindingStore
from evaluator_harness.langfuse_default_gateway import DefaultLangfuseGateway, ScoreConfigSyncResult
from evaluator_harness.langfuse_evaluator_setup import (
    EvaluatorOperation,
    audit_judge_evaluator_setup,
)


def test_audit_reports_missing_binding_for_user_owned_remote() -> None:
    config = load_project_config("tests/fixtures/projects/valid_rewrite_quality.yaml")
    client = DefaultLangfuseGateway()
    client.evaluators["eval-1"] = {
        "id": "eval-1",
        "display_name": "eh_rewrite_quality_clarity",
        "active": True,
    }

    result = audit_judge_evaluator_setup(
        config,
        client,
        [
            ScoreConfigSyncResult(
                evaluator_name="clarity",
                name="eh_rewrite_quality_clarity",
                score_config_id="score-config-1",
                status="reused",
                ownership="managed_by_harness",
            )
        ],
        bindings=EvaluatorBindingStore(),
    )

    assert result.evaluators[0].operation == EvaluatorOperation.BLOCK
    assert "binding" in str(result.evaluators[0].remediation).lower()


def test_audit_reports_score_config_target_mismatch_for_bound_evaluator() -> None:
    config = load_project_config("tests/fixtures/projects/valid_rewrite_quality.yaml")
    client = DefaultLangfuseGateway()
    display_name = "EH_rewrite-quality_v1_judge_clarity_v1_custom_observation"
    client.evaluators["eval-1"] = {
        "id": "eval-1",
        "display_name": display_name,
        "active": True,
        "filters": {
            "project": "rewrite-quality",
            "project_version": "v1",
            "evaluator_set_id": "clarity:v1",
            "observation_role": "model_output",
        },
            "variables": {
                "input": "observation.input",
                "output": "observation.output",
                "ground_truth": "trace.metadata.ground_truth",
            },
        "sampling_percent": 100,
        "score_config_id": "score-config-remote",
    }
    bindings = EvaluatorBindingStore(
        bindings=[
            EvaluatorBindingRecord(
                project="rewrite-quality",
                project_version="v1",
                evaluator_name="clarity",
                evaluator_version="v1",
                source_type="custom",
                target="observation",
                langfuse_evaluator_id="eval-1",
                langfuse_display_name=display_name,
                score_config_id="score-config-remote",
                score_config_name="eh_rewrite_quality_clarity",
                judge_model="gpt-4.1",
                llm_connection="lf-connection-default",
                last_synced_at="2026-06-04T00:00:00+00:00",
            )
        ]
    )

    result = audit_judge_evaluator_setup(
        config,
        client,
        [
            ScoreConfigSyncResult(
                evaluator_name="clarity",
                name="eh_rewrite_quality_clarity",
                score_config_id="score-config-expected",
                status="reused",
                ownership="managed_by_harness",
            )
        ],
        bindings=bindings,
    )

    plan = result.evaluators[0]
    assert plan.operation == EvaluatorOperation.UPDATE
    assert plan.changes == {"score_config_id": "score-config-expected"}
    assert "score-config-expected" in str(plan.remediation)
    assert "score-config-remote" in str(plan.remediation)


def test_audit_reuses_binding_score_config_when_remote_omits_target() -> None:
    config = load_project_config("tests/fixtures/projects/valid_rewrite_quality.yaml")
    client = DefaultLangfuseGateway()
    display_name = "EH_rewrite-quality_v1_judge_clarity_v1_custom_observation"
    client.evaluators["eval-1"] = {
        "id": "eval-1",
        "display_name": display_name,
        "active": True,
        "filters": {
            "project": "rewrite-quality",
            "project_version": "v1",
            "evaluator_set_id": "clarity:v1",
            "observation_role": "model_output",
        },
        "variables": {
            "input": "observation.input",
            "output": "observation.output",
            "ground_truth": "trace.metadata.ground_truth",
        },
        "sampling_percent": 100,
    }
    bindings = EvaluatorBindingStore(
        bindings=[
            EvaluatorBindingRecord(
                project="rewrite-quality",
                project_version="v1",
                evaluator_name="clarity",
                evaluator_version="v1",
                source_type="custom",
                target="observation",
                langfuse_evaluator_id="eval-1",
                langfuse_display_name=display_name,
                score_config_id="score-config-expected",
                score_config_name="eh_rewrite_quality_clarity",
                judge_model="gpt-4.1",
                llm_connection="lf-connection-default",
                last_synced_at="2026-06-04T00:00:00+00:00",
            )
        ]
    )

    result = audit_judge_evaluator_setup(
        config,
        client,
        [
            ScoreConfigSyncResult(
                evaluator_name="clarity",
                name="eh_rewrite_quality_clarity",
                score_config_id="score-config-expected",
                status="reused",
                ownership="managed_by_harness",
            )
        ],
        bindings=bindings,
    )

    plan = result.evaluators[0]
    assert plan.operation == EvaluatorOperation.REUSE
    assert plan.changes == {}
