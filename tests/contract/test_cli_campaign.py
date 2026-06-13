from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

import evaluator_harness.cli as cli
from evaluator_harness.cli import app
from evaluator_harness.exports import ExportResult
from evaluator_harness.runner import (
    CampaignCandidateRun,
    CampaignCandidateSelection,
    CampaignRunResult,
    RunResult,
)


def test_campaign_cli_success_output(monkeypatch) -> None:
    class FakeRunner:
        def campaign(self, project, **kwargs):
            assert project == Path("tests/fixtures/projects/campaign_mode.yaml")
            assert kwargs["skip_sync"] is False
            assert kwargs["select_human_review"] is True
            assert kwargs["no_report"] is False
            assert kwargs["overwrite"] is False
            assert kwargs["report_format"] == "excel"
            kwargs["on_run_start"]("baseline", "baseline")
            kwargs["on_run_start"]("candidate", "included-candidate")
            excel_report = type(
                "FakeWorkbook",
                (),
                {
                    "format": "excel",
                    "output_path": Path("reports/campaign-mode/baseline-1-comparison.xlsx"),
                    "warnings": (),
                },
            )()
            return CampaignRunResult(
                baseline_run=RunResult("baseline-1", "baseline", 2, 0),
                candidate_runs=[
                    CampaignCandidateRun(
                        "included-candidate",
                        RunResult("candidate-1", "candidate", 2, 0),
                        ExportResult(Path("reports/campaign-mode/candidate-1.csv"), 2),
                        "completed",
                    )
                ],
                skipped_candidates=[
                    CampaignCandidateSelection(
                        "excluded-candidate",
                        False,
                        "exclude-from-campaign=true",
                    )
                ],
                csv_reports=[
                    ExportResult(Path("reports/campaign-mode/baseline-1.csv"), 2),
                    ExportResult(Path("reports/campaign-mode/candidate-1.csv"), 2),
                ],
                excel_report=excel_report,
                final_reports=[excel_report],
                warnings=[],
            )

    monkeypatch.setattr(cli, "ExperimentRunner", FakeRunner)

    result = CliRunner().invoke(
        app,
        ["campaign", "--project", "tests/fixtures/projects/campaign_mode.yaml"],
    )

    assert result.exit_code == 0
    assert "running: baseline baseline" in result.stdout
    assert "running: candidate included-candidate" in result.stdout
    assert "campaign: completed" in result.stdout
    assert "baseline: baseline-1" in result.stdout
    assert "candidate: included-candidate candidate-1" in result.stdout
    assert "skipped: excluded-candidate exclude-from-campaign=true" in result.stdout
    assert "report: reports\\campaign-mode\\baseline-1.csv" in result.stdout
    assert "excel-report: reports\\campaign-mode\\baseline-1-comparison.xlsx" in result.stdout


def test_campaign_cli_html_report_format_output(monkeypatch) -> None:
    class FakeRunner:
        def campaign(self, project, **kwargs):
            assert project == Path("tests/fixtures/projects/campaign_mode.yaml")
            assert kwargs["report_format"] == "html"
            return CampaignRunResult(
                baseline_run=RunResult("baseline-1", "baseline", 2, 0),
                candidate_runs=[],
                skipped_candidates=[],
                csv_reports=[],
                excel_report=None,
                final_reports=[
                    type(
                        "FakeHtml",
                        (),
                        {
                            "format": "html",
                            "output_path": Path("reports/campaign-mode/baseline-1-comparison.html"),
                            "warnings": (),
                        },
                    )()
                ],
                warnings=[],
            )

    monkeypatch.setattr(cli, "ExperimentRunner", FakeRunner)

    result = CliRunner().invoke(
        app,
        [
            "campaign",
            "--project",
            "tests/fixtures/projects/campaign_mode.yaml",
            "--report-format",
            "html",
        ],
    )

    assert result.exit_code == 0
    assert "html-report: reports\\campaign-mode\\baseline-1-comparison.html" in result.stdout
    assert "excel-report:" not in result.stdout


def test_campaign_cli_both_report_format_output(monkeypatch) -> None:
    class FakeRunner:
        def campaign(self, *_args, **kwargs):
            assert kwargs["report_format"] == "both"
            return CampaignRunResult(
                baseline_run=RunResult("baseline-1", "baseline", 2, 0),
                candidate_runs=[],
                skipped_candidates=[],
                csv_reports=[],
                excel_report=None,
                final_reports=[
                    type(
                        "FakeExcel",
                        (),
                        {
                            "format": "excel",
                            "output_path": Path("reports/campaign-mode/baseline-1-comparison.xlsx"),
                            "warnings": (),
                        },
                    )(),
                    type(
                        "FakeHtml",
                        (),
                        {
                            "format": "html",
                            "output_path": Path("reports/campaign-mode/baseline-1-comparison.html"),
                            "warnings": (),
                        },
                    )(),
                ],
                warnings=[],
            )

    monkeypatch.setattr(cli, "ExperimentRunner", FakeRunner)

    result = CliRunner().invoke(
        app,
        [
            "campaign",
            "--project",
            "tests/fixtures/projects/campaign_mode.yaml",
            "--report-format",
            "both",
        ],
    )

    assert result.exit_code == 0
    assert "excel-report: reports\\campaign-mode\\baseline-1-comparison.xlsx" in result.stdout
    assert "html-report: reports\\campaign-mode\\baseline-1-comparison.html" in result.stdout


def test_campaign_cli_rejects_unsupported_report_format(monkeypatch) -> None:
    class FakeRunner:
        def campaign(self, *_args, **_kwargs):
            raise AssertionError("campaign should not start")

    monkeypatch.setattr(cli, "ExperimentRunner", FakeRunner)

    result = CliRunner().invoke(
        app,
        [
            "campaign",
            "--project",
            "tests/fixtures/projects/campaign_mode.yaml",
            "--report-format",
            "pdf",
        ],
    )

    assert result.exit_code == 1
    assert "Supported formats: excel, html, both" in result.stdout


def test_campaign_cli_skipped_when_no_candidates_eligible(monkeypatch) -> None:
    class FakeRunner:
        def campaign(self, *_args, **_kwargs):
            return CampaignRunResult(
                baseline_run=None,
                candidate_runs=[],
                skipped_candidates=[],
                csv_reports=[],
                excel_report=None,
                final_reports=[],
                warnings=["no candidates eligible for campaign"],
            )

    monkeypatch.setattr(cli, "ExperimentRunner", FakeRunner)

    result = CliRunner().invoke(
        app,
        ["campaign", "--project", "tests/fixtures/projects/campaign_mode.yaml"],
    )

    assert result.exit_code == 0
    assert "campaign: skipped" in result.stdout
    assert "reason: no candidates eligible for campaign" in result.stdout


def test_campaign_cli_completed_with_failures_exits_nonzero(monkeypatch) -> None:
    class FakeRunner:
        def campaign(self, *_args, **_kwargs):
            return CampaignRunResult(
                baseline_run=RunResult("baseline-1", "baseline", 2, 0),
                candidate_runs=[
                    CampaignCandidateRun(
                        "included-candidate",
                        RunResult("candidate-1", "candidate", 2, 0),
                        ExportResult(Path("reports/campaign-mode/candidate-1.csv"), 2),
                        "completed",
                    ),
                    CampaignCandidateRun(
                        "failing-candidate",
                        None,
                        None,
                        "failed",
                        "candidate failed",
                    ),
                ],
                skipped_candidates=[],
                csv_reports=[ExportResult(Path("reports/campaign-mode/baseline-1.csv"), 2)],
                excel_report=None,
                final_reports=[],
                warnings=[],
            )

    monkeypatch.setattr(cli, "ExperimentRunner", FakeRunner)

    result = CliRunner().invoke(
        app,
        ["campaign", "--project", "tests/fixtures/projects/campaign_mode.yaml"],
    )

    assert result.exit_code == 1
    assert "campaign: completed-with-failures" in result.stdout
    assert "candidate: included-candidate candidate-1" in result.stdout
    assert "failed: failing-candidate candidate failed" in result.stdout
    assert "report: reports\\campaign-mode\\baseline-1.csv" in result.stdout
