from __future__ import annotations

from typer.testing import CliRunner

import evaluator_harness.cli as cli
from evaluator_harness.cli import app
from tests.contract.test_cli_run_candidate import FakeRunResult


def test_sync_score_configs_cli_success_output(monkeypatch) -> None:
    monkeypatch.setenv("EVALUATOR_HARNESS_LIVE", "0")

    result = CliRunner().invoke(
        app,
        ["sync-score-configs", "--project", "configs/projects/rewrite_quality.yaml"],
    )

    assert result.exit_code == 0
    assert "score-config: eh_rewrite_quality_clarity" in result.stdout


def test_sync_score_configs_cli_dry_run_output(monkeypatch) -> None:
    monkeypatch.setenv("EVALUATOR_HARNESS_LIVE", "0")

    result = CliRunner().invoke(
        app,
        ["sync-score-configs", "--project", "configs/projects/rewrite_quality.yaml", "--dry-run"],
    )

    assert result.exit_code == 0
    assert "score-config: eh_rewrite_quality_clarity" in result.stdout
    assert "status: planned_create" in result.stdout


def test_run_baseline_cli_success_with_fake_provider(monkeypatch) -> None:
    monkeypatch.setenv("EVALUATOR_HARNESS_LIVE", "0")

    result = CliRunner().invoke(
        app,
        ["run", "--project", "configs/projects/rewrite_quality.yaml", "--mode", "baseline"],
    )

    assert result.exit_code == 0
    assert "run:" in result.stdout
    assert "baseline:" in result.stdout


def test_run_baseline_cli_can_skip_automatic_human_review(monkeypatch) -> None:
    class FakeRunner:
        def run(self, project, mode, **kwargs):
            assert mode == "baseline"
            assert kwargs["select_human_review"] is False
            return FakeRunResult(run_id="baseline-123", run_type="baseline")

    monkeypatch.setattr(cli, "ExperimentRunner", FakeRunner)

    result = CliRunner().invoke(
        app,
        [
            "run",
            "--project",
            "configs/projects/rewrite_quality.yaml",
            "--mode",
            "baseline",
            "--skip-human-review",
        ],
    )

    assert result.exit_code == 0
    assert "review: skipped" in result.stdout


def test_run_baseline_cli_rejects_unsupported_mode(monkeypatch) -> None:
    monkeypatch.setenv("EVALUATOR_HARNESS_LIVE", "0")

    result = CliRunner().invoke(
        app,
        ["run", "--project", "configs/projects/rewrite_quality.yaml", "--mode", "candidate"],
    )

    assert result.exit_code == 1
    assert "candidate" in result.stdout
