from __future__ import annotations

import pytest

from evaluator_harness.config import load_project_config
from evaluator_harness.evaluators import assert_blind_prompt, load_judge_prompt
from evaluator_harness.errors import ConfigError


def test_blind_evaluator_rejects_provider_identity_placeholders() -> None:
    config = load_project_config("configs/projects/rewrite_quality.yaml")
    evaluator = config.evaluators[0]
    prompt = load_judge_prompt("tests/fixtures/prompts/non_blind_judge.md")

    with pytest.raises(ConfigError, match="identity placeholders"):
        assert_blind_prompt(prompt, evaluator)


def test_non_blind_evaluator_allows_identity_placeholders() -> None:
    config = load_project_config("configs/projects/rewrite_quality.yaml")
    evaluator = config.evaluators[0].model_copy(
        update={
            "blind": False,
            "non_blind_reason": "Provider-specific schema compliance audit",
        }
    )
    prompt = load_judge_prompt("tests/fixtures/prompts/non_blind_judge.md")

    assert_blind_prompt(prompt, evaluator)
