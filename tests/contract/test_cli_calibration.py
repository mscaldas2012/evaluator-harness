from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from typer.testing import CliRunner

import evaluator_harness.cli as cli
from evaluator_harness.cli import app
from evaluator_harness.errors import ConfigError


@dataclass(frozen=True)
class FakeCalibrationResult:
    output_path: Path = Path("reports/rewrite-quality/calibration/candidate-1.json")
    row_count: int = 2
    paired_count: int = 1
    pending_count: int = 1
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class FakeCalibrationSummaryResult:
    output_path: Path = Path(
        "reports/rewrite-quality/calibration/candidate-1-summary.json"
    )
    summary_count: int = 1
    paired_count: int = 2
    pending_count: int = 0
    warnings: tuple[str, ...] = ()


def test_calibration_capture_cli_success_output(monkeypatch) -> None:
    captured_progress = []

    class FakeRunner:
        def __init__(self, *, progress=None):
            captured_progress.append(progress)

        def calibration_capture(self, project, run_id):
            assert run_id == "candidate-1"
            return FakeCalibrationResult()

    monkeypatch.setattr(cli, "ExperimentRunner", FakeRunner)

    result = CliRunner().invoke(
        app,
        [
            "calibration-capture",
            "--project",
            "configs/projects/rewrite_quality.yaml",
            "--run",
            "candidate-1",
        ],
    )

    assert result.exit_code == 0
    assert captured_progress
    assert "calibration:" in result.stdout
    assert "rows: 2" in result.stdout
    assert "paired: 1" in result.stdout
    assert "pending: 1" in result.stdout


def test_calibration_capture_cli_failure(monkeypatch) -> None:
    class FakeRunner:
        def calibration_capture(self, *_args, **_kwargs):
            raise ConfigError("run not found")

    monkeypatch.setattr(cli, "ExperimentRunner", FakeRunner)

    result = CliRunner().invoke(
        app,
        [
            "calibration-capture",
            "--project",
            "configs/projects/rewrite_quality.yaml",
            "--run",
            "candidate-1",
        ],
    )

    assert result.exit_code == 1
    assert "run not found" in result.stdout


def test_calibration_summary_cli_success_output(monkeypatch) -> None:
    captured_progress = []

    class FakeRunner:
        def __init__(self, *, progress=None):
            captured_progress.append(progress)

        def calibration_summary(self, project, run_id):
            assert run_id == "candidate-1"
            return FakeCalibrationSummaryResult()

    monkeypatch.setattr(cli, "ExperimentRunner", FakeRunner)

    result = CliRunner().invoke(
        app,
        [
            "calibration-summary",
            "--project",
            "configs/projects/rewrite_quality.yaml",
            "--run",
            "candidate-1",
        ],
    )

    assert result.exit_code == 0
    assert captured_progress
    assert "calibration-summary:" in result.stdout
    assert "summaries: 1" in result.stdout
    assert "paired: 2" in result.stdout
    assert "pending: 0" in result.stdout


def test_calibration_summary_cli_failure(monkeypatch) -> None:
    class FakeRunner:
        def calibration_summary(self, *_args, **_kwargs):
            raise ConfigError("snapshot not found")

    monkeypatch.setattr(cli, "ExperimentRunner", FakeRunner)

    result = CliRunner().invoke(
        app,
        [
            "calibration-summary",
            "--project",
            "configs/projects/rewrite_quality.yaml",
            "--run",
            "candidate-1",
        ],
    )

    assert result.exit_code == 1
    assert "snapshot not found" in result.stdout
