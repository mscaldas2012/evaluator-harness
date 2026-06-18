from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner

from evaluator_harness.cli import app
from evaluator_harness.config import LiveSettings
from evaluator_harness.langfuse_client import LangfuseClient


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


def test_cli_project_command_resolves_project_env_before_credentials(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("EVALUATOR_HARNESS_LIVE", "1")
    for name in (
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
        "LANGFUSE_HOST",
        "LANGFUSE_BASE_URL",
    ):
        monkeypatch.delenv(name, raising=False)
    project_path = _write_project_workspace(tmp_path)
    workspace = Path.cwd()
    (workspace / ".env").write_text(
        "\n".join(
            [
                "LANGFUSE_PUBLIC_KEY=root-public",
                "LANGFUSE_SECRET_KEY=root-secret",
                "LANGFUSE_HOST=https://root-langfuse.test",
            ]
        ),
        encoding="utf-8",
    )
    (workspace / ".env.project-env-files").write_text(
        "\n".join(
            [
                "LANGFUSE_PUBLIC_KEY=project-public",
                "LANGFUSE_SECRET_KEY=project-secret",
                "LANGFUSE_HOST=https://project-langfuse.test",
            ]
        ),
        encoding="utf-8",
    )
    seen: list[LiveSettings] = []

    def fake_from_env(cls):
        settings = LiveSettings.from_env(load_file=False)
        seen.append(settings)
        settings.require_langfuse()
        return LangfuseClient(settings=settings)

    monkeypatch.setattr(LangfuseClient, "from_env", classmethod(fake_from_env))

    result = CliRunner().invoke(
        app,
        ["sync-dataset", "--project", str(project_path), "--dry-run"],
    )

    assert result.exit_code == 0
    assert seen[0].langfuse_public_key == "project-public"
    assert seen[0].langfuse_secret_key == "project-secret"
    assert seen[0].langfuse_host == "https://project-langfuse.test"


def test_cli_missing_credentials_report_names_not_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("EVALUATOR_HARNESS_LIVE", "1")
    for name in (
        "LANGFUSE_PUBLIC_KEY",
        "LANGFUSE_SECRET_KEY",
        "LANGFUSE_HOST",
        "LANGFUSE_BASE_URL",
    ):
        monkeypatch.delenv(name, raising=False)
    project_path = _write_project_workspace(tmp_path)
    (Path.cwd() / ".env.project-env-files").write_text(
        "LANGFUSE_PUBLIC_KEY=project-public-secret\n",
        encoding="utf-8",
    )

    result = CliRunner().invoke(
        app,
        ["sync-dataset", "--project", str(project_path), "--dry-run"],
    )

    assert result.exit_code == 1
    assert "LANGFUSE_SECRET_KEY" in result.stdout
    assert "LANGFUSE_HOST" in result.stdout
    assert "project-public-secret" not in result.stdout
