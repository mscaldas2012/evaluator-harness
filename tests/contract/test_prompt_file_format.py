from __future__ import annotations

from typer.testing import CliRunner

from evaluator_harness.cli import app


def test_validate_accepts_role_based_prompt_project() -> None:
    result = CliRunner().invoke(
        app,
        [
            "validate",
            "--project",
            "tests/fixtures/projects/valid_role_prompt_project.yaml",
        ],
    )

    assert result.exit_code == 0
    assert "role-prompt-project/v1" in result.stdout


def test_validate_rejects_missing_dataset_column() -> None:
    result = CliRunner().invoke(
        app,
        [
            "validate",
            "--project",
            "tests/fixtures/projects/invalid_role_prompt_missing_column.yaml",
        ],
    )

    assert result.exit_code != 0
    assert "dataset.missing_field" in result.stdout


def test_validate_rejects_provider_that_cannot_send_role_messages() -> None:
    result = CliRunner().invoke(
        app,
        [
            "validate",
            "--project",
            "tests/fixtures/projects/invalid_role_prompt_ollama.yaml",
        ],
    )

    assert result.exit_code != 0
    assert "ollama" in result.stdout
    assert "role" in result.stdout
