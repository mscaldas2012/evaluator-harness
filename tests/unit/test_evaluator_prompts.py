from __future__ import annotations

import pytest

from evaluator_harness.evaluators import (
    assert_prompt_is_single_dimension,
    load_judge_prompt,
)
from evaluator_harness.errors import ConfigError


def test_loads_judge_prompt_text() -> None:
    prompt = load_judge_prompt("tests/fixtures/prompts/valid_clarity_judge.md")

    assert "clarity" in prompt.text
    assert prompt.path.name == "valid_clarity_judge.md"


def test_rejects_multi_dimension_prompt() -> None:
    prompt = load_judge_prompt("tests/fixtures/prompts/multi_dimension_judge.md")

    with pytest.raises(ConfigError, match="one dimension"):
        assert_prompt_is_single_dimension(prompt, dimension="clarity")
