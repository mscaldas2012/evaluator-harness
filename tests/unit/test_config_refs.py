from __future__ import annotations

from pathlib import Path

import pytest

from evaluator_harness.config import ConfigError, load_project_config, validate_project_config
from tests.fixtures.config_refs import assert_same_evaluation_config


FIXTURES = Path("tests/fixtures/projects/config_refs")


def test_resolves_shared_evaluation_config() -> None:
    config = load_project_config(FIXTURES / "valid_shared_project.yaml")

    assert config.project.name == "config-ref-project"
    assert [evaluator.name for evaluator in config.evaluators] == ["clarity"]
    assert config.judge_setup.default_judge_model == "gpt-4.1"
    assert config.human_review.enabled is True
    validate_project_config(config)


def test_shared_evaluation_matches_equivalent_single_file_project() -> None:
    config = load_project_config(FIXTURES / "valid_shared_project.yaml")
    equivalent = load_project_config(FIXTURES / "equivalent_single_file_project.yaml")

    assert_same_evaluation_config(config, equivalent)


def test_config_refs_preserve_existing_single_file_configs() -> None:
    config = load_project_config(Path("tests/fixtures/projects/valid_prompt_sync.yaml"))

    assert config.project.name == "prompt-sync"
    assert [evaluator.name for evaluator in config.evaluators] == ["clarity"]
    validate_project_config(config)


def test_rejects_missing_shared_evaluation_config() -> None:
    with pytest.raises(ConfigError, match="config_refs\\.evaluation.*does_not_exist"):
        load_project_config(FIXTURES / "missing_shared_project.yaml")


def test_rejects_unreadable_shared_evaluation_config(tmp_path: Path) -> None:
    shared_dir = tmp_path / "shared-dir"
    shared_dir.mkdir()
    project = _project_with_config_ref(tmp_path, "shared-dir")

    with pytest.raises(ConfigError, match="config_refs\\.evaluation.*shared-dir"):
        load_project_config(project)


def test_rejects_invalid_shared_evaluation_yaml(tmp_path: Path) -> None:
    shared = tmp_path / "shared.yaml"
    shared.write_text("evaluators: [", encoding="utf-8")
    project = _project_with_config_ref(tmp_path, "shared.yaml")

    with pytest.raises(ConfigError, match="Invalid YAML.*config_refs\\.evaluation"):
        load_project_config(project)


@pytest.mark.parametrize(
    "section",
    [
        "project",
        "dataset",
        "task_prompt",
        "baseline",
        "candidates",
        "config_refs",
        "scenario",
    ],
)
def test_rejects_disallowed_shared_evaluation_sections(
    tmp_path: Path,
    section: str,
) -> None:
    shared = tmp_path / "shared.yaml"
    shared.write_text(
        f"""
evaluators: []
{section}: {{}}
""".strip(),
        encoding="utf-8",
    )
    project = _project_with_config_ref(tmp_path, "shared.yaml")

    with pytest.raises(ConfigError, match=f"disallowed.*{section}"):
        load_project_config(project)


def test_rejects_disallowed_shared_evaluation_fixture() -> None:
    with pytest.raises(ConfigError, match="disallowed.*dataset"):
        load_project_config(FIXTURES / "disallowed_shared_project.yaml")


@pytest.mark.parametrize("section", ["evaluators", "judge_setup", "human_review"])
def test_rejects_local_shared_evaluation_conflicts(
    tmp_path: Path,
    section: str,
) -> None:
    project = _project_with_config_ref(tmp_path, "shared.yaml", extra_section=section)
    (tmp_path / "shared.yaml").write_text(
        """
judge_setup:
  default_judge_model: gpt-4.1
evaluators: []
human_review:
  enabled: false
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match=f"conflict.*{section}"):
        load_project_config(project)


def test_rejects_local_shared_human_review_conflict_fixture() -> None:
    with pytest.raises(ConfigError, match="conflict.*human_review"):
        load_project_config(FIXTURES / "conflicting_project.yaml")


def _project_with_config_ref(
    directory: Path,
    ref: str,
    *,
    extra_section: str | None = None,
) -> Path:
    project = directory / "project.yaml"
    extra = ""
    if extra_section == "evaluators":
        extra = "evaluators: []\n"
    elif extra_section == "judge_setup":
        extra = "judge_setup: {}\n"
    elif extra_section == "human_review":
        extra = "human_review:\n  enabled: true\n"
    project.write_text(
        f"""
project:
  name: config-ref-test
  version: v1
  score_config_prefix: eh_config_ref_test_
config_refs:
  evaluation: {ref}
dataset:
  kind: local_csv
  path: tests/fixtures/datasets/prompt_variables.csv
task_prompt:
  path: tests/fixtures/prompts/prompt_sync_task.md
  version: v1
  template_variables:
    - dataset.input
baseline:
  name: dry-run-baseline
  provider: dry_run
  auth_mode: none
  model: dry-run
  parameters:
    temperature: 0.0
candidates:
  - name: dry-run-candidate
    provider: dry_run
    auth_mode: none
    model: dry-run
    parameters:
      temperature: 0.0
{extra}
""".strip(),
        encoding="utf-8",
    )
    return project
