from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from typer.testing import CliRunner

import evaluator_harness.cli as cli
from evaluator_harness.cli import app
from evaluator_harness.errors import ConfigError


@dataclass(frozen=True)
class FakeExcelReportResult:
    output_path: Path = Path("reports/baseline-1-comparison.xlsx")
    report_count: int = 2
    row_count: int = 4
    score_observation_count: int = 6
    warnings: tuple[str, ...] = field(default_factory=tuple)


def test_excel_report_cli_success_output(monkeypatch) -> None:
    def fake_create_excel_report(*, baseline_run_id, reports_dir, output_path, overwrite):
        assert baseline_run_id == "baseline-1"
        assert reports_dir == Path("reports")
        assert output_path == Path("reports/out.xlsx")
        assert overwrite is True
        return FakeExcelReportResult(output_path=output_path)

    monkeypatch.setattr(cli, "create_excel_report", fake_create_excel_report)

    result = CliRunner().invoke(
        app,
        [
            "excel-report",
            "--baseline",
            "baseline-1",
            "--reports-dir",
            "reports",
            "--output",
            "reports/out.xlsx",
            "--overwrite",
        ],
    )

    assert result.exit_code == 0
    assert "excel-report: reports\\out.xlsx" in result.stdout
    assert "baseline: baseline-1" in result.stdout
    assert "reports: 2" in result.stdout
    assert "rows: 4" in result.stdout
    assert "score-observations: 6" in result.stdout


def test_excel_report_cli_surfaces_warnings(monkeypatch) -> None:
    def fake_create_excel_report(**_kwargs):
        return FakeExcelReportResult(warnings=("No numeric score columns found.",))

    monkeypatch.setattr(cli, "create_excel_report", fake_create_excel_report)

    result = CliRunner().invoke(app, ["excel-report", "--baseline", "baseline-1"])

    assert result.exit_code == 0
    assert "warning: No numeric score columns found." in result.stdout


def test_excel_report_cli_missing_baseline_is_error(monkeypatch) -> None:
    def fake_create_excel_report(**_kwargs):
        raise ConfigError("No CSV report contains baseline run 'baseline-missing'.")

    monkeypatch.setattr(cli, "create_excel_report", fake_create_excel_report)

    result = CliRunner().invoke(app, ["excel-report", "--baseline", "baseline-missing"])

    assert result.exit_code == 1
    assert "baseline-missing" in result.stdout


def test_excel_report_cli_existing_output_without_overwrite_is_error(monkeypatch) -> None:
    def fake_create_excel_report(**_kwargs):
        raise ConfigError("Workbook already exists. Pass --overwrite to replace it.")

    monkeypatch.setattr(cli, "create_excel_report", fake_create_excel_report)

    result = CliRunner().invoke(app, ["excel-report", "--baseline", "baseline-1"])

    assert result.exit_code == 1
    assert "--overwrite" in result.stdout


def test_excel_report_cli_malformed_csv_is_error(monkeypatch) -> None:
    def fake_create_excel_report(**_kwargs):
        raise ConfigError("Malformed CSV report bad.csv: missing run_id column.")

    monkeypatch.setattr(cli, "create_excel_report", fake_create_excel_report)

    result = CliRunner().invoke(app, ["excel-report", "--baseline", "baseline-1"])

    assert result.exit_code == 1
    assert "bad.csv" in result.stdout
