from __future__ import annotations

from typer.testing import CliRunner

from evaluator_harness.cli import app


def test_validate_cli_accepts_config_ref_project() -> None:
    result = CliRunner().invoke(
        app,
        [
            "validate",
            "--project",
            "tests/fixtures/projects/config_refs/valid_shared_project.yaml",
        ],
    )

    assert result.exit_code == 0
    assert "config-ref-project/v1" in result.stdout
    assert "dataset: local_csv" in result.stdout
    assert "baseline: dry-run-baseline" in result.stdout
    assert "candidates: dry-run-candidate" in result.stdout
    assert "evaluators: clarity/v1" in result.stdout
    assert "judge-default: gpt-4.1" in result.stdout


def test_validate_cli_reports_config_ref_conflict() -> None:
    result = CliRunner().invoke(
        app,
        [
            "validate",
            "--project",
            "tests/fixtures/projects/config_refs/conflicting_project.yaml",
        ],
    )

    assert result.exit_code == 1
    assert "config_refs.evaluation" in result.stdout
    assert "conflict" in result.stdout
    assert "human_review" in result.stdout
