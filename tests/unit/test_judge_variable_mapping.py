from __future__ import annotations

import pytest

from evaluator_harness.config import load_project_config
from evaluator_harness.errors import ConfigError
from evaluator_harness.langfuse_evaluator_setup import (
    build_variable_mapping,
    build_prompt_variable_mapping,
)


def test_variable_mapping_uses_langfuse_observation_and_trace_paths() -> None:
    evaluator = load_project_config(
        "tests/fixtures/projects/valid_rewrite_quality.yaml"
    ).evaluators[0]

    assert build_variable_mapping(evaluator) == {
        "input": "observation.input",
        "output": "observation.output",
        "baseline_output": "trace.metadata.baseline_output",
        "ground_truth": "trace.metadata.ground_truth",
    }


def test_missing_required_variable_mapping_blocks_setup() -> None:
    evaluator = load_project_config(
        "tests/fixtures/projects/valid_rewrite_quality.yaml"
    ).evaluators[0]
    evaluator.variables.remove("baseline_output")

    with pytest.raises(ConfigError, match="baseline_output"):
        build_variable_mapping(evaluator)


def test_prompt_variable_mapping_excludes_declared_variables_absent_from_prompt() -> None:
    evaluator = load_project_config(
        "configs/projects/rewrite_quality.yaml"
    ).evaluators[0]

    assert build_prompt_variable_mapping(evaluator) == {
        "input": "observation.input",
        "output": "observation.output",
        "ground_truth": "trace.metadata.ground_truth",
    }
