from __future__ import annotations

from pathlib import Path

from evaluator_harness.calibration import (
    CalibrationSnapshotResult,
    CalibrationSummaryResult,
)
from evaluator_harness.runner import ExperimentRunner


def test_campaign_calibration_capture_flow_uses_manifest_run_ids(
    tmp_path: Path,
) -> None:
    from evaluator_harness.campaign_calibration import (
        CampaignManifest,
        CampaignRunReference,
        capture_campaign_calibration,
        resolve_campaign_run_references,
        write_campaign_manifest,
    )

    write_campaign_manifest(
        CampaignManifest(
            project_name="campaign-mode",
            project_version="1",
            baseline_run_id="baseline-1",
            reports_dir=tmp_path,
            generated_at="2026-06-25T00:00:00Z",
            runs=[
                CampaignRunReference(run_id="baseline-1", role="baseline"),
                CampaignRunReference(
                    run_id="candidate-1",
                    role="candidate",
                    candidate_name="included",
                ),
            ],
        )
    )
    resolved = resolve_campaign_run_references("baseline-1", reports_dir=tmp_path)
    calls: list[str] = []

    def capture(run_id: str) -> CalibrationSnapshotResult:
        calls.append(run_id)
        return CalibrationSnapshotResult(
            tmp_path / "calibration" / f"{run_id}.json",
            1,
            1,
            0,
        )

    result = capture_campaign_calibration(
        project_name="campaign-mode",
        project_version="1",
        baseline_run_id="baseline-1",
        source=resolved.source,
        run_references=resolved.runs,
        capture_run=capture,
    )

    assert calls == ["baseline-1", "candidate-1"]
    assert result.captured_count == 2


def test_campaign_calibration_summary_flow_writes_summary_paths(
    tmp_path: Path,
) -> None:
    from evaluator_harness.campaign_calibration import (
        CampaignRunReference,
        capture_campaign_calibration,
        summarize_campaign_calibration,
    )

    captured = capture_campaign_calibration(
        project_name="campaign-mode",
        project_version="1",
        baseline_run_id="baseline-1",
        source="manifest",
        run_references=[
            CampaignRunReference(run_id="baseline-1", role="baseline"),
            CampaignRunReference(run_id="candidate-1", role="candidate"),
        ],
        capture_run=lambda run_id: CalibrationSnapshotResult(
            tmp_path / "calibration" / f"{run_id}.json",
            1,
            1,
            0,
        ),
    )

    def summarize(run_id: str) -> CalibrationSummaryResult:
        output = tmp_path / "calibration" / f"{run_id}-summary.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("[]", encoding="utf-8")
        return CalibrationSummaryResult(output, 1, 1, 0)

    result = summarize_campaign_calibration(captured, summarize_run=summarize)

    assert result.summarized_count == 2
    assert all(
        run.summary_path and run.summary_path.exists()
        for run in result.run_results
    )


def test_runner_campaign_calibration_report_writes_html_report(
    tmp_path: Path,
) -> None:
    from evaluator_harness.campaign_calibration import (
        CampaignManifest,
        CampaignRunReference,
        write_campaign_manifest,
    )

    class FakeRunner(ExperimentRunner):
        def calibration_capture(self, project_path, run_id, *, output_dir=None):
            output = Path(output_dir) / f"{run_id}.json"
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(
                '[{"item_id":"1","trace_id":"trace-1","run_id":"'
                + run_id
                + '","evaluator_name":"clarity","automated_score":0.8,'
                '"human_score":0.6,"score_delta":-0.2,"paired":true,'
                '"pending_label":false}]',
                encoding="utf-8",
            )
            return CalibrationSnapshotResult(output, 1, 1, 0)

        def calibration_summary(self, project_path, run_id, *, output_dir=None):
            output = Path(output_dir) / f"{run_id}-summary.json"
            output.write_text(
                '[{"project_name":"campaign-mode","project_version":"1",'
                '"run_id":"'
                + run_id
                + '","evaluator_name":"clarity","score_target":"managed.clarity",'
                '"record_count":1,"paired_count":1,"pending_count":0,'
                '"paired_coverage":1.0,"disagreement_rate":0.5,'
                '"mean_absolute_score_delta":0.2,"directional_bias":-0.2,'
                '"warnings":[]}]',
                encoding="utf-8",
            )
            return CalibrationSummaryResult(output, 1, 1, 0)

    write_campaign_manifest(
        CampaignManifest(
            project_name="campaign-mode",
            project_version="1",
            baseline_run_id="baseline-1",
            reports_dir=tmp_path,
            generated_at="2026-06-25T00:00:00Z",
            runs=[CampaignRunReference("baseline-1", "baseline")],
        )
    )

    result = FakeRunner().campaign_calibration_report(
        Path("tests/fixtures/projects/campaign_mode.yaml"),
        "baseline-1",
        reports_dir=tmp_path,
    )

    assert result.html_report_path == (
        tmp_path / "baseline-1-calibration-report.html"
    ).resolve()
    assert result.html_report_path.exists()
