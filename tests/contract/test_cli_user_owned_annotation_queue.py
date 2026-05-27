from __future__ import annotations

from typer.testing import CliRunner

from evaluator_harness.cli import app


def test_validate_reports_user_owned_queue_without_id() -> None:
    result = CliRunner().invoke(
        app,
        [
            "validate",
            "--project",
            "tests/fixtures/projects/invalid_user_owned_annotation_queue.yaml",
        ],
    )

    assert result.exit_code == 1
    assert "annotation_queue_id" in result.stdout
