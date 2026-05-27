from __future__ import annotations

from dataclasses import dataclass

from typer.testing import CliRunner

import evaluator_harness.cli as cli
from evaluator_harness.cli import app
from evaluator_harness.errors import ConfigError


@dataclass(frozen=True)
class FakeRunResult:
    run_id: str = "candidate-123"
    run_type: str = "candidate"
    completed_count: int = 2
    failed_count: int = 0
    baseline_reference: object | None = object()


def test_run_candidate_cli_success_output(monkeypatch) -> None:
    class FakeRunner:
        def run(self, project, mode, **kwargs):
            assert mode == "candidate"
            assert kwargs["candidate"] == "llama3-local"
            assert kwargs["baseline"] == "latest-compatible"
            return FakeRunResult()

    monkeypatch.setattr(cli, "ExperimentRunner", FakeRunner)

    result = CliRunner().invoke(
        app,
        [
            "run",
            "--project",
            "configs/projects/rewrite_quality.yaml",
            "--mode",
            "candidate",
            "--candidate",
            "llama3-local",
            "--baseline",
            "latest-compatible",
        ],
    )

    assert result.exit_code == 0
    assert "run: candidate-123" in result.stdout
    assert "candidate: 2 completed, 0 failed" in result.stdout


def test_run_candidate_cli_failure_exit(monkeypatch) -> None:
    class FakeRunner:
        def run(self, *_args, **_kwargs):
            raise ConfigError("No compatible baseline found")

    monkeypatch.setattr(cli, "ExperimentRunner", FakeRunner)

    result = CliRunner().invoke(
        app,
        [
            "run",
            "--project",
            "configs/projects/rewrite_quality.yaml",
            "--mode",
            "candidate",
            "--candidate",
            "llama3-local",
            "--baseline",
            "latest-compatible",
        ],
    )

    assert result.exit_code == 1
    assert "No compatible baseline found" in result.stdout
