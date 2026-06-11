from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

import evaluator_harness.cli as cli
from evaluator_harness.cli import app
from evaluator_harness.config import BaselineReference
from evaluator_harness.runner import RunResult


def test_candidate_cli_requires_explicit_baseline(monkeypatch) -> None:
    calls = []

    class FakeRunner:
        def mixed_variant_axes(self, project: Path, candidate: str) -> list[str]:
            return []

        def run(self, *args, **kwargs):
            calls.append((args, kwargs))
            return RunResult(run_id="candidate-1", run_type="candidate", completed_count=1, failed_count=0)

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
            "dry-run-candidate",
            "--no-report",
        ],
    )

    assert result.exit_code != 0
    assert "--baseline is required for candidate runs" in result.stdout
    assert calls == []


def test_candidate_cli_accepts_explicit_baseline(monkeypatch) -> None:
    class FakeRunner:
        def mixed_variant_axes(self, project: Path, candidate: str) -> list[str]:
            return []

        def run(self, project, mode, **kwargs):
            assert kwargs["baseline"] == "baseline-1"
            return RunResult(
                run_id="candidate-1",
                run_type="candidate",
                completed_count=1,
                failed_count=0,
                baseline_reference=BaselineReference(
                    baseline_run_id="baseline-1",
                    langfuse_run_name="run",
                    created_at="2026-06-11T00:00:00+00:00",
                    project_name="rewrite-quality",
                    project_version="v1",
                    dataset_name="rewrite-quality/v1",
                    dataset_version="latest",
                    prompt_version="v1",
                    evaluator_set_id="clarity:v1",
                    baseline_model="model",
                    baseline_parameters_hash="hash",
                ),
            )

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
            "dry-run-candidate",
            "--baseline",
            "baseline-1",
            "--no-report",
        ],
    )

    assert result.exit_code == 0
    assert "baseline-reference: baseline-1" in result.stdout
