from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from typer.testing import CliRunner

import evaluator_harness.cli as cli
from evaluator_harness.cli import app
from evaluator_harness.errors import ConfigError
from tests.contract.test_cli_run_candidate import FakeRunResult


@dataclass(frozen=True)
class FakeExportResult:
    output_path: Path = Path("reports/rewrite-quality/baseline-123.csv")
    row_count: int = 2


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
    assert "model-output-targeting: aligned" in result.stdout


def test_run_baseline_cli_can_skip_automatic_human_review(monkeypatch) -> None:
    class FakeRunner:
        def run(self, project, mode, **kwargs):
            assert mode == "baseline"
            assert kwargs["select_human_review"] is False
            return FakeRunResult(run_id="baseline-123", run_type="baseline")

        def export(self, project, run_id, fmt, **_kwargs):
            return FakeExportResult()

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


def test_run_baseline_cli_can_skip_sync(monkeypatch) -> None:
    class FakeRunner:
        def run(self, project, mode, **kwargs):
            assert mode == "baseline"
            assert kwargs["skip_sync"] is True
            return FakeRunResult(run_id="baseline-123", run_type="baseline")

        def export(self, project, run_id, fmt, **_kwargs):
            return FakeExportResult()

    monkeypatch.setattr(cli, "ExperimentRunner", FakeRunner)

    result = CliRunner().invoke(
        app,
        [
            "run",
            "--project",
            "configs/projects/rewrite_quality.yaml",
            "--mode",
            "baseline",
            "--skip-sync",
        ],
    )

    assert result.exit_code == 0
    assert "sync: skipped" in result.stdout


def test_run_baseline_cli_exports_report_by_default(monkeypatch) -> None:
    calls: list[tuple[Path, str, str, int | None]] = []

    class FakeRunner:
        def run(self, project, mode, **kwargs):
            assert mode == "baseline"
            return FakeRunResult(
                run_id="baseline-123",
                run_type="baseline",
                completed_count=10,
                failed_count=2,
            )

        def export(self, project, run_id, fmt, **kwargs):
            calls.append((project, run_id, fmt, kwargs.get("expected_count")))
            return FakeExportResult()

    monkeypatch.setattr(cli, "ExperimentRunner", FakeRunner)

    result = CliRunner().invoke(
        app,
        ["run", "--project", "configs/projects/rewrite_quality.yaml", "--mode", "baseline"],
    )

    assert result.exit_code == 0
    assert calls == [
        (Path("configs/projects/rewrite_quality.yaml"), "baseline-123", "csv", 12)
    ]
    assert "report: reports\\rewrite-quality\\baseline-123.csv" in result.stdout
    assert "report-rows: 2" in result.stdout


def test_run_baseline_cli_no_report_skips_export(monkeypatch) -> None:
    class FakeRunner:
        def run(self, project, mode, **kwargs):
            assert mode == "baseline"
            return FakeRunResult(run_id="baseline-123", run_type="baseline")

        def export(self, *_args, **_kwargs):
            raise AssertionError("export should not be called")

    monkeypatch.setattr(cli, "ExperimentRunner", FakeRunner)

    result = CliRunner().invoke(
        app,
        [
            "run",
            "--project",
            "configs/projects/rewrite_quality.yaml",
            "--mode",
            "baseline",
            "--no-report",
        ],
    )

    assert result.exit_code == 0
    assert "report:" not in result.stdout


def test_run_baseline_cli_rejects_unsupported_mode(monkeypatch) -> None:
    monkeypatch.setenv("EVALUATOR_HARNESS_LIVE", "0")

    result = CliRunner().invoke(
        app,
        ["run", "--project", "configs/projects/rewrite_quality.yaml", "--mode", "candidate"],
    )

    assert result.exit_code == 1
    assert "candidate" in result.stdout


def test_run_cli_surfaces_baseline_lookup_failure(monkeypatch) -> None:
    class FakeRunner:
        def mixed_variant_axes(self, *_args, **_kwargs):
            return []

        def run(self, project, mode, **kwargs):
            raise ConfigError(
                "No baseline reference found for latest-compatible. "
                "Langfuse baseline lookup failed."
            )

    monkeypatch.setattr(cli, "ExperimentRunner", FakeRunner)

    result = CliRunner().invoke(
        app,
        [
            "run",
            "--project",
            "configs/projects/rewrite_quality.yaml",
            "--mode",
            "candidate",
            "--candidate",
            "dry-run-candidate",
            "--baseline",
            "latest-compatible",
            "--no-report",
        ],
    )

    assert result.exit_code == 1
    normalized = result.stdout.replace("\n", " ")
    assert "Langfuse baseline lookup" in normalized
    assert "failed." in normalized
