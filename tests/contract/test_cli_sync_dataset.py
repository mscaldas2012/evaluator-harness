from __future__ import annotations

from typer.testing import CliRunner

from evaluator_harness.cli import app


def test_sync_dataset_cli_success_output(monkeypatch) -> None:
    monkeypatch.setenv("EVALUATOR_HARNESS_LIVE", "0")

    result = CliRunner().invoke(
        app,
        ["sync-dataset", "--project", "configs/projects/rewrite_quality.yaml"],
    )

    assert result.exit_code == 0
    assert "dataset: rewrite-quality/v1" in result.stdout
    assert "version:" in result.stdout
    assert "items: 2" in result.stdout


def test_sync_dataset_cli_dry_run_output(monkeypatch) -> None:
    monkeypatch.setenv("EVALUATOR_HARNESS_LIVE", "0")

    result = CliRunner().invoke(
        app,
        ["sync-dataset", "--project", "configs/projects/rewrite_quality.yaml", "--dry-run"],
    )

    assert result.exit_code == 0
    assert "dataset: rewrite-quality/v1" in result.stdout
    assert "items: 2" in result.stdout
    assert "status: planned" in result.stdout


def test_sync_dataset_cli_failure_output(monkeypatch) -> None:
    monkeypatch.setenv("EVALUATOR_HARNESS_LIVE", "0")

    result = CliRunner().invoke(
        app,
        ["sync-dataset", "--project", "tests/fixtures/projects/invalid_missing_dataset.yaml"],
    )

    assert result.exit_code == 1
    assert "dataset" in result.stdout
