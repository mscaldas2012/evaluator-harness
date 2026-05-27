from __future__ import annotations

from pathlib import Path

import pytest

from evaluator_harness.config import load_project_config, validate_project_config
from evaluator_harness.errors import ConfigError


def test_validates_prompt_paths_versions_modes_and_variables() -> None:
    config = load_project_config(Path("configs/projects/rewrite_quality.yaml"))

    validate_project_config(config)


def test_rejects_invalid_score_config_prefix(tmp_path: Path) -> None:
    project = _valid_project_yaml(score_config_prefix="bad prefix")
    path = tmp_path / "project.yaml"
    path.write_text(project, encoding="utf-8")

    with pytest.raises(ConfigError, match="score_config_prefix"):
        load_project_config(path)


def test_rejects_numeric_score_without_bounds(tmp_path: Path) -> None:
    project = _valid_project_yaml(score_block="name: clarity\n      data_type: NUMERIC")
    path = tmp_path / "project.yaml"
    path.write_text(project, encoding="utf-8")

    with pytest.raises(ConfigError, match="Numeric score"):
        load_project_config(path)


def test_rejects_user_owned_score_config_without_id(tmp_path: Path) -> None:
    project = _valid_project_yaml(
        score_block="""
name: clarity
      managed_by_harness: false
      data_type: NUMERIC
      min_value: 0
      max_value: 1
""".strip()
    )
    path = tmp_path / "project.yaml"
    path.write_text(project, encoding="utf-8")

    with pytest.raises(ConfigError, match="langfuse_score_config_id"):
        load_project_config(path)


def test_rejects_candidate_evaluator_without_baseline_output(tmp_path: Path) -> None:
    project = _valid_project_yaml(modes="[candidate]", variables="[input, output]")
    path = tmp_path / "project.yaml"
    path.write_text(project, encoding="utf-8")

    config = load_project_config(path)
    with pytest.raises(ConfigError, match="baseline_output"):
        validate_project_config(config)


def _valid_project_yaml(
    *,
    score_config_prefix: str = "eh_test_",
    score_block: str = "name: clarity\n      data_type: NUMERIC\n      min_value: 0\n      max_value: 1",
    modes: str = "[baseline, candidate]",
    variables: str = "[input, output, baseline_output, ground_truth]",
) -> str:
    return f"""
project:
  name: test-project
  version: v1
  score_config_prefix: {score_config_prefix}
dataset:
  kind: local_csv
  path: datasets/rewrite_quality.csv
task_prompt:
  path: prompts/rewrite_quality/task_prompt.md
  version: v1
baseline:
  name: baseline
  provider: openai_compatible
  auth_mode: api_key
  model: gpt-4.1
  parameters:
    temperature: 0.2
candidates:
  - name: candidate
    provider: ollama
    auth_mode: none
    model: llama3
    parameters:
      temperature: 0.2
evaluators:
  - name: clarity
    type: llm_as_judge
    version: v1
    prompt_path: prompts/rewrite_quality/evaluators/clarity.md
    score:
      {score_block}
    modes: {modes}
    variables: {variables}
""".strip()
