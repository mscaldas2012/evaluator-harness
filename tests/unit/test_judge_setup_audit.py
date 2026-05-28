from __future__ import annotations

from evaluator_harness.config import load_project_config
from evaluator_harness.evaluator_bindings import EvaluatorBindingStore
from evaluator_harness.langfuse_client import LangfuseClient, ScoreConfigSyncResult
from evaluator_harness.langfuse_evaluator_setup import (
    EvaluatorOperation,
    audit_judge_evaluator_setup,
)


def test_audit_reports_missing_binding_for_user_owned_remote() -> None:
    config = load_project_config("tests/fixtures/projects/valid_rewrite_quality.yaml")
    client = LangfuseClient()
    client.evaluators["eval-1"] = {
        "id": "eval-1",
        "display_name": "EH_rewrite-quality_v1_judge_clarity_v1_custom_observation",
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
