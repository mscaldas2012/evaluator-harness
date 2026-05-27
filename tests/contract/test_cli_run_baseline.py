from __future__ import annotations

from typer.testing import CliRunner

from evaluator_harness.cli import app


def test_sync_score_configs_cli_success_output() -> None:
    result = CliRunner().invoke(
        app,
        ["sync-score-configs", "--project", "configs/projects/rewrite_quality.yaml"],
    )

    assert result.exit_code == 0
    assert "score-config: eh_rewrite_quality_clarity" in result.stdout


def test_run_baseline_cli_success_with_fake_provider() -> None:
    result = CliRunner().invoke(
        app,
        ["run", "--project", "configs/projects/rewrite_quality.yaml", "--mode", "baseline"],
    )

    assert result.exit_code == 0
    assert "run:" in result.stdout
    assert "baseline:" in result.stdout


def test_run_baseline_cli_rejects_unsupported_mode() -> None:
    result = CliRunner().invoke(
        app,
        ["run", "--project", "configs/projects/rewrite_quality.yaml", "--mode", "candidate"],
    )

    assert result.exit_code == 1
    assert "candidate" in result.stdout
