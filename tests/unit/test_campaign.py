from __future__ import annotations

from pathlib import Path

from evaluator_harness.config import load_project_config
from evaluator_harness.errors import RuntimeDependencyError
from evaluator_harness.exports import ExportResult
from evaluator_harness.runner import (
    CampaignRunResult,
    ExperimentRunner,
    RunResult,
    campaign_candidate_selections,
)


class RecordingRunner(ExperimentRunner):
    def __init__(self) -> None:
        super().__init__()
        self.run_calls: list[tuple[str, dict[str, object]]] = []
        self.export_calls: list[tuple[Path, str, str]] = []

    def run(self, project_path: Path, mode: str, **kwargs: object) -> RunResult:
        self.run_calls.append((mode, kwargs))
        if mode == "baseline":
            return RunResult("baseline-campaign", "baseline", 3, 0)
        candidate = str(kwargs["candidate"])
        return RunResult(f"candidate-{candidate}", "candidate", 3, 0)

    def export(self, project_path: Path, run_id: str, fmt: str) -> ExportResult:
        self.export_calls.append((project_path, run_id, fmt))
        return ExportResult(Path("reports/campaign-mode") / f"{run_id}.csv", 3)


class FailingCandidateRunner(RecordingRunner):
    def run(self, project_path: Path, mode: str, **kwargs: object) -> RunResult:
        self.run_calls.append((mode, kwargs))
        if mode == "baseline":
            return RunResult("baseline-campaign", "baseline", 3, 0)
        if kwargs["candidate"] == "failing-candidate":
            from evaluator_harness.errors import ConfigError

            raise ConfigError("candidate failed")
        return RunResult(f"candidate-{kwargs['candidate']}", "candidate", 3, 0)


def test_campaign_candidate_selection_includes_false_and_omitted_candidates() -> None:
    config = load_project_config(Path("tests/fixtures/projects/campaign_mode.yaml"))

    selections = campaign_candidate_selections(config)

    assert [
        (selection.candidate_name, selection.included, selection.reason)
        for selection in selections
    ] == [
        ("included-candidate", True, "exclude-from-campaign=false"),
        ("excluded-candidate", False, "exclude-from-campaign=true"),
        ("default-included-candidate", True, "exclude-from-campaign=false"),
    ]


def test_campaign_candidate_selection_identifies_skipped_candidates() -> None:
    config = load_project_config(Path("tests/fixtures/projects/campaign_mode.yaml"))

    selections = campaign_candidate_selections(config)

    skipped = [selection for selection in selections if not selection.included]
    assert [
        (selection.candidate_name, selection.reason) for selection in skipped
    ] == [
        ("excluded-candidate", "exclude-from-campaign=true"),
    ]


def test_campaign_runs_baseline_first_then_candidates_with_campaign_baseline() -> None:
    runner = RecordingRunner()

    result = runner.campaign(
        Path("tests/fixtures/projects/campaign_mode.yaml"),
        no_report=True,
    )

    assert result.baseline_run is not None
    assert result.baseline_run.run_id == "baseline-campaign"
    assert runner.run_calls == [
        ("baseline", {"select_human_review": True, "skip_sync": False}),
        (
            "candidate",
            {
                "candidate": "included-candidate",
                "baseline": "baseline-campaign",
                "select_human_review": True,
                "skip_sync": False,
            },
        ),
        (
            "candidate",
            {
                "candidate": "default-included-candidate",
                "baseline": "baseline-campaign",
                "select_human_review": True,
                "skip_sync": False,
            },
        ),
    ]


def test_campaign_passes_skip_sync_and_skip_human_review_to_runs() -> None:
    runner = RecordingRunner()

    runner.campaign(
        Path("tests/fixtures/projects/campaign_mode.yaml"),
        skip_sync=True,
        select_human_review=False,
        no_report=True,
    )

    assert all(call[1]["skip_sync"] is True for call in runner.run_calls)
    assert all(call[1]["select_human_review"] is False for call in runner.run_calls)


def test_campaign_exports_reports_and_passes_excel_overwrite(monkeypatch) -> None:
    runner = RecordingRunner()
    excel_calls: list[dict[str, object]] = []

    def fake_create_excel_report(**kwargs):
        excel_calls.append(kwargs)
        return type(
            "FakeWorkbook",
            (),
            {
                "output_path": Path("reports/campaign-mode/baseline-campaign-comparison.xlsx"),
                "warnings": (),
            },
        )()

    monkeypatch.setattr("evaluator_harness.runner.create_excel_report", fake_create_excel_report)

    result = runner.campaign(
        Path("tests/fixtures/projects/campaign_mode.yaml"),
        overwrite=True,
    )

    assert [call[1] for call in runner.export_calls] == [
        "baseline-campaign",
        "candidate-included-candidate",
        "candidate-default-included-candidate",
    ]
    assert excel_calls == [
        {
            "baseline_run_id": "baseline-campaign",
            "reports_dir": Path("reports/campaign-mode"),
            "overwrite": True,
        }
    ]
    assert result.excel_report is not None


def test_campaign_candidate_failures_preserve_successful_outputs(monkeypatch) -> None:
    runner = FailingCandidateRunner()

    monkeypatch.setattr(
        "evaluator_harness.runner.campaign_candidate_selections",
        lambda _config: [
            type("Selection", (), {"candidate_name": "included-candidate", "included": True})(),
            type("Selection", (), {"candidate_name": "failing-candidate", "included": True})(),
        ],
    )
    monkeypatch.setattr(
        "evaluator_harness.runner.create_excel_report",
        lambda **_kwargs: type(
            "FakeWorkbook",
            (),
            {
                "output_path": Path("reports/campaign-mode/baseline-campaign-comparison.xlsx"),
                "warnings": (),
            },
        )(),
    )

    result = runner.campaign(
        Path("tests/fixtures/projects/campaign_mode.yaml"),
        confirm_mixed_variant=True,
    )

    assert [candidate.status for candidate in result.candidate_runs] == [
        "completed",
        "failed",
    ]
    assert result.candidate_runs[0].run_result is not None
    assert result.candidate_runs[1].message == "candidate failed"
    assert [report.output_path.name for report in result.csv_reports] == [
        "baseline-campaign.csv",
        "candidate-included-candidate.csv",
    ]


def test_campaign_excel_failure_records_warning_and_preserves_reports(monkeypatch) -> None:
    runner = RecordingRunner()

    def fail_excel(**_kwargs):
        raise RuntimeDependencyError("Excel unavailable")

    monkeypatch.setattr("evaluator_harness.runner.create_excel_report", fail_excel)

    result = runner.campaign(Path("tests/fixtures/projects/campaign_mode.yaml"))

    assert result.excel_report is None
    assert "Excel unavailable" in result.warnings
    assert [report.output_path.name for report in result.csv_reports] == [
        "baseline-campaign.csv",
        "candidate-included-candidate.csv",
        "candidate-default-included-candidate.csv",
    ]
