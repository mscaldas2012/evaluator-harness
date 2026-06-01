from __future__ import annotations

from pathlib import Path

from evaluator_harness.config import load_project_config
from evaluator_harness.langfuse_client import LangfuseClient
from evaluator_harness.prompt_sync import (
    discover_prompt_artifacts,
    sync_project_prompts,
)


def _config():
    return load_project_config("tests/fixtures/projects/valid_prompt_sync.yaml")


def test_discover_prompt_artifacts_includes_task_and_judge_prompts() -> None:
    artifacts = discover_prompt_artifacts(_config())

    assert [(artifact.artifact_type, artifact.artifact_name) for artifact in artifacts] == [
        ("task", "task_prompt"),
        ("evaluator", "clarity"),
    ]
    assert artifacts[0].prompt_shape == "chat"
    assert artifacts[0].roles == ["system", "user"]
    assert artifacts[0].content_identity.startswith("sha256:")
    assert artifacts[1].prompt_shape == "text"


def test_sync_project_prompts_creates_missing_text_and_chat_versions(tmp_path: Path) -> None:
    langfuse = LangfuseClient()

    result = sync_project_prompts(
        _config(),
        langfuse,
        binding_path=tmp_path / "prompt-sync.yaml",
    )

    assert result.created_count == 2
    assert {item.status for item in result.items} == {"created"}
    assert len(langfuse.prompt_versions) == 2
    assert (tmp_path / "prompt-sync.yaml").exists()


def test_sync_project_prompts_reuses_unchanged_versions(tmp_path: Path) -> None:
    langfuse = LangfuseClient()
    binding_path = tmp_path / "prompt-sync.yaml"

    first = sync_project_prompts(_config(), langfuse, binding_path=binding_path)
    second = sync_project_prompts(_config(), langfuse, binding_path=binding_path)

    assert first.created_count == 2
    assert second.reused_count == 2
    assert sum(len(versions) for versions in langfuse.prompt_versions.values()) == 2


def test_sync_project_prompts_conflicts_on_same_version_changed_content(tmp_path: Path) -> None:
    config = _config()
    artifact = discover_prompt_artifacts(config)[0]
    langfuse = LangfuseClient(
        prompt_versions={
            artifact.managed_name: [
                {
                    "name": artifact.managed_name,
                    "version": 1,
                    "labels": artifact.labels,
                    "config": {
                        "managed_by": "evaluator_harness",
                        "artifact_version": artifact.artifact_version,
                        "content_identity": "sha256:different",
                    },
                }
            ]
        }
    )

    result = sync_project_prompts(
        config,
        langfuse,
        binding_path=tmp_path / "prompt-sync.yaml",
    )

    assert result.conflict_count == 1
    assert "Bump" in str(result.items[0].remediation)


def test_dry_run_project_prompts_does_not_create_or_write_bindings(tmp_path: Path) -> None:
    langfuse = LangfuseClient()
    binding_path = tmp_path / "prompt-sync.yaml"

    result = sync_project_prompts(
        _config(),
        langfuse,
        dry_run=True,
        binding_path=binding_path,
    )

    assert result.mode == "dry-run"
    assert result.total_count == 2
    assert langfuse.prompt_versions == {}
    assert not binding_path.exists()


def test_dry_run_reports_user_owned_remote_prompt_conflict(tmp_path: Path) -> None:
    config = _config()
    artifact = discover_prompt_artifacts(config)[0]
    langfuse = LangfuseClient(
        prompt_versions={
            artifact.managed_name: [
                {
                    "name": artifact.managed_name,
                    "version": 1,
                    "labels": artifact.labels,
                    "config": {"owner": "human"},
                }
            ]
        }
    )

    result = sync_project_prompts(
        config,
        langfuse,
        dry_run=True,
        binding_path=tmp_path / "prompt-sync.yaml",
    )

    assert result.conflict_count == 1
    assert "ownership" in result.items[0].message
