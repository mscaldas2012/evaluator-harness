from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

import evaluator_harness.cli as cli
from evaluator_harness.cli import app
from tests.contract.test_cli_run_baseline import FakeExportResult
from tests.contract.test_cli_run_candidate import FakeRunResult


def test_run_cli_resolves_project_name_to_config_path(monkeypatch) -> None:
    calls: list[Path] = []

    class FakeRunner:
        def run(self, project, mode, **_kwargs):
            calls.append(project)
            assert mode == "baseline"
            return FakeRunResult(run_id="baseline-123", run_type="baseline")

        def export(self, project, _run_id, _fmt):
            calls.append(project)
            return FakeExportResult()

    monkeypatch.setattr(cli, "ExperimentRunner", FakeRunner)

    result = CliRunner().invoke(
        app,
        ["run", "--project", "dfe-general-public", "--mode", "baseline"],
    )

    assert result.exit_code == 0
    assert calls == [
        Path("configs/projects/dfe-general-public.yaml"),
        Path("configs/projects/dfe-general-public.yaml"),
    ]


def test_run_cli_keeps_explicit_project_path(monkeypatch) -> None:
    calls: list[Path] = []

    class FakeRunner:
        def run(self, project, mode, **_kwargs):
            calls.append(project)
            assert mode == "baseline"
            return FakeRunResult(run_id="baseline-123", run_type="baseline")

        def export(self, project, _run_id, _fmt):
            calls.append(project)
            return FakeExportResult()

    monkeypatch.setattr(cli, "ExperimentRunner", FakeRunner)

    result = CliRunner().invoke(
        app,
        ["run", "--project", "configs/projects/dfe-general-public.yaml", "--mode", "baseline"],
    )

    assert result.exit_code == 0
    assert calls == [
        Path("configs/projects/dfe-general-public.yaml"),
        Path("configs/projects/dfe-general-public.yaml"),
    ]
