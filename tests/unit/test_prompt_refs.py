from __future__ import annotations

from pathlib import Path

import pytest

from evaluator_harness.config import load_project_config, validate_project_config
from evaluator_harness.errors import ConfigError
from evaluator_harness.runner import prompt_identity


def test_validates_prompt_paths_versions_modes_and_variables() -> None:
    config = load_project_config(Path("configs/projects/rewrite_quality.yaml"))

    validate_project_config(config)


def test_prompt_identity_includes_version_path_and_content_hash() -> None:
    config = load_project_config(
        Path("tests/fixtures/projects/valid_prompt_variant_candidate.yaml")
    )

    identity = prompt_identity(config.candidates[0].task_prompt)

    assert identity["path"] == "tests/fixtures/prompts/rewrite_quality_task_prompt_v2.md"
    assert identity["version"] == "v2"
    assert len(identity["content_hash"]) == 64


def test_prompt_identity_changes_when_prompt_content_changes(tmp_path: Path) -> None:
    first = tmp_path / "first.md"
    second = tmp_path / "second.md"
    first.write_text("Rewrite:\n{{input}}\n", encoding="utf-8")
    second.write_text("Rewrite clearly:\n{{input}}\n", encoding="utf-8")

    from evaluator_harness.config import PromptRef

    first_identity = prompt_identity(
        PromptRef(path=first, version="v2", template_variables=["input"])
    )
    second_identity = prompt_identity(
        PromptRef(path=second, version="v2", template_variables=["input"])
    )

    assert first_identity["content_hash"] != second_identity["content_hash"]


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
  provider: dry_run
  auth_mode: none
  model: dry-run
  parameters:
    temperature: 0.0
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
