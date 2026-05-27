from __future__ import annotations

from pathlib import Path

from evaluator_harness.exports import export_summary


def test_export_summary_writes_trace_rows_without_score_aggregation(tmp_path: Path) -> None:
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
                "dataset_name": "rewrite-quality/v1",
                "dataset_version": "latest",
                "prompt_version": "v1",
                "evaluator_set_id": "clarity:v1",
                "provider": "ollama",
                "model": "llama3",
                "model_name": "llama3-local",
                "temperature": 0.2,
                "latency_ms": 123,
                "input_tokens": None,
                "output_tokens": None,
                "cost_usd": None,
                "baseline_reference": {"baseline_run_id": "baseline-1"},
            },
        }
    ]
    output_path = tmp_path / "summary.csv"

    result = export_summary(traces, output_path)

    csv_text = output_path.read_text(encoding="utf-8")
    assert result.row_count == 1
    assert result.output_path == output_path
    assert "trace_id,run_id,item_id,project" in csv_text
    assert "trace-1,candidate-1,1,rewrite-quality" in csv_text
    assert "score" not in csv_text.lower()
