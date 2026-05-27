from __future__ import annotations

from evaluator_harness.config import EvaluatorRunType, EvaluatorTarget, load_project_config
from evaluator_harness.evaluators import build_filter_profile


def test_filter_profile_uses_model_output_role_and_project_metadata() -> None:
    config = load_project_config("configs/projects/rewrite_quality.yaml")
    evaluator = config.evaluators[0]

    profile = build_filter_profile(config, evaluator)

    assert profile.target == EvaluatorTarget.OBSERVATION
    assert profile.observation_role == "model_output"
    assert profile.project == "rewrite-quality"
    assert profile.project_version == "v1"
    assert profile.evaluator_set_id == "clarity:v1"
    assert profile.run_types == [
        EvaluatorRunType.BASELINE,
        EvaluatorRunType.CANDIDATE,
    ]
