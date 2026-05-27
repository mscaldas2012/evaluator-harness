from __future__ import annotations

from evaluator_harness.config import load_project_config
from evaluator_harness.evaluators import sanitized_judge_input_package


def test_blind_judge_input_package_excludes_provider_and_model_identity() -> None:
    config = load_project_config("configs/projects/rewrite_quality.yaml")
    evaluator = config.evaluators[0]

    package = sanitized_judge_input_package(
        evaluator=evaluator,
        input="source",
        output="candidate",
        baseline_output="baseline",
        metadata={"provider": "openai", "model": "gpt-5"},
    )

    assert package["metadata"]["evaluator_name"] == "clarity"
    assert "provider" not in package["metadata"]
    assert "model" not in package["metadata"]
    assert package["anonymous_labels"]["output"] == "Output A"


def test_non_blind_judge_input_package_can_include_identity_metadata() -> None:
    config = load_project_config("configs/projects/rewrite_quality.yaml")
    evaluator = config.evaluators[0].model_copy(
        update={
            "blind": False,
            "non_blind_reason": "Provider-specific diagnostic",
        }
    )

    package = sanitized_judge_input_package(
        evaluator=evaluator,
        input="source",
        output="candidate",
        metadata={"provider": "openai", "model": "gpt-5"},
    )

    assert package["metadata"]["provider"] == "openai"
    assert package["metadata"]["model"] == "gpt-5"
