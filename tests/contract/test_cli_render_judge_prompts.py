from __future__ import annotations

from typer.testing import CliRunner

from evaluator_harness.cli import app


def test_render_judge_prompts_outputs_langfuse_setup_contract() -> None:
    result = CliRunner().invoke(
        app,
        ["render-judge-prompts", "--project", "configs/projects/rewrite_quality.yaml"],
    )

    assert result.exit_code == 0
    assert "evaluator: clarity/v1" in result.stdout
    assert "target: observation role=model_output" in result.stdout
    assert "score: eh_rewrite_quality_clarity" in result.stdout
    assert "llm_judge: EVAL" in result.stdout
    assert "human_annotation: ANNOTATION" in result.stdout
    assert "project: rewrite-quality" in result.stdout
    assert "observation_role: model_output" in result.stdout
