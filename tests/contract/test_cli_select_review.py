from __future__ import annotations

from dataclasses import dataclass

from typer.testing import CliRunner

import evaluator_harness.cli as cli
from evaluator_harness.cli import app
from evaluator_harness.errors import ConfigError, LangfuseError


@dataclass(frozen=True)
class FakeReviewResult:
    selected_count: int = 2
    queued_count: int = 2
    skipped_duplicate_count: int = 0
    queue_id: str | None = "queue-1"
    queue_ownership: str = "managed_by_harness"
    reasons: dict[str, int] | None = None


def test_select_review_cli_success_output(monkeypatch) -> None:
    class FakeRunner:
        def select_review(self, project, run_id):
            assert run_id == "candidate-1"
            return FakeReviewResult(reasons={"failure": 1, "sample": 1})

    monkeypatch.setattr(cli, "ExperimentRunner", FakeRunner)

    result = CliRunner().invoke(
        app,
        [
            "select-review",
            "--project",
            "configs/projects/rewrite_quality.yaml",
            "--run",
            "candidate-1",
        ],
    )

    assert result.exit_code == 0
    assert "selected: 2" in result.stdout
    assert "queued: 2" in result.stdout
    assert "queue: queue-1" in result.stdout


def test_select_review_cli_missing_queue_failure(monkeypatch) -> None:
    class FakeRunner:
        def select_review(self, *_args):
            raise ConfigError("annotation_queue_id is required")

    monkeypatch.setattr(cli, "ExperimentRunner", FakeRunner)

    result = CliRunner().invoke(
        app,
        [
            "select-review",
            "--project",
            "configs/projects/rewrite_quality.yaml",
            "--run",
            "candidate-1",
        ],
    )

    assert result.exit_code == 1
    assert "annotation_queue_id" in result.stdout


def test_select_review_cli_langfuse_failure(monkeypatch) -> None:
    class FakeRunner:
        def select_review(self, *_args):
            raise LangfuseError("Langfuse is unreachable during select-review")

    monkeypatch.setattr(cli, "ExperimentRunner", FakeRunner)

    result = CliRunner().invoke(
        app,
        [
            "select-review",
            "--project",
            "configs/projects/rewrite_quality.yaml",
            "--run",
            "candidate-1",
        ],
    )

    assert result.exit_code == 1
    assert "Langfuse is unreachable" in result.stdout
