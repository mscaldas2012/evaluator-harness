from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

import evaluator_harness.cli as cli
from evaluator_harness.cli import app
from evaluator_harness.prompt_sync import PromptSyncReport, PromptSyncStatus, discover_prompt_artifacts
from evaluator_harness.config import load_project_config


def _report(mode: str = "apply") -> PromptSyncReport:
    config = load_project_config("tests/fixtures/projects/valid_prompt_sync.yaml")
    artifact = discover_prompt_artifacts(config)[0]
    return PromptSyncReport(
        project="prompt-sync",
        project_version="v1",
        mode=mode,
        binding_path=Path("configs/langfuse/prompt_bindings/prompt-sync.yaml"),
        items=[
            PromptSyncStatus(
                artifact=artifact,
                operation="create",
                status="created" if mode == "apply" else "skipped",
                managed_name=artifact.managed_name,
                content_identity=artifact.content_identity,
                langfuse_prompt_version=1 if mode == "apply" else None,
                message="ok",
            )
        ],
    )


def test_sync_prompts_cli_success_output(monkeypatch) -> None:
    class FakeRunner:
        def sync_prompts(self, project, *, dry_run=False):
            assert project == Path("tests/fixtures/projects/valid_prompt_sync.yaml")
            assert dry_run is False
            return _report()

    monkeypatch.setattr(cli, "ExperimentRunner", FakeRunner)

    result = CliRunner().invoke(
        app,
        [
            "sync-prompts",
            "--project",
            "tests/fixtures/projects/valid_prompt_sync.yaml",
        ],
    )

    assert result.exit_code == 0
    assert "project: prompt-sync/v1" in result.stdout
    assert "created: 1" in result.stdout
    assert "prompt: task/task_prompt/v1" in result.stdout


def test_sync_prompts_dry_run_cli_output(monkeypatch) -> None:
    class FakeRunner:
        def sync_prompts(self, project, *, dry_run=False):
            assert dry_run is True
            return _report("dry-run")

    monkeypatch.setattr(cli, "ExperimentRunner", FakeRunner)

    result = CliRunner().invoke(
        app,
        [
            "sync-prompts",
            "--project",
            "tests/fixtures/projects/valid_prompt_sync.yaml",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "mode: dry-run" in result.stdout
    assert "status: skipped" in result.stdout


def test_sync_prompts_audit_alias_still_maps_to_dry_run(monkeypatch) -> None:
    class FakeRunner:
        def sync_prompts(self, project, *, dry_run=False):
            assert dry_run is True
            return _report("dry-run")

    monkeypatch.setattr(cli, "ExperimentRunner", FakeRunner)

    result = CliRunner().invoke(
        app,
        [
            "sync-prompts",
            "--project",
            "tests/fixtures/projects/valid_prompt_sync.yaml",
            "--audit",
        ],
    )

    assert result.exit_code == 0
    assert "mode: dry-run" in result.stdout
