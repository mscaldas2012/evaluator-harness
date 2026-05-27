from __future__ import annotations

import pytest

from evaluator_harness.config import load_project_config
from evaluator_harness.errors import ConfigError
from evaluator_harness.evaluators import validate_judge_result_contract


def test_valid_judge_result_example_matches_contract() -> None:
    evaluator = load_project_config("configs/projects/rewrite_quality.yaml").evaluators[0]

    validate_judge_result_contract(
        evaluator,
        example={"reasoning": "clear", "score": 0.8, "confidence": 0.9},
    )


def test_rejects_judge_result_example_score_outside_range() -> None:
    evaluator = load_project_config("configs/projects/rewrite_quality.yaml").evaluators[0]

    with pytest.raises(ConfigError, match="outside configured score range"):
        validate_judge_result_contract(
            evaluator,
            example={"reasoning": "clear", "score": 2.0, "confidence": 0.9},
        )


def test_rejects_judge_result_example_missing_required_fields() -> None:
    evaluator = load_project_config("configs/projects/rewrite_quality.yaml").evaluators[0]

    with pytest.raises(ConfigError, match="missing fields"):
        validate_judge_result_contract(evaluator, example={"score": 0.5})
