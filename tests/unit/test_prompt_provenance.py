from __future__ import annotations

from pathlib import Path

from evaluator_harness.config import load_project_config
from evaluator_harness.langfuse_default_gateway import DefaultLangfuseGateway
from evaluator_harness.prompt_sync import (
    discover_prompt_artifacts,
    prompt_provenance_metadata,
    sync_project_prompts,
)
from evaluator_harness.providers.base import ModelResponse
from evaluator_harness.runner import ExperimentRunner
from tests.fixtures.fake_provider import FakeModelProvider


def test_validate_project_does_not_require_prompt_bindings() -> None:
    runner = ExperimentRunner(langfuse_gateway=DefaultLangfuseGateway())

    result = runner.validate_project(Path("tests/fixtures/projects/valid_prompt_sync.yaml"))

    assert result.project_name == "prompt-sync"


def test_prompt_provenance_metadata_contains_local_identity_without_binding(tmp_path: Path) -> None:
    config = load_project_config("tests/fixtures/projects/valid_prompt_sync.yaml")

    metadata = prompt_provenance_metadata(
        config,
        binding_path=tmp_path / "missing.yaml",
    )

    assert metadata["prompt_artifact_type"] == "task"
    assert metadata["prompt_content_identity"].startswith("sha256:")
    assert "langfuse_prompt_name" not in metadata


def test_prompt_provenance_metadata_includes_matching_langfuse_reference(tmp_path: Path) -> None:
    config = load_project_config("tests/fixtures/projects/valid_prompt_sync.yaml")
    langfuse = DefaultLangfuseGateway()
    binding_path = tmp_path / "prompt-sync.yaml"

    sync_project_prompts(config, langfuse, binding_path=binding_path)
    metadata = prompt_provenance_metadata(config, binding_path=binding_path)

    assert metadata["langfuse_prompt_name"].startswith("EH_prompt_sync")
    assert metadata["langfuse_prompt_version"] == 1


def test_remote_prompt_content_never_replaces_local_prompt_content() -> None:
    langfuse = DefaultLangfuseGateway()
    provider = FakeModelProvider(
        response=ModelResponse(output="baseline output"),
    )
    runner = ExperimentRunner(
        langfuse_gateway=langfuse,
        provider_factory=lambda _config: provider,
    )

    runner.run(Path("tests/fixtures/projects/valid_prompt_sync.yaml"), "baseline")

    assert "Rewrite public health content clearly" in provider.calls[0].prompt
    assert "remote" not in provider.calls[0].prompt.lower()


def test_run_trace_metadata_includes_local_prompt_provenance() -> None:
    langfuse = DefaultLangfuseGateway()
    provider = FakeModelProvider(response=ModelResponse(output="baseline output"))
    runner = ExperimentRunner(
        langfuse_gateway=langfuse,
        provider_factory=lambda _config: provider,
    )

    runner.run(Path("tests/fixtures/projects/valid_prompt_sync.yaml"), "baseline")

    metadata = langfuse.traces[0]["metadata"]
    assert metadata["prompt_artifact_type"] == "task"
    assert metadata["prompt_artifact_name"] == "task_prompt"
    assert metadata["prompt_content_identity"].startswith("sha256:")


def test_evaluator_prompt_provenance_artifact_can_be_resolved() -> None:
    config = load_project_config("tests/fixtures/projects/valid_prompt_sync.yaml")
    artifacts = discover_prompt_artifacts(config)

    evaluator_artifact = [artifact for artifact in artifacts if artifact.artifact_type == "evaluator"][0]

    assert evaluator_artifact.artifact_name == "clarity"
    assert evaluator_artifact.local_path.as_posix() == "tests/fixtures/prompts/prompt_sync_judge.md"
