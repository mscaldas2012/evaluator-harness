from __future__ import annotations

from pathlib import Path

from evaluator_harness.langfuse_client import LangfuseClient
from evaluator_harness.runner import ExperimentRunner


def test_campaign_success_with_fake_backed_dry_run(monkeypatch) -> None:
    excel_calls: list[dict[str, object]] = []

    def fake_create_excel_report(**kwargs):
        excel_calls.append(kwargs)
        return type(
            "FakeWorkbook",
            (),
            {
                "output_path": Path("reports/campaign-mode/baseline-comparison.xlsx"),
                "warnings": (),
            },
        )()

    monkeypatch.setattr("evaluator_harness.runner.create_excel_report", fake_create_excel_report)
    runner = ExperimentRunner(langfuse_client=LangfuseClient())

    result = runner.campaign(
        Path("tests/fixtures/projects/campaign_mode.yaml"),
        skip_sync=True,
        select_human_review=False,
    )

    assert result.baseline_run is not None
    assert result.baseline_run.run_id.startswith("baseline-")
    assert [candidate.candidate_name for candidate in result.candidate_runs] == [
        "included-candidate",
        "default-included-candidate",
    ]
    assert len(result.csv_reports) == 3
    assert excel_calls[0]["baseline_run_id"] == result.baseline_run.run_id


def test_campaign_runs_all_candidates_except_explicitly_excluded(monkeypatch) -> None:
    monkeypatch.setattr(
        "evaluator_harness.runner.create_excel_report",
        lambda **_kwargs: type(
            "FakeWorkbook",
            (),
            {"output_path": Path("reports/campaign-mode/baseline-comparison.xlsx"), "warnings": ()},
        )(),
    )
    runner = ExperimentRunner(langfuse_client=LangfuseClient())

    result = runner.campaign(
        Path("tests/fixtures/projects/campaign_mode.yaml"),
        skip_sync=True,
        select_human_review=False,
    )

    assert [candidate.candidate_name for candidate in result.candidate_runs] == [
        "included-candidate",
        "default-included-candidate",
    ]
    assert [candidate.candidate_name for candidate in result.skipped_candidates] == [
        "excluded-candidate",
    ]
