from __future__ import annotations

import json
from pathlib import Path

import pytest

from evaluator_harness.campaign_calibration import (
    CampaignCalibrationRun,
    CampaignRunCalibrationResult,
    CampaignRunReference,
)
from evaluator_harness.errors import ConfigError


def test_build_campaign_calibration_report_payload_loads_summaries_and_snapshots(
    tmp_path: Path,
) -> None:
    from evaluator_harness.campaign_calibration_reports import (
        build_campaign_calibration_report_payload,
    )

    summary_path, snapshot_path = _write_summary_and_snapshot(tmp_path, "baseline-1")
    campaign_run = CampaignCalibrationRun(
        project_name="campaign-mode",
        project_version="1",
        baseline_run_id="baseline-1",
        source="manifest",
        run_references=[CampaignRunReference("baseline-1", "baseline")],
        run_results=[
            CampaignRunCalibrationResult(
                "baseline-1",
                "baseline",
                None,
                "completed",
                snapshot_path=snapshot_path,
                summary_path=summary_path,
            )
        ],
    )

    payload = build_campaign_calibration_report_payload(
        campaign_run,
        output_path=tmp_path / "baseline-1-calibration-report.html",
    )

    assert payload.baseline_run_id == "baseline-1"
    assert payload.evaluator_summaries[0]["evaluator_name"] == "clarity"
    assert payload.paired_records[0]["item_id"] == "1"
    assert payload.pending_records[0]["item_id"] == "3"


def test_derive_campaign_calibration_report_path_validates_html_suffix(
    tmp_path: Path,
) -> None:
    from evaluator_harness.campaign_calibration_reports import (
        derive_campaign_calibration_report_path,
    )

    assert derive_campaign_calibration_report_path(
        "baseline-1",
        reports_dir=tmp_path,
    ) == (tmp_path / "baseline-1-calibration-report.html").resolve()
    with pytest.raises(ConfigError, match=".html"):
        derive_campaign_calibration_report_path(
            "baseline-1",
            reports_dir=tmp_path,
            output_path=tmp_path / "report.txt",
        )


def test_render_campaign_calibration_html_includes_metrics_and_warnings(
    tmp_path: Path,
) -> None:
    from evaluator_harness.campaign_calibration_reports import (
        build_campaign_calibration_report_payload,
        render_campaign_calibration_report,
    )

    summary_path, snapshot_path = _write_summary_and_snapshot(tmp_path, "candidate-1")
    campaign_run = CampaignCalibrationRun(
        project_name="campaign-mode",
        project_version="1",
        baseline_run_id="baseline-1",
        source="manifest",
        run_references=[CampaignRunReference("candidate-1", "candidate")],
        run_results=[
            CampaignRunCalibrationResult(
                "candidate-1",
                "candidate",
                "included",
                "warning",
                snapshot_path=snapshot_path,
                summary_path=summary_path,
                warnings=("missing annotation",),
            )
        ],
        warnings=("candidate-1: missing annotation",),
    )
    payload = build_campaign_calibration_report_payload(
        campaign_run,
        output_path=tmp_path / "baseline-1-calibration-report.html",
    )

    html = render_campaign_calibration_report(payload)

    assert "Campaign Calibration Report" in html
    assert "candidate-1" in html
    assert "paired coverage" in html.lower()
    assert "disagreement rate" in html.lower()
    assert "mean absolute score delta" in html.lower()
    assert "directional bias" in html.lower()
    assert "Largest Deltas" in html
    assert "Pending Records" in html
    assert "trace-2" in html
    assert "trace-3" in html
    assert "candidate-1: missing annotation" in html
    assert "2/3" in html
    assert "(66.7%)" in html
    assert "1/2" in html
    assert "(50%)" in html


def test_render_campaign_calibration_html_styles_run_groups_and_deltas(
    tmp_path: Path,
) -> None:
    from evaluator_harness.campaign_calibration_reports import (
        build_campaign_calibration_report_payload,
        render_campaign_calibration_report,
    )

    baseline_summary, baseline_snapshot = _write_summary_and_snapshot(
        tmp_path,
        "baseline-1",
        directional_bias=0.2,
    )
    baseline_csv = _write_run_csv(
        tmp_path,
        "baseline-1",
        model="gpt-4.1",
        prompt_version="v1",
        temperature="0.1",
    )
    candidate_summary, candidate_snapshot = _write_summary_and_snapshot(
        tmp_path,
        "candidate-a",
        directional_bias=-0.2,
    )
    candidate_csv = _write_run_csv(
        tmp_path,
        "candidate-a",
        model="mistral-large-3",
        prompt_version="consolidated",
        temperature="0.2",
    )
    campaign_run = CampaignCalibrationRun(
        project_name="campaign-mode",
        project_version="1",
        baseline_run_id="baseline-1",
        source="manifest",
        run_references=[
            CampaignRunReference(
                "baseline-1",
                "baseline",
                csv_report_path=baseline_csv,
            ),
            CampaignRunReference(
                "candidate-a",
                "candidate",
                "candidate-a",
                csv_report_path=candidate_csv,
            ),
        ],
        run_results=[
            CampaignRunCalibrationResult(
                "baseline-1",
                "baseline",
                None,
                "completed",
                snapshot_path=baseline_snapshot,
                summary_path=baseline_summary,
            ),
            CampaignRunCalibrationResult(
                "candidate-a",
                "candidate",
                "candidate-a",
                "completed",
                snapshot_path=candidate_snapshot,
                summary_path=candidate_summary,
            ),
        ],
    )
    payload = build_campaign_calibration_report_payload(
        campaign_run,
        output_path=tmp_path / "baseline-1-calibration-report.html",
    )

    html = render_campaign_calibration_report(payload)

    assert 'class="run-badge baseline run-color-0"' in html
    assert 'class="run-badge candidate run-color-1"' in html
    assert 'class="run-label"' in html
    assert 'title="candidate-a"' in html
    assert "run-color-0" in html
    assert "run-color-1" in html
    assert 'data-run-id="baseline-1"' in html
    assert 'data-run-id="candidate-a"' in html
    assert '<select id="run-filter"' in html
    assert '<option value="candidate-a">candidate-a</option>' in html
    assert "applyRunFilter" in html
    assert 'class="delta delta-up"' in html
    assert 'class="delta delta-down"' in html
    assert "&#9650;" in html
    assert "&#9660;" in html
    assert "Evaluator Trend" in html
    assert 'class="sparkline"' in html
    assert '<details class="table-panel" open>' in html
    assert "<summary><h2>Run Overview</h2></summary>" in html
    assert 'class="pivot-run-diff"' in html
    assert "model: mistral-large-3" in html
    assert "prompt: consolidated" in html
    assert "temp: 0.2" in html
    assert "Mean absolute score delta</th>" in html
    mean_abs_index = html.index("Mean absolute score delta</th>")
    directional_index = html.index("Directional bias</th>")
    mean_abs_column_html = html[mean_abs_index:directional_index]
    assert "delta-up" not in mean_abs_column_html
    assert "delta-down" not in mean_abs_column_html


def _write_run_csv(
    tmp_path: Path,
    run_id: str,
    *,
    model: str,
    prompt_version: str,
    temperature: str,
) -> Path:
    path = tmp_path / f"{run_id}.csv"
    path.write_text(
        "\n".join(
            [
                "run_id,model,prompt_version,temperature",
                f"{run_id},{model},{prompt_version},{temperature}",
            ]
        ),
        encoding="utf-8",
    )
    return path


def _write_summary_and_snapshot(
    tmp_path: Path,
    run_id: str,
    *,
    directional_bias: float = -0.2,
) -> tuple[Path, Path]:
    summary_path = tmp_path / f"{run_id}-summary.json"
    snapshot_path = tmp_path / f"{run_id}.json"
    summary_path.write_text(
        json.dumps(
            [
                {
                    "project_name": "campaign-mode",
                    "project_version": "1",
                    "run_id": run_id,
                    "evaluator_name": "clarity",
                    "score_target": "managed.clarity",
                    "record_count": 3,
                    "paired_count": 2,
                    "pending_count": 1,
                    "paired_coverage": 0.6666666667,
                    "disagreement_rate": 0.5,
                    "mean_absolute_score_delta": 0.2,
                    "directional_bias": directional_bias,
                    "warnings": [],
                }
            ]
        ),
        encoding="utf-8",
    )
    snapshot_path.write_text(
        json.dumps(
            [
                {
                    "item_id": "1",
                    "trace_id": "trace-1",
                    "run_id": run_id,
                    "evaluator_name": "clarity",
                    "automated_score": 0.8,
                    "human_score": 0.6,
                    "score_delta": -0.2,
                    "paired": True,
                    "pending_label": False,
                },
                {
                    "item_id": "2",
                    "trace_id": "trace-2",
                    "run_id": run_id,
                    "evaluator_name": "clarity",
                    "automated_score": 0.1,
                    "human_score": 0.9,
                    "score_delta": -0.8,
                    "paired": True,
                    "pending_label": False,
                },
                {
                    "item_id": "3",
                    "trace_id": "trace-3",
                    "run_id": run_id,
                    "evaluator_name": "clarity",
                    "automated_score": 0.4,
                    "human_score": None,
                    "score_delta": None,
                    "paired": False,
                    "pending_label": True,
                }
            ]
        ),
        encoding="utf-8",
    )
    return summary_path, snapshot_path
