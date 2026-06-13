from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from typer.testing import CliRunner

import evaluator_harness.cli as cli
from evaluator_harness.cli import app
from evaluator_harness.errors import ConfigError


@dataclass(frozen=True)
class FakeReportResult:
    format: str
    output_path: Path
    report_count: int = 2
    row_count: int = 4
    score_observation_count: int = 6
    warnings: tuple[str, ...] = field(default_factory=tuple)


def test_comparison_report_cli_generates_html(monkeypatch) -> None:
    def fake_create_comparison_reports(**kwargs):
        assert kwargs["baseline_run_id"] == "baseline-1"
        assert kwargs["reports_dir"] == Path("reports")
        assert kwargs["formats"] == "html"
        assert kwargs["output_path"] == Path("reports/out.html")
        assert kwargs["overwrite"] is True
        return [FakeReportResult("html", Path("reports/out.html"))]

    monkeypatch.setattr(cli, "create_comparison_reports", fake_create_comparison_reports)

    result = CliRunner().invoke(
        app,
        [
            "comparison-report",
            "--baseline",
            "baseline-1",
            "--format",
            "html",
            "--reports-dir",
            "reports",
            "--output",
            "reports/out.html",
            "--overwrite",
        ],
    )

    assert result.exit_code == 0
    assert "html-report: reports\\out.html" in result.stdout
    assert "baseline: baseline-1" in result.stdout
    assert "reports: 2" in result.stdout
    assert "rows: 4" in result.stdout
    assert "score-observations: 6" in result.stdout


def test_comparison_report_cli_generates_both(monkeypatch) -> None:
    def fake_create_comparison_reports(**kwargs):
        assert kwargs["formats"] == "both"
        assert kwargs["output_dir"] == Path("reports/out")
        return [
            FakeReportResult("excel", Path("reports/out/baseline-1-comparison.xlsx")),
            FakeReportResult("html", Path("reports/out/baseline-1-comparison.html")),
        ]

    monkeypatch.setattr(cli, "create_comparison_reports", fake_create_comparison_reports)

    result = CliRunner().invoke(
        app,
        [
            "comparison-report",
            "--baseline",
            "baseline-1",
            "--format",
            "both",
            "--reports-dir",
            "reports",
            "--output-dir",
            "reports/out",
        ],
    )

    assert result.exit_code == 0
    assert "excel-report: reports\\out\\baseline-1-comparison.xlsx" in result.stdout
    assert "html-report: reports\\out\\baseline-1-comparison.html" in result.stdout


def test_comparison_report_cli_surfaces_unsupported_format(monkeypatch) -> None:
    def fake_create_comparison_reports(**_kwargs):
        raise ConfigError("Unsupported report format 'pdf'. Supported formats: excel, html, both.")

    monkeypatch.setattr(cli, "create_comparison_reports", fake_create_comparison_reports)

    result = CliRunner().invoke(
        app,
        ["comparison-report", "--baseline", "baseline-1", "--format", "pdf"],
    )

    assert result.exit_code == 1
    assert "Supported formats: excel, html, both" in result.stdout
