from __future__ import annotations

import csv
from pathlib import Path

from evaluator_harness.exports import export_summary
from evaluator_harness.langfuse_default_gateway import DefaultLangfuseGateway
from evaluator_harness.runner import ExperimentRunner


def test_export_summary_writes_trace_rows_with_score_columns(tmp_path: Path) -> None:
    traces = [
        {
            "trace_id": "trace-1",
            "run_id": "candidate-1",
            "input": "Source",
            "output": "Output",
            "error": None,
            "timestamp": "2026-05-26T00:00:00+00:00",
            "metadata": {
                "dataset_item_id": "1",
                "project": "rewrite-quality",
                "project_version": "v1",
                "scenario_group": "dfe",
                "scenario_name": "general_public",
                "scenario_display_name": "General public",
                "dataset_name": "rewrite-quality/v1",
                "dataset_version": "latest",
                "prompt_version": "v1",
                "prompt_shape": "messages",
                "prompt_roles": ["system", "user"],
                "prompt_artifact_type": "task",
                "prompt_artifact_name": "task_prompt",
                "prompt_local_path": "prompts/task.md",
                "prompt_content_identity": "sha256:abc",
                "prompt_managed_name": "EH_project_v1_prompt_task_task_prompt_v1",
                "langfuse_prompt_name": "EH_project_v1_prompt_task_task_prompt_v1",
                "langfuse_prompt_version": 1,
                "langfuse_prompt_labels": ["project", "v1"],
                "evaluator_set_id": "clarity:v1",
                "provider": "ollama",
                "model": "llama3",
                "model_name": "llama3-local",
                "temperature": 0.2,
                "generation_parameter_hash": "params-hash",
                "item_comparison_session_id": "eh-item-session",
                "parameter_identity": {"temperature": 0.2, "top_p": 1.0},
                "variant_identity": {
                    "candidate": "llama3-local",
                    "generation_parameter_hash": "params-hash",
                },
                "latency_ms": 123,
                "input_tokens": None,
                "output_tokens": None,
                "cost_usd": None,
                "baseline_reference": {"baseline_run_id": "baseline-1"},
            },
        }
    ]
    output_path = tmp_path / "summary.csv"

    scores = [
        {
            "trace_id": "trace-1",
            "name": "EH DFE active voice",
            "value": 0.75,
            "comment": "Mostly active.",
        },
        {
            "trace_id": "trace-1",
            "name": "lists_preserved",
            "score": 1,
        },
    ]

    result = export_summary(traces, output_path, scores=scores)

    csv_text = output_path.read_text(encoding="utf-8")
    assert result.row_count == 1
    assert result.output_path == output_path
    assert "trace_id,run_id,item_id,project" in csv_text
    assert "trace-1,candidate-1,1,rewrite-quality" in csv_text
    assert "scenario_group" in csv_text
    assert "general_public" in csv_text
    assert "General public" in csv_text
    assert "generation_parameter_hash" in csv_text
    assert "item_comparison_session_id" in csv_text
    assert "eh-item-session" in csv_text
    assert "prompt_shape" in csv_text
    assert "prompt_content_identity" in csv_text
    assert "sha256:abc" in csv_text
    assert "EH_project_v1_prompt_task_task_prompt_v1" in csv_text
    assert "messages" in csv_text
    assert '[""system"", ""user""]' in csv_text
    assert "params-hash" in csv_text
    assert '""temperature"": 0.2' in csv_text
    assert "score_eh_dfe_active_voice" in csv_text
    assert "score_eh_dfe_active_voice_comment" in csv_text
    assert "score_lists_preserved" in csv_text
    assert "0.75" in csv_text
    assert "Mostly active." in csv_text


def test_runner_export_writes_csv_under_project_report_folder() -> None:
    client = DefaultLangfuseGateway(
        traces=[
            {
                "trace_id": "trace-1",
                "run_id": "baseline-123",
                "metadata": {
                    "dataset_item_id": "1",
                    "project": "rewrite-quality",
                },
            }
        ],
    )
    runner = ExperimentRunner(langfuse_gateway=client)

    result = runner.export(
        Path("configs/projects/rewrite_quality.yaml"),
        "baseline-123",
        "csv",
    )

    assert result.output_path == Path("reports/rewrite-quality/baseline-123.csv")
    assert result.output_path.exists()


def test_export_summary_leaves_missing_scores_empty(tmp_path: Path) -> None:
    traces = [
        {
            "trace_id": "trace-1",
            "run_id": "baseline-1",
            "metadata": {"dataset_item_id": "1"},
        },
        {
            "trace_id": "trace-2",
            "run_id": "baseline-1",
            "metadata": {"dataset_item_id": "2"},
        },
    ]
    output_path = tmp_path / "summary.csv"

    export_summary(
        traces,
        output_path,
        scores=[{"trace_id": "trace-1", "name": "clarity", "value": 1}],
    )

    rows = output_path.read_text(encoding="utf-8").splitlines()
    assert "score_clarity" in rows[0]
    assert "trace-1,baseline-1,1" in rows[1]
    assert "trace-2,baseline-1,2" in rows[2]


def test_fetch_scores_filters_fake_scores_by_trace_id() -> None:
    client = DefaultLangfuseGateway(
        scores={
            "baseline-1": [
                {"trace_id": "trace-1", "name": "clarity", "score": 1},
                {"trace_id": "trace-2", "name": "clarity", "score": 0},
            ]
        }
    )

    scores = client.fetch_scores("baseline-1", trace_ids=["trace-2"])

    assert scores == [{"trace_id": "trace-2", "name": "clarity", "score": 0}]


def test_export_summary_uses_latest_duplicate_score(tmp_path: Path) -> None:
    traces = [
        {
            "trace_id": "trace-1",
            "run_id": "baseline-1",
            "metadata": {"dataset_item_id": "1"},
        }
    ]
    output_path = tmp_path / "summary.csv"

    export_summary(
        traces,
        output_path,
        scores=[
            {
                "trace_id": "trace-1",
                "name": "clarity",
                "value": 0,
                "timestamp": "2026-05-29T10:00:00Z",
            },
            {
                "trace_id": "trace-1",
                "name": "clarity",
                "value": 1,
                "timestamp": "2026-05-29T11:00:00Z",
            },
        ],
    )

    rows = list(csv.DictReader(output_path.open(encoding="utf-8")))
    assert rows[0]["score_clarity"] == "1"


def test_export_summary_groups_scores_by_trace_id_not_session_id(tmp_path: Path) -> None:
    traces = [
        {
            "trace_id": "trace-1",
            "run_id": "candidate-1",
            "metadata": {
                "dataset_item_id": "1",
                "item_comparison_session_id": "shared-session",
            },
        },
        {
            "trace_id": "trace-2",
            "run_id": "candidate-1",
            "metadata": {
                "dataset_item_id": "2",
                "item_comparison_session_id": "shared-session",
            },
        },
    ]
    output_path = tmp_path / "summary.csv"

    export_summary(
        traces,
        output_path,
        scores=[{"trace_id": "trace-2", "name": "clarity", "value": 1}],
    )

    rows = list(csv.DictReader(output_path.open(encoding="utf-8")))
    assert rows[0]["score_clarity"] == ""
    assert rows[1]["score_clarity"] == "1"
