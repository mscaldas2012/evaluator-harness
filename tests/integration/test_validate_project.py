from __future__ import annotations

from pathlib import Path

from evaluator_harness.config import load_project_config
from evaluator_harness.runner import ExperimentRunner


def test_validates_sample_rewrite_project_without_model_calls() -> None:
    result = ExperimentRunner().validate_project(Path("configs/projects/rewrite_quality.yaml"))

    assert result.project_name == "rewrite-quality"
    assert result.dataset_kind == "local_csv"
    assert result.item_count == 2
    assert result.baseline_name == "gpt5.2-dgw-default"
    assert result.candidate_names == [
        "dry-run-candidate",
        "azure-mistral-large-3",
    ]
    assert result.evaluator_names == ["clarity/v1"]
    assert result.evaluator_targets == ["clarity=observation/model_output"]
    assert result.score_targets == ["clarity=eh_rewrite_quality_clarity"]


def test_rewrite_quality_judge_filter_does_not_depend_on_generation_name() -> None:
    config = load_project_config(Path("configs/projects/rewrite_quality.yaml"))

    filter_profile = config.evaluators[0].filter_profile
    assert config.evaluators[0].target_observation_name is None
    assert filter_profile is not None
    assert filter_profile.observation_name is None
    assert filter_profile.environment is None
