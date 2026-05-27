from __future__ import annotations

from pathlib import Path

from evaluator_harness.runner import ExperimentRunner


def test_validates_sample_rewrite_project_without_model_calls() -> None:
    result = ExperimentRunner().validate_project(Path("configs/projects/rewrite_quality.yaml"))

    assert result.project_name == "rewrite-quality"
    assert result.dataset_kind == "local_csv"
    assert result.item_count == 2
    assert result.baseline_name == "gpt5.2-dgw-default"
    assert result.candidate_names == [
        "llama3-local",
        "llama3-local-temp-high",
        "dry-run-candidate",
    ]
    assert result.evaluator_names == ["clarity/v1"]
