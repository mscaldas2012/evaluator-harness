from __future__ import annotations

from dataclasses import dataclass

from typer.testing import CliRunner

import evaluator_harness.cli as cli
from evaluator_harness.cli import app
from evaluator_harness.errors import ConfigError


@dataclass(frozen=True)
class FakeQueueResult:
    queue_id: str | None = "queue-1"
    queue_name: str | None = "EH_rewrite-quality_v1_review_default"
    ownership: str = "managed_by_harness"
    status: str = "created"
    score_config_ids: list[str] | None = None
    reference_path: str | None = ".evaluator-harness/queue-references/rewrite-quality__v1__default.json"
    message: str = "created"
    manual_fallback_reason: str | None = None


def test_sync_annotation_queue_cli_success_output(monkeypatch) -> None:
    class FakeRunner:
        def sync_annotation_queue(self, project, *, dry_run=False):
            assert dry_run is False
            return FakeQueueResult(score_config_ids=["score-config-1"])

    monkeypatch.setattr(cli, "ExperimentRunner", FakeRunner)

    result = CliRunner().invoke(
        app,
        ["sync-annotation-queue", "--project", "configs/projects/rewrite_quality.yaml"],
    )

    assert result.exit_code == 0
    assert "queue: queue-1" in result.stdout
    assert "status: created" in result.stdout
    assert "ownership: managed_by_harness" in result.stdout
    assert "reference:" in result.stdout


def test_sync_annotation_queue_cli_skipped_output(monkeypatch) -> None:
    class FakeRunner:
        def sync_annotation_queue(self, project, *, dry_run=False):
            return FakeQueueResult(
                queue_id=None,
                queue_name=None,
                ownership="skipped",
                status="skipped",
                reference_path=None,
                message="human review disabled",
            )

    monkeypatch.setattr(cli, "ExperimentRunner", FakeRunner)

    result = CliRunner().invoke(
        app,
        ["sync-annotation-queue", "--project", "tests/fixtures/projects/disabled_annotation_queue.yaml"],
    )

    assert result.exit_code == 0
    assert "status: skipped" in result.stdout


def test_sync_annotation_queue_cli_failure_output(monkeypatch) -> None:
    class FakeRunner:
        def sync_annotation_queue(self, project, *, dry_run=False):
            raise ConfigError("score config IDs are required")

    monkeypatch.setattr(cli, "ExperimentRunner", FakeRunner)

    result = CliRunner().invoke(
        app,
        ["sync-annotation-queue", "--project", "configs/projects/rewrite_quality.yaml"],
    )

    assert result.exit_code == 1
    assert "score config" in result.stdout


def test_sync_annotation_queue_cli_dry_run_output(monkeypatch) -> None:
    class FakeRunner:
        def sync_annotation_queue(self, project, *, dry_run=False):
            assert dry_run is True
            return FakeQueueResult(
                queue_id=None,
                status="planned",
                score_config_ids=["score-config-1"],
                reference_path=None,
                message="annotation queue would be created",
            )

    monkeypatch.setattr(cli, "ExperimentRunner", FakeRunner)

    result = CliRunner().invoke(
        app,
        [
            "sync-annotation-queue",
            "--project",
            "configs/projects/rewrite_quality.yaml",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "status: planned" in result.stdout
    assert "message: annotation queue would be created" in result.stdout


def test_sync_annotation_queue_cli_conflict_exits_nonzero(monkeypatch) -> None:
    class FakeRunner:
        def sync_annotation_queue(self, project, *, dry_run=False):
            return FakeQueueResult(
                queue_id="queue-1",
                status="conflict",
                score_config_ids=["other-score-config"],
                reference_path=None,
                message="Existing annotation queue has score configs that do not match this project.",
            )

    monkeypatch.setattr(cli, "ExperimentRunner", FakeRunner)

    result = CliRunner().invoke(
        app,
        [
            "sync-annotation-queue",
            "--project",
            "configs/projects/rewrite_quality.yaml",
            "--dry-run",
        ],
    )

    assert result.exit_code == 1
    assert "status: conflict" in result.stdout
    assert "do not match this" in result.stdout
    assert "project" in result.stdout
