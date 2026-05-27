from __future__ import annotations

from typer.testing import CliRunner

from evaluator_harness.cli import app


def test_validate_cli_success_output() -> None:
    result = CliRunner().invoke(
        app,
        ["validate", "--project", "configs/projects/rewrite_quality.yaml"],
    )

    assert result.exit_code == 0
    assert "rewrite-quality/v1" in result.stdout
    assert "dataset: local_csv" in result.stdout
    assert "baseline: gpt5.2-dgw-default" in result.stdout
    assert "candidates: llama3-local" in result.stdout
    assert "evaluators: clarity/v1" in result.stdout
    assert "evaluator-targets: clarity=observation/model_output" in result.stdout
    assert "score-targets: clarity=eh_rewrite_quality_clarity" in result.stdout


def test_validate_cli_failure_output() -> None:
    result = CliRunner().invoke(
        app,
        ["validate", "--project", "tests/fixtures/projects/invalid_missing_dataset.yaml"],
    )

    assert result.exit_code == 1
    assert "dataset" in result.stdout
