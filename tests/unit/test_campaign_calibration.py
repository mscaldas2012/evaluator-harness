from __future__ import annotations

from pathlib import Path

import pytest

from evaluator_harness.calibration import (
    CalibrationSnapshotResult,
    CalibrationSummaryResult,
)
from evaluator_harness.campaigns import (
    CampaignCandidateRun,
    CampaignCandidateSelection,
    CampaignRunResult,
)
from evaluator_harness.config import load_project_config
from evaluator_harness.errors import ConfigError
from evaluator_harness.exports import ExportResult
from evaluator_harness.runner import RunResult


def test_campaign_manifest_requires_matching_baseline_reference() -> None:
    from evaluator_harness.campaign_calibration import (
        CampaignManifest,
        CampaignRunReference,
    )

    with pytest.raises(ConfigError, match="baseline run"):
        CampaignManifest(
            project_name="campaign-mode",
            project_version="1",
            baseline_run_id="baseline-1",
            reports_dir=Path("reports/campaign-mode"),
            generated_at="2026-06-25T00:00:00Z",
            runs=[
                CampaignRunReference(
                    run_id="candidate-1",
                    role="candidate",
                    candidate_name="candidate",
                    csv_report_path=Path("reports/campaign-mode/candidate-1.csv"),
                )
            ],
        )


def test_manifest_from_campaign_result_records_baseline_and_candidates() -> None:
    from evaluator_harness.campaign_calibration import manifest_from_campaign_result

    config = load_project_config(Path("tests/fixtures/projects/campaign_mode.yaml"))
    result = CampaignRunResult(
        baseline_run=RunResult("baseline-1", "baseline", 2, 0),
        candidate_runs=[
            CampaignCandidateRun(
                "included-candidate",
                RunResult("candidate-1", "candidate", 2, 0),
                ExportResult(Path("reports/campaign-mode/candidate-1.csv"), 2),
                "completed",
            ),
            CampaignCandidateRun(
                "failed-candidate",
                None,
                None,
                "failed",
                "candidate failed",
            ),
        ],
        skipped_candidates=[
            CampaignCandidateSelection(
                "excluded-candidate",
                False,
                "exclude-from-campaign=true",
            )
        ],
        csv_reports=[ExportResult(Path("reports/campaign-mode/baseline-1.csv"), 2)],
        excel_report=None,
        final_reports=[],
        warnings=["campaign warning"],
    )

    manifest = manifest_from_campaign_result(
        config=config,
        result=result,
        reports_dir=Path("reports/campaign-mode"),
    )

    assert manifest.baseline_run_id == "baseline-1"
    assert [(run.role, run.run_id, run.status) for run in manifest.runs] == [
        ("baseline", "baseline-1", "completed"),
        ("candidate", "candidate-1", "completed"),
    ]
    assert manifest.warnings == ("campaign warning",)


def test_write_and_load_manifest_by_baseline_run_id(tmp_path: Path) -> None:
    from evaluator_harness.campaign_calibration import (
        CampaignManifest,
        CampaignRunReference,
        load_campaign_manifest,
        write_campaign_manifest,
    )

    manifest = CampaignManifest(
        project_name="campaign-mode",
        project_version="1",
        baseline_run_id="baseline-1",
        reports_dir=tmp_path,
        generated_at="2026-06-25T00:00:00Z",
        runs=[
            CampaignRunReference(
                run_id="baseline-1",
                role="baseline",
                csv_report_path=tmp_path / "baseline-1.csv",
            )
        ],
    )

    output_path = write_campaign_manifest(manifest)
    loaded = load_campaign_manifest(tmp_path, "baseline-1")

    assert output_path == tmp_path / "campaign-manifests" / "baseline-1.json"
    assert loaded == manifest


def test_fallback_discovery_uses_csv_exports_when_manifest_is_missing(
    tmp_path: Path,
) -> None:
    from evaluator_harness.campaign_calibration import resolve_campaign_run_references

    _write_csv(
        tmp_path / "baseline-1.csv",
        [
            {
                "run_id": "baseline-1",
                "run_type": "baseline",
                "baseline_run_id": "",
            }
        ],
    )
    _write_csv(
        tmp_path / "candidate-1.csv",
        [
            {
                "run_id": "candidate-1",
                "run_type": "candidate",
                "baseline_run_id": "baseline-1",
                "candidate_name": "included",
            }
        ],
    )

    result = resolve_campaign_run_references("baseline-1", reports_dir=tmp_path)

    assert result.source == "fallback-artifacts"
    assert [(run.role, run.run_id, run.candidate_name) for run in result.runs] == [
        ("baseline", "baseline-1", None),
        ("candidate", "candidate-1", "included"),
    ]


def test_fallback_discovery_fails_when_baseline_export_is_missing(
    tmp_path: Path,
) -> None:
    from evaluator_harness.campaign_calibration import resolve_campaign_run_references

    with pytest.raises(ConfigError, match="No campaign manifest or CSV report"):
        resolve_campaign_run_references("baseline-1", reports_dir=tmp_path)


def test_resolve_campaign_run_references_prefers_manifest_over_fallback(
    tmp_path: Path,
) -> None:
    from evaluator_harness.campaign_calibration import (
        CampaignManifest,
        CampaignRunReference,
        resolve_campaign_run_references,
        write_campaign_manifest,
    )

    _write_csv(
        tmp_path / "baseline-1.csv",
        [{"run_id": "baseline-1", "run_type": "baseline", "baseline_run_id": ""}],
    )
    manifest = CampaignManifest(
        project_name="campaign-mode",
        project_version="1",
        baseline_run_id="baseline-1",
        reports_dir=tmp_path,
        generated_at="2026-06-25T00:00:00Z",
        runs=[
            CampaignRunReference(run_id="baseline-1", role="baseline"),
            CampaignRunReference(
                run_id="candidate-from-manifest",
                role="candidate",
                candidate_name="manifest-candidate",
            ),
        ],
    )
    write_campaign_manifest(manifest)

    result = resolve_campaign_run_references("baseline-1", reports_dir=tmp_path)

    assert result.source == "manifest"
    assert [run.run_id for run in result.runs] == [
        "baseline-1",
        "candidate-from-manifest",
    ]


def test_capture_campaign_calibration_supports_baseline_only_run(
    tmp_path: Path,
) -> None:
    from evaluator_harness.campaign_calibration import (
        CampaignRunReference,
        capture_campaign_calibration,
    )

    calls: list[str] = []

    def capture(run_id: str) -> CalibrationSnapshotResult:
        calls.append(run_id)
        return CalibrationSnapshotResult(tmp_path / f"{run_id}.json", 1, 1, 0)

    result = capture_campaign_calibration(
        project_name="campaign-mode",
        project_version="1",
        baseline_run_id="baseline-1",
        source="manifest",
        run_references=[CampaignRunReference(run_id="baseline-1", role="baseline")],
        capture_run=capture,
    )

    assert calls == ["baseline-1"]
    assert result.captured_count == 1
    assert result.run_results[0].status == "completed"


def test_capture_campaign_calibration_continues_after_candidate_warning(
    tmp_path: Path,
) -> None:
    from evaluator_harness.campaign_calibration import (
        CampaignRunReference,
        capture_campaign_calibration,
    )

    def capture(run_id: str) -> CalibrationSnapshotResult:
        warnings = ("missing annotations",) if run_id == "candidate-1" else ()
        return CalibrationSnapshotResult(tmp_path / f"{run_id}.json", 1, 0, 1, warnings)

    result = capture_campaign_calibration(
        project_name="campaign-mode",
        project_version="1",
        baseline_run_id="baseline-1",
        source="manifest",
        run_references=[
            CampaignRunReference(run_id="baseline-1", role="baseline"),
            CampaignRunReference(
                run_id="candidate-1",
                role="candidate",
                candidate_name="candidate",
            ),
            CampaignRunReference(
                run_id="candidate-2",
                role="candidate",
                candidate_name="candidate-2",
            ),
        ],
        capture_run=capture,
    )

    assert [run.run_id for run in result.run_results] == [
        "baseline-1",
        "candidate-1",
        "candidate-2",
    ]
    assert result.captured_count == 3
    assert result.run_results[1].status == "warning"
    assert "candidate-1: missing annotations" in result.warnings


def test_summarize_campaign_calibration_summarizes_successful_runs(
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
            tmp_path / f"{run_id}.json",
            2,
            2,
            0,
        ),
    )
    calls: list[str] = []

    def summarize(run_id: str) -> CalibrationSummaryResult:
        calls.append(run_id)
        return CalibrationSummaryResult(
            tmp_path / f"{run_id}-summary.json",
            1,
            2,
            0,
        )

    result = summarize_campaign_calibration(captured, summarize_run=summarize)

    assert calls == ["baseline-1", "candidate-1"]
    assert result.summarized_count == 2
    assert [run.summary_path for run in result.run_results] == [
        tmp_path / "baseline-1-summary.json",
        tmp_path / "candidate-1-summary.json",
    ]


def test_summarize_campaign_calibration_propagates_zero_coverage_warning(
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
        run_references=[CampaignRunReference(run_id="baseline-1", role="baseline")],
        capture_run=lambda run_id: CalibrationSnapshotResult(
            tmp_path / f"{run_id}.json",
            1,
            0,
            1,
        ),
    )

    result = summarize_campaign_calibration(
        captured,
        summarize_run=lambda run_id: CalibrationSummaryResult(
            tmp_path / f"{run_id}-summary.json",
            1,
            0,
            1,
            warnings=("Evaluator clarity has zero paired coverage.",),
        ),
    )

    assert result.run_results[0].status == "warning"
    assert (
        "baseline-1: Evaluator clarity has zero paired coverage."
        in result.warnings
    )


def test_summarize_campaign_calibration_keeps_baseline_when_candidate_fails(
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
            tmp_path / f"{run_id}.json",
            1,
            1,
            0,
        ),
    )

    def summarize(run_id: str) -> CalibrationSummaryResult:
        if run_id == "candidate-1":
            raise ConfigError("summary failed")
        return CalibrationSummaryResult(tmp_path / f"{run_id}-summary.json", 1, 1, 0)

    result = summarize_campaign_calibration(captured, summarize_run=summarize)

    assert result.summarized_count == 1
    assert [run.status for run in result.run_results] == ["completed", "failed"]
    assert "candidate-1: summary failed" in result.warnings


def _write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    headers = list(rows[0])
    lines = [",".join(headers)]
    lines.extend(",".join(row.get(header, "") for header in headers) for row in rows)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
