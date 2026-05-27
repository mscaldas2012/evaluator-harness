from __future__ import annotations

from pathlib import Path

from evaluator_harness.langfuse_client import LangfuseClient
from evaluator_harness.runner import ExperimentRunner


def test_select_review_routes_configured_queue_items() -> None:
    langfuse = LangfuseClient()
    langfuse.traces.extend(
        [
            {
                "trace_id": "trace-1",
                "run_id": "candidate-1",
                "input": "Source 1",
                "output": "Candidate 1",
                "error": "provider timeout",
                "metadata": {
                    "dataset_item_id": "1",
                    "ground_truth": "Expected 1",
                    "baseline_reference": {"baseline_run_id": "baseline-1"},
                    "provider": "ollama",
                    "model": "llama3",
                },
            },
            {
                "trace_id": "trace-2",
                "run_id": "candidate-1",
                "input": "Source 2",
                "output": "Candidate 2",
                "metadata": {
                    "dataset_item_id": "2",
                    "ground_truth": "Expected 2",
                    "baseline_reference": {"baseline_run_id": "baseline-1"},
                },
            },
            {
                "trace_id": "trace-baseline-1",
                "run_id": "baseline-1",
                "output": "Baseline 1",
                "metadata": {"dataset_item_id": "1"},
            },
        ]
    )
    langfuse.scores["candidate-1"] = [{"trace_id": "trace-2", "score": 0.2, "confidence": 0.4}]

    result = ExperimentRunner(langfuse_client=langfuse).select_review(
        Path("configs/projects/rewrite_quality.yaml"),
        "candidate-1",
    )

    assert result.selected_count >= 1
    assert result.queued_count == result.selected_count
    assert result.queue_id == "annotation-queue-1"
    assert langfuse.annotation_queue_items[0]["baseline_output"] == "Baseline 1"
