from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from typer.testing import CliRunner

import evaluator_harness.cli as cli
from evaluator_harness.cli import app


def _sync_all_result(*, annotation_status: str = "planned") -> SimpleNamespace:
    return SimpleNamespace(
        dataset=SimpleNamespace(
            name="rewrite-quality/v1",
            status="planned",
            item_count=2,
        ),
        prompts=SimpleNamespace(
            mode="dry-run",
            created_count=0,
            reused_count=0,
            conflict_count=0,
            failed_count=0,
        ),
        score_configs=[
            SimpleNamespace(name="eh_rewrite_quality_clarity", status="planned_create")
        ],
        judge_evaluators=SimpleNamespace(mode="preview", overall_status="success"),
        annotation_queue=SimpleNamespace(
            status=annotation_status,
            queue_id=None,
            message="annotation queue would be created",
        ),
    )


def test_sync_all_cli_dry_run_reports_all_phases(monkeypatch) -> None:
    class FakeRunner:
        def sync_all(self, project, *, dry_run=False):
            assert project == Path("configs/projects/rewrite_quality.yaml")
            assert dry_run is True
            return _sync_all_result()

    monkeypatch.setattr(cli, "ExperimentRunner", FakeRunner)

    result = CliRunner().invoke(
        app,
        [
            "sync-all",
            "--project",
            "configs/projects/rewrite_quality.yaml",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "Report" in result.stdout
    assert "dataset: rewrite-quality/v1" in result.stdout
    assert "prompts: dry-run" in result.stdout
    assert "score-configs: eh_rewrite_quality_clarity=planned_create" in result.stdout
    assert "judge-evaluators: preview, success" in result.stdout
    assert "annotation-queue: planned" in result.stdout


def test_sync_all_cli_exits_nonzero_on_annotation_conflict(monkeypatch) -> None:
    class FakeRunner:
        def sync_all(self, project, *, dry_run=False):
            return _sync_all_result(annotation_status="conflict")

    monkeypatch.setattr(cli, "ExperimentRunner", FakeRunner)

    result = CliRunner().invoke(
        app,
        [
            "sync-all",
            "--project",
            "configs/projects/rewrite_quality.yaml",
            "--dry-run",
        ],
    )

    assert result.exit_code == 1
    assert "annotation-queue: conflict" in result.stdout
