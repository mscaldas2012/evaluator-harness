from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import SimpleNamespace

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
    review_selection: object | None = None


@dataclass(frozen=True)
class FakeExportResult:
    output_path: Path = Path("reports/rewrite-quality/candidate-123.csv")
    row_count: int = 2


class FakeRunnerBase:
    def export(self, project, run_id, fmt):
        return FakeExportResult()


def test_run_candidate_cli_success_output(monkeypatch) -> None:
    class FakeRunner(FakeRunnerBase):
        def mixed_variant_axes(self, *_args, **_kwargs):
            return []

        def run(self, project, mode, **kwargs):
            assert mode == "candidate"
            assert kwargs["candidate"] == "llama3-local"
            assert kwargs["baseline"] == "latest-compatible"
            assert kwargs["select_human_review"] is True
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


def test_run_candidate_cli_exports_report_by_default(monkeypatch) -> None:
    calls: list[tuple[Path, str, str]] = []

    class FakeRunner(FakeRunnerBase):
        def mixed_variant_axes(self, *_args, **_kwargs):
            return []

        def run(self, project, mode, **kwargs):
            assert mode == "candidate"
            return FakeRunResult()

        def export(self, project, run_id, fmt):
            calls.append((project, run_id, fmt))
            return FakeExportResult()

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
    assert calls == [(Path("configs/projects/rewrite_quality.yaml"), "candidate-123", "csv")]
    assert "report: reports\\rewrite-quality\\candidate-123.csv" in result.stdout
    assert "report-rows: 2" in result.stdout


def test_run_candidate_cli_no_report_skips_export(monkeypatch) -> None:
    class FakeRunner(FakeRunnerBase):
        def mixed_variant_axes(self, *_args, **_kwargs):
            return []

        def run(self, project, mode, **kwargs):
            assert mode == "candidate"
            return FakeRunResult()

        def export(self, *_args, **_kwargs):
            raise AssertionError("export should not be called")

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
            "--no-report",
        ],
    )

    assert result.exit_code == 0
    assert "report:" not in result.stdout


def test_run_candidate_cli_prints_automatic_human_review_summary(monkeypatch) -> None:
    class FakeRunner(FakeRunnerBase):
        def mixed_variant_axes(self, *_args, **_kwargs):
            return []

        def run(self, *_args, **_kwargs):
            return FakeRunResult(
                review_selection=SimpleNamespace(
                    selected_count=2,
                    queued_count=1,
                    skipped_duplicate_count=1,
                )
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
            "llama3-local",
            "--baseline",
            "latest-compatible",
        ],
    )

    assert result.exit_code == 0
    assert "review-selected: 2" in result.stdout
    assert "review-queued: 1" in result.stdout
    assert "review-duplicates-skipped: 1" in result.stdout


def test_run_candidate_cli_can_skip_automatic_human_review(monkeypatch) -> None:
    class FakeRunner(FakeRunnerBase):
        def mixed_variant_axes(self, *_args, **_kwargs):
            return []

        def run(self, project, mode, **kwargs):
            assert kwargs["select_human_review"] is False
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
            "--skip-human-review",
        ],
    )

    assert result.exit_code == 0
    assert "review: skipped" in result.stdout


def test_run_candidate_cli_failure_exit(monkeypatch) -> None:
    class FakeRunner(FakeRunnerBase):
        def mixed_variant_axes(self, *_args, **_kwargs):
            return []

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


def test_run_candidate_cli_does_not_prompt_for_model_and_parameter_variant(monkeypatch) -> None:
    class FakeRunner(FakeRunnerBase):
        def mixed_variant_axes(self, project, candidate):
            assert project == Path("configs/projects/rewrite_quality.yaml")
            assert candidate == "azure-mistral-large-3"
            return ["model", "params"]

        def run(self, *_args, **_kwargs):
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
            "azure-mistral-large-3",
            "--baseline",
            "latest-compatible",
        ],
    )

    assert result.exit_code == 0
    assert "Candidate variant changes multiple comparison axes" not in result.stdout
    assert "Type Y to continue:" not in result.stdout
    assert "run: candidate-123" in result.stdout


def test_run_candidate_cli_prompts_for_prompt_mixed_variant(monkeypatch) -> None:
    class FakeRunner(FakeRunnerBase):
        def mixed_variant_axes(self, project, candidate):
            assert project == Path("configs/projects/rewrite_quality.yaml")
            assert candidate == "azure-mistral-large-3"
            return ["model", "prompt", "params"]

        def run(self, *_args, **_kwargs):
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
            "azure-mistral-large-3",
            "--baseline",
            "latest-compatible",
        ],
        input="y\n",
    )

    assert result.exit_code == 0
    assert "Candidate variant changes multiple comparison axes: model, prompt, params." in result.stdout
    assert "Type Y to continue:" in result.stdout
    assert "run: candidate-123" in result.stdout


def test_run_candidate_cli_accepts_uppercase_y_for_mixed_variant(monkeypatch) -> None:
    class FakeRunner(FakeRunnerBase):
        def mixed_variant_axes(self, *_args, **_kwargs):
            return ["prompt", "params"]

        def run(self, *_args, **_kwargs):
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
            "azure-mistral-large-3",
            "--baseline",
            "latest-compatible",
        ],
        input="Y\n",
    )

    assert result.exit_code == 0
    assert "Type Y to continue:" in result.stdout
    assert "run: candidate-123" in result.stdout


def test_run_candidate_cli_aborts_mixed_variant_without_y(monkeypatch) -> None:
    class FakeRunner(FakeRunnerBase):
        def mixed_variant_axes(self, *_args, **_kwargs):
            return ["prompt", "params"]

        def run(self, *_args, **_kwargs):
            raise AssertionError("run should not be called")

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
            "azure-mistral-large-3",
            "--baseline",
            "latest-compatible",
        ],
        input="n\n",
    )

    assert result.exit_code == 1
    assert "Candidate run cancelled." in result.stdout


def test_run_candidate_cli_confirm_flag_bypasses_mixed_variant_prompt(monkeypatch) -> None:
    class FakeRunner(FakeRunnerBase):
        def mixed_variant_axes(self, *_args, **_kwargs):
            return ["prompt", "params"]

        def run(self, *_args, **_kwargs):
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
            "azure-mistral-large-3",
            "--baseline",
            "latest-compatible",
            "--confirm-mixed-variant",
        ],
    )

    assert result.exit_code == 0
    assert "Type Y to continue:" not in result.stdout
    assert "run: candidate-123" in result.stdout
