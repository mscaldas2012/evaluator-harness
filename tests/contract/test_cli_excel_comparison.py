from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from typer.testing import CliRunner

import evaluator_harness.cli as cli
from evaluator_harness.cli import app
from evaluator_harness.errors import ConfigError


@dataclass(frozen=True)
class FakeExcelReportResult:
    format: str = "excel"
    output_path: Path = Path("reports/baseline-1-comparison.xlsx")
    report_count: int = 2
    row_count: int = 4
    score_observation_count: int = 6
    warnings: tuple[str, ...] = field(default_factory=tuple)


def test_excel_report_cli_success_output(monkeypatch) -> None:
    def fake_create_comparison_reports(**kwargs):
        baseline_run_id = kwargs["baseline_run_id"]
        reports_dir = kwargs["reports_dir"]
        output_path = kwargs["output_path"]
        overwrite = kwargs["overwrite"]
        assert baseline_run_id == "baseline-1"
        assert reports_dir == Path("reports")
        assert output_path == Path("reports/out.xlsx")
        assert overwrite is True
        assert kwargs["formats"] == "excel"
        return [FakeExcelReportResult(output_path=output_path)]

    monkeypatch.setattr(cli, "create_comparison_reports", fake_create_comparison_reports)

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


def test_excel_report_cli_delegates_to_comparison_reports(monkeypatch) -> None:
    calls: list[dict[str, object]] = []

    def fake_create_comparison_reports(**kwargs):
        calls.append(kwargs)
        return [
            type(
                "FakeExcel",
                (),
                {
                    "format": "excel",
                    "output_path": Path("reports/out.xlsx"),
                    "report_count": 2,
                    "row_count": 4,
                    "score_observation_count": 6,
                    "warnings": (),
                },
            )()
        ]

    monkeypatch.setattr(
        cli,
        "create_comparison_reports",
        fake_create_comparison_reports,
        raising=False,
    )

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
        ],
    )

    assert result.exit_code == 0
    assert calls[0]["formats"] == "excel"
    assert "excel-report: reports\\out.xlsx" in result.stdout


def test_excel_report_cli_uses_project_reports_dir_by_default(monkeypatch) -> None:
    def fake_load_project_config(project_path):
        assert project_path == Path("configs/projects/dfe-general-public.yaml")

        class FakeProject:
            name = "dfe-general-public"

        class FakeConfig:
            project = FakeProject()

        return FakeConfig()

    def fake_create_comparison_reports(**kwargs):
        baseline_run_id = kwargs["baseline_run_id"]
        reports_dir = kwargs["reports_dir"]
        output_path = kwargs["output_path"]
        overwrite = kwargs["overwrite"]
        assert baseline_run_id == "baseline-1"
        assert reports_dir == Path("reports/dfe-general-public")
        assert output_path is None
        assert overwrite is False
        assert kwargs["formats"] == "excel"
        return [FakeExcelReportResult()]

    monkeypatch.setattr(cli, "load_project_config", fake_load_project_config)
    monkeypatch.setattr(cli, "create_comparison_reports", fake_create_comparison_reports)

    result = CliRunner().invoke(
        app,
        [
            "excel-report",
            "--project",
            "dfe-general-public",
            "--baseline",
            "baseline-1",
        ],
    )

    assert result.exit_code == 0


def test_excel_report_cli_keeps_explicit_reports_dir_with_project(monkeypatch) -> None:
    def fake_load_project_config(_project_path):
        raise AssertionError("project config is not needed with explicit --reports-dir")

    def fake_create_comparison_reports(**kwargs):
        baseline_run_id = kwargs["baseline_run_id"]
        reports_dir = kwargs["reports_dir"]
        assert baseline_run_id == "baseline-1"
        assert reports_dir == Path("custom-reports")
        assert kwargs["formats"] == "excel"
        return [FakeExcelReportResult()]

    monkeypatch.setattr(cli, "load_project_config", fake_load_project_config, raising=False)
    monkeypatch.setattr(cli, "create_comparison_reports", fake_create_comparison_reports)

    result = CliRunner().invoke(
        app,
        [
            "excel-report",
            "--project",
            "dfe-general-public",
            "--baseline",
            "baseline-1",
            "--reports-dir",
            "custom-reports",
        ],
    )

    assert result.exit_code == 0


def test_excel_report_cli_surfaces_warnings(monkeypatch) -> None:
    def fake_create_comparison_reports(**_kwargs):
        return [FakeExcelReportResult(warnings=("No numeric score columns found.",))]

    monkeypatch.setattr(cli, "create_comparison_reports", fake_create_comparison_reports)

    result = CliRunner().invoke(app, ["excel-report", "--baseline", "baseline-1"])

    assert result.exit_code == 0
    assert "warning: No numeric score columns found." in result.stdout


def test_excel_report_cli_missing_baseline_is_error(monkeypatch) -> None:
    def fake_create_comparison_reports(**_kwargs):
        raise ConfigError("No CSV report contains baseline run 'baseline-missing'.")

    monkeypatch.setattr(cli, "create_comparison_reports", fake_create_comparison_reports)

    result = CliRunner().invoke(app, ["excel-report", "--baseline", "baseline-missing"])

    assert result.exit_code == 1
    assert "baseline-missing" in result.stdout


def test_excel_report_cli_existing_output_without_overwrite_is_error(monkeypatch) -> None:
    def fake_create_comparison_reports(**_kwargs):
        raise ConfigError("Workbook already exists. Pass --overwrite to replace it.")

    monkeypatch.setattr(cli, "create_comparison_reports", fake_create_comparison_reports)

    result = CliRunner().invoke(app, ["excel-report", "--baseline", "baseline-1"])

    assert result.exit_code == 1
    assert "--overwrite" in result.stdout


def test_excel_report_cli_malformed_csv_is_error(monkeypatch) -> None:
    def fake_create_comparison_reports(**_kwargs):
        raise ConfigError("Malformed CSV report bad.csv: missing run_id column.")

    monkeypatch.setattr(cli, "create_comparison_reports", fake_create_comparison_reports)

    result = CliRunner().invoke(app, ["excel-report", "--baseline", "baseline-1"])

    assert result.exit_code == 1
    assert "bad.csv" in result.stdout
