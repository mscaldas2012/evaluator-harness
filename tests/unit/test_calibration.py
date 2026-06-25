from __future__ import annotations

import json
from pathlib import Path

from evaluator_harness.calibration import (
    CalibrationRecord,
    CalibrationSnapshotResult,
    build_calibration_snapshot,
    summarize_calibration_snapshot,
)
    

def test_build_calibration_snapshot_marks_pending_and_paired_items(tmp_path: Path) -> None:
    traces = [
        {
            "trace_id": "trace-1",
            "run_id": "candidate-1",
            "input": "Source 1",
            "output": "Candidate 1",
            "metadata": {
                "project": "rewrite-quality",
                "project_version": "v1",
                "dataset_item_id": "1",
                "dataset_name": "rewrite-quality/v1",
                "dataset_compatibility_version": "sha256:test",
                "prompt_version": "v1",
                "evaluator_set_id": "clarity:v1",
                "baseline_reference": {"baseline_run_id": "baseline-1"},
            },
        },
        {
            "trace_id": "trace-2",
            "run_id": "candidate-1",
            "input": "Source 2",
            "output": "Candidate 2",
            "metadata": {
                "project": "rewrite-quality",
                "project_version": "v1",
                "dataset_item_id": "2",
                "dataset_name": "rewrite-quality/v1",
                "dataset_compatibility_version": "sha256:test",
                "prompt_version": "v1",
                "evaluator_set_id": "clarity:v1",
                "baseline_reference": {"baseline_run_id": "baseline-1"},
            },
        },
    ]
    scores = [
        {
            "id": "score-1",
            "name": "clarity",
            "trace_id": "trace-1",
            "value": 0.8,
            "comment": "judge",
            "source": "EVAL",
        },
        {
            "id": "score-2",
            "name": "clarity",
            "trace_id": "trace-1",
            "value": 0.6,
            "comment": "human",
            "source": "ANNOTATION",
        },
        {
            "id": "score-3",
            "name": "clarity",
            "trace_id": "trace-2",
            "value": 0.4,
            "comment": "judge",
            "source": "EVAL",
        },
    ]
    selections = [
        {
            "item_id": "1",
            "run_id": "candidate-1",
            "trace_id": "trace-1",
            "selection_reason": "sample",
            "selection_bucket": "stable_calibration",
        },
        {
            "item_id": "2",
            "run_id": "candidate-1",
            "trace_id": "trace-2",
            "selection_reason": "low_confidence",
            "selection_bucket": "run_risk",
        },
    ]

    result = build_calibration_snapshot(
        project_name="rewrite-quality",
        project_version="v1",
        run_id="candidate-1",
        run_type="candidate",
        traces=traces,
        scores=scores,
        selections=selections,
        evaluator_names=["clarity"],
        output_dir=tmp_path,
    )

    assert isinstance(result, CalibrationSnapshotResult)
    assert result.row_count == 2
    assert result.paired_count == 1
    assert result.pending_count == 1
    assert result.output_path.exists()
    payload = json.loads(result.output_path.read_text(encoding="utf-8"))
    assert payload[0]["selection_reason"] == "sample"
    assert payload[0]["paired"] is True
    assert payload[1]["pending_label"] is True


def test_completed_annotation_snapshot_keeps_only_paired_evaluator_rows(
    tmp_path: Path,
) -> None:
    traces = [
        {
            "trace_id": "trace-1",
            "run_id": "candidate-1",
            "metadata": {"dataset_item_id": "1"},
        }
    ]
    scores = [
        {
            "name": "clarity",
            "trace_id": "trace-1",
            "value": 0.8,
            "source": "EVAL",
        },
        {
            "name": "clarity",
            "trace_id": "trace-1",
            "value": 0.6,
            "source": "ANNOTATION",
        },
        {
            "name": "relevance",
            "trace_id": "trace-1",
            "value": 0.9,
            "source": "EVAL",
        },
    ]
    selections = [
        {
            "item_id": "1",
            "run_id": "candidate-1",
            "trace_id": "trace-1",
            "selection_reason": "annotated_queue_item",
            "selection_bucket": "completed_annotation",
        }
    ]

    result = build_calibration_snapshot(
        project_name="rewrite-quality",
        project_version="v1",
        run_id="candidate-1",
        run_type="candidate",
        traces=traces,
        scores=scores,
        selections=selections,
        evaluator_names=["clarity", "relevance"],
        output_dir=tmp_path,
    )

    assert result.row_count == 1
    assert result.paired_count == 1
    assert result.pending_count == 0
    payload = json.loads(result.output_path.read_text(encoding="utf-8"))
    assert payload[0]["evaluator_name"] == "clarity"


def test_cleaner_completed_annotation_snapshot_replaces_pending_existing_snapshot(
    tmp_path: Path,
) -> None:
    (tmp_path / "candidate-1.json").write_text(
        json.dumps(
            [
                {
                    "item_id": "1",
                    "trace_id": "trace-1",
                    "run_id": "candidate-1",
                    "evaluator_name": "clarity",
                    "automated_score": 0.8,
                    "human_score": 0.6,
                    "paired": True,
                    "pending_label": False,
                },
                {
                    "item_id": "1",
                    "trace_id": "trace-1",
                    "run_id": "candidate-1",
                    "evaluator_name": "relevance",
                    "automated_score": 0.9,
                    "human_score": None,
                    "paired": False,
                    "pending_label": True,
                },
            ]
        ),
        encoding="utf-8",
    )

    result = build_calibration_snapshot(
        project_name="rewrite-quality",
        project_version="v1",
        run_id="candidate-1",
        run_type="candidate",
        traces=[
            {
                "trace_id": "trace-1",
                "run_id": "candidate-1",
                "metadata": {"dataset_item_id": "1"},
            }
        ],
        scores=[
            {
                "name": "clarity",
                "trace_id": "trace-1",
                "value": 0.8,
                "source": "EVAL",
            },
            {
                "name": "clarity",
                "trace_id": "trace-1",
                "value": 0.6,
                "source": "ANNOTATION",
            },
        ],
        selections=[
            {
                "item_id": "1",
                "run_id": "candidate-1",
                "trace_id": "trace-1",
                "selection_reason": "annotated_queue_item",
                "selection_bucket": "completed_annotation",
            }
        ],
        evaluator_names=["clarity", "relevance"],
        output_dir=tmp_path,
    )

    assert result.row_count == 1
    assert result.paired_count == 1
    assert result.pending_count == 0
    payload = json.loads(result.output_path.read_text(encoding="utf-8"))
    assert [record["evaluator_name"] for record in payload] == ["clarity"]


def test_calibration_record_delta_is_human_minus_automated() -> None:
    record = CalibrationRecord(
        item_id="1",
        trace_id="trace-1",
        run_id="candidate-1",
        evaluator_name="clarity",
        selection_reason="sample",
        selection_bucket="stable_calibration",
        automated_score=0.8,
        human_score=0.6,
    )

    assert record.score_delta == -0.2
    assert record.paired is True
    assert record.pending_label is False


def test_summarize_calibration_snapshot_calculates_metrics_and_warnings(
    tmp_path: Path,
) -> None:
    snapshot_path = tmp_path / "candidate-1.json"
    snapshot_path.write_text(
        json.dumps(
            [
                {
                    "item_id": "1",
                    "trace_id": "trace-1",
                    "run_id": "candidate-1",
                    "evaluator_name": "clarity",
                    "score_target": "managed.clarity",
                    "automated_score": 0.8,
                    "human_score": 0.6,
                    "score_delta": -0.2,
                    "paired": True,
                    "pending_label": False,
                },
                {
                    "item_id": "2",
                    "trace_id": "trace-2",
                    "run_id": "candidate-1",
                    "evaluator_name": "clarity",
                    "score_target": "managed.clarity",
                    "automated_score": 0.4,
                    "human_score": 0.4,
                    "score_delta": 0.0,
                    "paired": True,
                    "pending_label": False,
                },
                {
                    "item_id": "3",
                    "trace_id": "trace-3",
                    "run_id": "candidate-1",
                    "evaluator_name": "fluency",
                    "score_target": "managed.fluency",
                    "automated_score": 0.9,
                    "human_score": None,
                    "score_delta": None,
                    "paired": False,
                    "pending_label": True,
                },
            ]
        ),
        encoding="utf-8",
    )

    result = summarize_calibration_snapshot(
        snapshot_path,
        project_name="rewrite-quality",
        project_version="v1",
    )

    assert result.output_path == tmp_path / "candidate-1-summary.json"
    assert result.summary_count == 2
    assert result.paired_count == 2
    assert result.pending_count == 1
    assert result.warnings == (
        "Evaluator fluency has zero paired coverage for run candidate-1.",
    )
    payload = json.loads(result.output_path.read_text(encoding="utf-8"))
    assert payload == [
        {
            "project_name": "rewrite-quality",
            "project_version": "v1",
            "run_id": "candidate-1",
            "evaluator_name": "clarity",
            "score_target": "managed.clarity",
            "record_count": 2,
            "paired_count": 2,
            "pending_count": 0,
            "paired_coverage": 1.0,
            "disagreement_rate": 0.5,
            "mean_absolute_score_delta": 0.1,
            "directional_bias": -0.1,
            "warnings": [],
        },
        {
            "project_name": "rewrite-quality",
            "project_version": "v1",
            "run_id": "candidate-1",
            "evaluator_name": "fluency",
            "score_target": "managed.fluency",
            "record_count": 1,
            "paired_count": 0,
            "pending_count": 1,
            "paired_coverage": 0.0,
            "disagreement_rate": 0.0,
            "mean_absolute_score_delta": 0.0,
            "directional_bias": 0.0,
            "warnings": [
                "Evaluator fluency has zero paired coverage for run candidate-1."
            ],
        },
    ]
