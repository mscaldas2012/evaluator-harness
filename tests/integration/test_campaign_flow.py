from __future__ import annotations

from pathlib import Path

from evaluator_harness.langfuse_default_gateway import DefaultLangfuseGateway
from evaluator_harness.runner import ExperimentRunner


def test_campaign_success_with_fake_backed_dry_run(monkeypatch) -> None:
    report_calls: list[dict[str, object]] = []

    def fake_create_comparison_reports(**kwargs):
        report_calls.append(kwargs)
        return [
            type(
                "FakeWorkbook",
                (),
                {
                    "format": "excel",
                    "output_path": Path("reports/campaign-mode/baseline-comparison.xlsx"),
                    "warnings": (),
                },
            )()
        ]

    monkeypatch.setattr(
        "evaluator_harness.runner.create_comparison_reports",
        fake_create_comparison_reports,
    )
    runner = ExperimentRunner(langfuse_gateway=DefaultLangfuseGateway())

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
    assert report_calls[0]["baseline_run_id"] == result.baseline_run.run_id


def test_campaign_runs_all_candidates_except_explicitly_excluded(monkeypatch) -> None:
    monkeypatch.setattr(
        "evaluator_harness.runner.create_comparison_reports",
        lambda **_kwargs: [
            type(
                "FakeWorkbook",
                (),
                {
                    "format": "excel",
                    "output_path": Path("reports/campaign-mode/baseline-comparison.xlsx"),
                    "warnings": (),
                },
            )()
        ],
    )
    runner = ExperimentRunner(langfuse_gateway=DefaultLangfuseGateway())

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
