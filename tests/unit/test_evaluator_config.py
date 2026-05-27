from __future__ import annotations

from pathlib import Path

import pytest

from evaluator_harness.config import (
    EvaluatorMode,
    EvaluatorRunType,
    EvaluatorTarget,
    load_project_config,
    validate_project_config,
)
from evaluator_harness.errors import ConfigError


def test_valid_evaluator_config_parses_judge_fields() -> None:
    config = load_project_config("tests/fixtures/projects/valid_rewrite_quality.yaml")
    evaluator = config.evaluators[0]

    assert evaluator.dimension == "clarity"
    assert evaluator.target == EvaluatorTarget.OBSERVATION
    assert evaluator.target_observation_role == "model_output"
    assert evaluator.target_observation_name == "OpenAI-generation"
    assert evaluator.run_types == [
        EvaluatorRunType.BASELINE,
        EvaluatorRunType.CANDIDATE,
    ]
    assert evaluator.mode == EvaluatorMode.BASELINE_COMPARISON
    assert evaluator.blind is True
    assert evaluator.non_blind_reason is None
    assert evaluator.required_inputs == ["input", "output", "baseline_output"]
    assert evaluator.output_schema.score.minimum == 0
    assert evaluator.output_schema.score.maximum == 1
    assert evaluator.filter_profile.project == "rewrite-quality"


def test_blind_defaults_to_true_for_evaluator_config(tmp_path: Path) -> None:
    project = tmp_path / "project.yaml"
    project.write_text(
        Path("tests/fixtures/projects/valid_rewrite_quality.yaml")
        .read_text(encoding="utf-8")
        .replace("    blind: true\n", ""),
        encoding="utf-8",
    )

    config = load_project_config(project)

    assert config.evaluators[0].blind is True


@pytest.mark.parametrize(
    ("path", "message"),
    [
        ("tests/fixtures/projects/invalid_evaluator_missing_target.yaml", "target"),
        ("tests/fixtures/projects/invalid_evaluator_missing_output_schema.yaml", "output_schema"),
        ("tests/fixtures/projects/invalid_evaluator_broad_filter.yaml", "filter"),
    ],
)
def test_invalid_evaluator_configs_fail_validation(path: str, message: str) -> None:
    config = load_project_config(path)

    with pytest.raises(ConfigError, match=message):
        validate_project_config(config)


def test_rejects_invalid_run_type(tmp_path: Path) -> None:
    project = tmp_path / "project.yaml"
    project.write_text(
        Path("tests/fixtures/projects/valid_rewrite_quality.yaml")
        .read_text(encoding="utf-8")
        .replace("      - candidate\n", "      - experiment\n", 1),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="run_types"):
        load_project_config(project)


def test_rejects_non_blind_evaluator_without_reason(tmp_path: Path) -> None:
    project = tmp_path / "project.yaml"
    project.write_text(
        Path("tests/fixtures/projects/valid_rewrite_quality.yaml")
        .read_text(encoding="utf-8")
        .replace("    blind: true\n", "    blind: false\n"),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="non_blind_reason"):
        load_project_config(project)
