from __future__ import annotations

import json
from pathlib import Path

from evaluator_harness.langfuse_default_gateway import DefaultLangfuseGateway
from evaluator_harness.runner import ExperimentRunner


def test_calibration_capture_writes_rows_for_selected_review_items(tmp_path: Path) -> None:
    langfuse = DefaultLangfuseGateway()
    langfuse.traces.extend(
        [
            {
                "trace_id": "trace-1",
                "run_id": "candidate-1",
                "input": "Source 1",
                "output": "Candidate 1",
                "metadata": {
                    "dataset_item_id": "1",
                    "dataset_name": "rewrite-quality/v1",
                    "dataset_compatibility_version": "sha256:test",
                    "project": "rewrite-quality",
                    "project_version": "v1",
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
                    "dataset_item_id": "2",
                    "dataset_name": "rewrite-quality/v1",
                    "dataset_compatibility_version": "sha256:test",
                    "project": "rewrite-quality",
                    "project_version": "v1",
                    "prompt_version": "v1",
                    "evaluator_set_id": "clarity:v1",
                    "baseline_reference": {"baseline_run_id": "baseline-1"},
                },
            },
        ]
    )
    langfuse.scores["candidate-1"] = [
        {
            "id": "score-1",
            "name": "clarity",
            "trace_id": "trace-1",
            "score": 0.8,
            "source": "EVAL",
        },
        {
            "id": "score-2",
            "name": "clarity",
            "trace_id": "trace-1",
            "score": 0.7,
            "source": "ANNOTATION",
        },
        {
            "id": "score-3",
            "name": "clarity",
            "trace_id": "trace-2",
            "score": 0.4,
            "source": "EVAL",
        },
    ]

    result = ExperimentRunner(langfuse_gateway=langfuse).calibration_capture(
        Path("configs/projects/rewrite_quality.yaml"),
        "candidate-1",
        output_dir=tmp_path,
    )

    assert result.row_count == 1
    assert result.paired_count == 1
    assert result.pending_count == 0
    payload = json.loads(result.output_path.read_text(encoding="utf-8"))
    assert payload[0]["trace_id"] == "trace-1"
    assert payload[0]["selection_bucket"] == "stable_calibration"
    assert payload[0]["evaluator_version"] == "v1"
    assert payload[0]["prompt_version"] == "v1"
    assert payload[0]["evaluator_set_id"] == "clarity:v1"
    assert payload[0]["automated_score_source"] == "EVAL"
    assert payload[0]["human_score_source"] == "ANNOTATION"


def test_calibration_summary_writes_metrics_from_captured_snapshot(
    tmp_path: Path,
) -> None:
    langfuse = DefaultLangfuseGateway()
    langfuse.traces.extend(
        [
            {
                "trace_id": "trace-1",
                "run_id": "candidate-1",
                "input": "Source 1",
                "output": "Candidate 1",
                "metadata": {
                    "dataset_item_id": "1",
                    "dataset_name": "rewrite-quality/v1",
                    "dataset_compatibility_version": "sha256:test",
                    "project": "rewrite-quality",
                    "project_version": "v1",
                    "prompt_version": "v1",
                    "evaluator_set_id": "clarity:v1",
                    "baseline_reference": {"baseline_run_id": "baseline-1"},
                },
            }
        ]
    )
    langfuse.scores["candidate-1"] = [
        {
            "id": "score-1",
            "name": "clarity",
            "trace_id": "trace-1",
            "score": 0.8,
            "source": "EVAL",
        },
        {
            "id": "score-2",
            "name": "clarity",
            "trace_id": "trace-1",
            "score": 0.7,
            "source": "ANNOTATION",
        },
    ]
    runner = ExperimentRunner(langfuse_gateway=langfuse)
    runner.calibration_capture(
        Path("configs/projects/rewrite_quality.yaml"),
        "candidate-1",
        output_dir=tmp_path,
    )

    result = runner.calibration_summary(
        Path("configs/projects/rewrite_quality.yaml"),
        "candidate-1",
        output_dir=tmp_path,
    )

    assert result.summary_count == 1
    assert result.paired_count == 1
    payload = json.loads(result.output_path.read_text(encoding="utf-8"))
    assert payload[0]["run_id"] == "candidate-1"
    assert payload[0]["evaluator_name"] == "clarity"
    assert payload[0]["score_target"] == "eh_rewrite_quality_clarity"
    assert payload[0]["mean_absolute_score_delta"] == 0.1


def test_calibration_capture_pairs_completed_annotation_queue_scores(
    tmp_path: Path,
) -> None:
    langfuse = DefaultLangfuseGateway()
    langfuse.traces.append(
        {
            "trace_id": "trace-1",
            "run_id": "candidate-1",
            "input": "Source 1",
            "output": "Candidate 1",
            "metadata": {
                "dataset_item_id": "1",
                "dataset_name": "rewrite-quality/v1",
                "dataset_compatibility_version": "sha256:test",
                "project": "rewrite-quality",
                "project_version": "v1",
                "prompt_version": "v1",
                "evaluator_set_id": "clarity:v1",
            },
        }
    )
    langfuse.scores["candidate-1"] = [
        {
            "id": "score-1",
            "name": "clarity",
            "trace_id": "trace-1",
            "score": 0.8,
            "source": "EVAL",
        }
    ]
    langfuse.annotation_queue_items.append(
        {
            "queue_id": "queue-1",
            "trace_id": "trace-1",
            "object_id": "trace-1",
            "status": "COMPLETED",
            "scores": [{"name": "clarity", "value": 0.6}],
        }
    )

    result = ExperimentRunner(langfuse_gateway=langfuse).calibration_capture(
        Path("configs/projects/rewrite_quality.yaml"),
        "candidate-1",
        output_dir=tmp_path,
    )

    assert result.row_count == 1
    assert result.paired_count == 1
    assert result.pending_count == 0
    payload = json.loads(result.output_path.read_text(encoding="utf-8"))
    assert payload[0]["human_score"] == 0.6
    assert payload[0]["human_score_source"] == "ANNOTATION"


def test_calibration_capture_uses_completed_annotation_queue_items_as_primary_cohort(
    tmp_path: Path,
) -> None:
    langfuse = DefaultLangfuseGateway()
    langfuse.annotation_queues["queue-1"] = {"id": "queue-1", "name": "Reviews"}
    langfuse.traces.extend(
        [
            {
                "trace_id": "sampled-trace",
                "run_id": "candidate-1",
                "input": "Source 1",
                "output": "Candidate 1",
                "metadata": {
                    "dataset_item_id": "1",
                    "dataset_name": "rewrite-quality/v1",
                    "dataset_compatibility_version": "sha256:test",
                    "project": "rewrite-quality",
                    "project_version": "v1",
                    "prompt_version": "v1",
                    "evaluator_set_id": "clarity:v1",
                },
            },
            {
                "trace_id": "annotated-trace",
                "run_id": "candidate-1",
                "input": "Source 2",
                "output": "Candidate 2",
                "metadata": {
                    "dataset_item_id": "2",
                    "dataset_name": "rewrite-quality/v1",
                    "dataset_compatibility_version": "sha256:test",
                    "project": "rewrite-quality",
                    "project_version": "v1",
                    "prompt_version": "v1",
                    "evaluator_set_id": "clarity:v1",
                },
            },
        ]
    )
    langfuse.scores["candidate-1"] = [
        {
            "id": "score-1",
            "name": "clarity",
            "trace_id": "sampled-trace",
            "score": 0.8,
            "source": "EVAL",
        },
        {
            "id": "score-2",
            "name": "clarity",
            "trace_id": "annotated-trace",
            "score": 0.4,
            "source": "EVAL",
        },
    ]
    langfuse.annotation_queue_items.append(
        {
            "queue_id": "queue-1",
            "trace_id": "annotated-trace",
            "object_id": "annotated-trace",
            "status": "COMPLETED",
            "scores": [{"name": "clarity", "value": 0.6}],
        }
    )

    result = ExperimentRunner(langfuse_gateway=langfuse).calibration_capture(
        Path("configs/projects/rewrite_quality.yaml"),
        "candidate-1",
        output_dir=tmp_path,
    )

    assert result.row_count == 1
    assert result.paired_count == 1
    assert result.pending_count == 0
    payload = json.loads(result.output_path.read_text(encoding="utf-8"))
    by_trace = {record["trace_id"]: record for record in payload}
    assert set(by_trace) == {"annotated-trace"}
    assert by_trace["annotated-trace"]["selection_reason"] == "annotated_queue_item"
    assert by_trace["annotated-trace"]["selection_bucket"] == "completed_annotation"
    assert by_trace["annotated-trace"]["human_score"] == 0.6


def test_calibration_capture_preserves_existing_richer_snapshot_on_degraded_capture(
    tmp_path: Path,
) -> None:
    output_path = tmp_path / "candidate-1.json"
    output_path.write_text(
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
                }
            ]
        ),
        encoding="utf-8",
    )
    langfuse = DefaultLangfuseGateway(
        traces=[
            {
                "trace_id": "trace-1",
                "run_id": "candidate-1",
                "metadata": {
                    "dataset_item_id": "1",
                    "dataset_name": "rewrite-quality/v1",
                    "dataset_compatibility_version": "sha256:test",
                },
            }
        ],
    )

    result = ExperimentRunner(langfuse_gateway=langfuse).calibration_capture(
        Path("configs/projects/rewrite_quality.yaml"),
        "candidate-1",
        output_dir=tmp_path,
    )

    assert result.row_count == 1
    assert result.paired_count == 1
    assert "preserved existing calibration snapshot" in result.warnings[0]
    payload = json.loads(output_path.read_text(encoding="utf-8"))
    assert payload[0]["human_score"] == 0.6


def test_calibration_capture_falls_back_to_existing_export_when_live_scores_missing(
    tmp_path: Path,
) -> None:
    project_path = Path("configs/projects/rewrite_quality.yaml").resolve()
    (tmp_path / "candidate-1.csv").write_text(
        "\n".join(
            [
                "trace_id,run_id,item_id,dataset_name,dataset_version,project,project_version,prompt_version,evaluator_set_id,error,input,output,score_clarity,score_clarity_comment",
                "trace-1,candidate-1,1,rewrite-quality/v1,sha256:test,rewrite-quality,v1,v1,clarity:v1,,Source 1,Candidate 1,0.8,judge",
                "trace-2,candidate-1,2,rewrite-quality/v1,sha256:test,rewrite-quality,v1,v1,clarity:v1,,Source 2,Candidate 2,0.4,judge",
            ]
        ),
        encoding="utf-8",
    )
    langfuse = DefaultLangfuseGateway(
        traces=[
            {
                "trace_id": "trace-1",
                "run_id": "candidate-1",
                "metadata": {
                    "dataset_item_id": "1",
                    "dataset_name": "rewrite-quality/v1",
                    "dataset_compatibility_version": "sha256:test",
                },
            }
        ],
    )

    result = ExperimentRunner(langfuse_gateway=langfuse).calibration_capture(
        project_path,
        "candidate-1",
        output_dir=tmp_path / "calibration",
    )

    assert result.row_count == 1
    assert result.pending_count == 1
    assert any("existing run export" in warning for warning in result.warnings)
    payload = json.loads(result.output_path.read_text(encoding="utf-8"))
    assert payload[0]["automated_score"] == 0.8
