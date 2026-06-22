from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from typer.testing import CliRunner

import evaluator_harness.cli as cli
from evaluator_harness.cli import app


@dataclass(frozen=True)
class FakeExportResult:
    output_path: Path = Path("reports/rewrite-quality/candidate-1.csv")
    row_count: int = 2
    warnings: tuple[str, ...] = ()


def test_export_csv_cli_success_output(monkeypatch) -> None:
    class FakeRunner:
        def export(self, project, run_id, fmt):
            assert run_id == "candidate-1"
            assert fmt == "csv"
            return FakeExportResult()

    monkeypatch.setattr(cli, "ExperimentRunner", FakeRunner)

    result = CliRunner().invoke(
        app,
        [
            "export",
            "--project",
            "configs/projects/rewrite_quality.yaml",
            "--run",
            "candidate-1",
            "--format",
            "csv",
        ],
    )

    assert result.exit_code == 0
    assert "export:" in result.stdout
    assert "rows: 2" in result.stdout


def test_export_csv_cli_prints_langfuse_warnings(monkeypatch) -> None:
    class FakeRunner:
        def export(self, project, run_id, fmt):
            return FakeExportResult(
                warnings=(
                    "Langfuse score retrieval failed; scores may be incomplete. "
                    "(operation=score_retrieval, affected=1)",
                )
            )

    monkeypatch.setattr(cli, "ExperimentRunner", FakeRunner)

    result = CliRunner().invoke(
        app,
        [
            "export",
            "--project",
            "configs/projects/rewrite_quality.yaml",
            "--run",
            "candidate-1",
            "--format",
            "csv",
        ],
    )

    assert result.exit_code == 0
    assert "warning-count: 1" in result.stdout
    assert "warning: Langfuse score retrieval failed" in result.stdout
