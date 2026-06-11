from __future__ import annotations

import os
from pathlib import Path

import pytest

from evaluator_harness.runner import ExperimentRunner


def _write_project_workspace(tmp_path: Path, *, project_name: str = "project-env-files") -> Path:
    tmp_path = Path.cwd()
    dataset_path = tmp_path / "dataset.csv"
    dataset_path.write_text("input\nhello\n", encoding="utf-8")
    prompt_path = tmp_path / "prompt.md"
    prompt_path.write_text("Rewrite: {{input}}\n", encoding="utf-8")
    project_path = tmp_path / "project.yaml"
    project_path.write_text(
        f"""
project:
  name: {project_name}
  description: Project env fixture.
  version: v1
  score_config_prefix: eh_project_env_
dataset:
  kind: local_csv
  path: {dataset_path.as_posix()}
  langfuse_dataset_name: {project_name}/v1
  item_id_strategy: explicit_or_hash
judge_setup:
  default_judge_model: fixture-judge
task_prompt:
  path: {prompt_path.as_posix()}
  version: v1
  template_variables:
    - input
baseline:
  name: dry-run-baseline
  provider: dry_run
  auth_mode: none
  model: dry-run
  parameters:
    temperature: 0.0
    top_p: 1.0
    max_tokens: 256
candidates:
  - name: dry-run-candidate
    provider: dry_run
    auth_mode: none
    model: dry-run
    parameters:
      temperature: 0.0
      top_p: 1.0
      max_tokens: 256
evaluators:
  - name: fixture_quality
    type: llm_as_judge
    version: v1
    dimension: fixture_quality
    source_type: custom
    target: observation
    target_observation_role: model_output
    run_types:
      - baseline
      - candidate
    mode: baseline_comparison
    blind: true
    prompt_path: {prompt_path.as_posix()}
    prompt_version: v1
    sampling_percent:
    historical_backfill:
    score:
      name: fixture_quality
      managed_by_harness: true
      data_type: NUMERIC
      min_value: 0
      max_value: 1
      allowed_score_sources:
        - llm_judge
        - human_annotation
    modes:
      - baseline
      - candidate
    required_inputs:
      - input
      - output
      - baseline_output
    variables:
      - input
      - output
      - baseline_output
    output_schema:
      reasoning: string
      score:
        type: number
        minimum: 0
        maximum: 1
      confidence:
        type: number
        minimum: 0
        maximum: 1
""".strip(),
        encoding="utf-8",
    )
    return project_path


def test_project_env_overrides_root_env_for_project_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PROJECT_ENV_SHARED", raising=False)
    project_path = _write_project_workspace(tmp_path)
    workspace = Path.cwd()
    (workspace / ".env").write_text("PROJECT_ENV_SHARED=root-shared\n", encoding="utf-8")
    (workspace / ".env.project-env-files").write_text(
        "PROJECT_ENV_SHARED=project-shared\n",
        encoding="utf-8",
    )

    ExperimentRunner().validate_project(project_path)

    assert os.getenv("PROJECT_ENV_SHARED") == "project-shared"


def test_project_only_env_value_is_available_to_project_command(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PROJECT_ENV_PROJECT_ONLY", raising=False)
    project_path = _write_project_workspace(tmp_path)
    (Path.cwd() / ".env.project-env-files").write_text(
        "PROJECT_ENV_PROJECT_ONLY=project-only\n",
        encoding="utf-8",
    )

    ExperimentRunner().validate_project(project_path)

    assert os.getenv("PROJECT_ENV_PROJECT_ONLY") == "project-only"


def test_missing_project_env_file_falls_back_to_root_env(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PROJECT_ENV_ROOT_ONLY", raising=False)
    project_path = _write_project_workspace(tmp_path)
    (Path.cwd() / ".env").write_text("PROJECT_ENV_ROOT_ONLY=root-only\n", encoding="utf-8")

    ExperimentRunner().validate_project(project_path)

    assert os.getenv("PROJECT_ENV_ROOT_ONLY") == "root-only"


def test_malformed_project_env_lines_are_ignored(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("PROJECT_ENV_VALID", raising=False)
    monkeypatch.delenv("INVALID-NAME", raising=False)
    project_path = _write_project_workspace(tmp_path)
    (Path.cwd() / ".env.project-env-files").write_text(
        "PROJECT_ENV_VALID=valid\nINVALID-NAME=ignored\nMALFORMED LINE\n",
        encoding="utf-8",
    )

    ExperimentRunner().validate_project(project_path)

    assert os.getenv("PROJECT_ENV_VALID") == "valid"
    assert os.getenv("INVALID-NAME") is None
