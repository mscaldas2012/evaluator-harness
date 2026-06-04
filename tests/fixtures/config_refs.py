from __future__ import annotations

from evaluator_harness.config import ProjectConfig


def assert_same_evaluation_config(left: ProjectConfig, right: ProjectConfig) -> None:
    assert [evaluator.model_dump(mode="json") for evaluator in left.evaluators] == [
        evaluator.model_dump(mode="json") for evaluator in right.evaluators
    ]
    assert left.judge_setup.model_dump(mode="json") == right.judge_setup.model_dump(mode="json")
    assert left.human_review.model_dump(mode="json") == right.human_review.model_dump(mode="json")
