from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

import evaluator_harness.cli as cli
from evaluator_harness.cli import app


def test_campaign_calibration_report_cli_invokes_runner(monkeypatch) -> None:
    class FakeRunner:
        def campaign_calibration_report(self, project, **kwargs):
            assert project == Path("tests/fixtures/projects/campaign_mode.yaml")
            assert kwargs["baseline_run_id"] == "baseline-1"
            assert kwargs["reports_dir"] is None
            assert kwargs["output_path"] is None
            assert kwargs["output_dir"] is None
            return type(
                "FakeCampaignCalibration",
                (),
                {
                    "baseline_run_id": "baseline-1",
                    "run_count": 2,
                    "captured_count": 2,
                    "summarized_count": 2,
                    "source": "manifest",
                    "html_report_path": Path(
                        "reports/campaign-mode/baseline-1-calibration-report.html"
                    ),
                    "warnings": ("candidate-1: missing annotations",),
                    "run_results": [],
                },
            )()

    monkeypatch.setattr(cli, "ExperimentRunner", FakeRunner)

    result = CliRunner().invoke(
        app,
        [
            "campaign-calibration-report",
            "--project",
            "tests/fixtures/projects/campaign_mode.yaml",
            "--baseline",
            "baseline-1",
        ],
    )

    assert result.exit_code == 0
    assert "campaign-calibration: completed" in result.stdout
    assert "baseline: baseline-1" in result.stdout
    assert "runs: 2" in result.stdout
    assert "captured: 2" in result.stdout
    assert "summarized: 2" in result.stdout
    assert (
        "report: reports\\campaign-mode\\baseline-1-calibration-report.html"
        in result.stdout
    )
    assert "source: manifest" in result.stdout
    assert "warning-count: 1" in result.stdout
    assert "warning: candidate-1: missing annotations" in result.stdout
