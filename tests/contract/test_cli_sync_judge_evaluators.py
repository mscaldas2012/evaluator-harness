from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from typer.testing import CliRunner

import evaluator_harness.cli as cli_module
from evaluator_harness.cli import app


def _project_with_binding(tmp_path: Path, source: str = "tests/fixtures/projects/valid_rewrite_quality.yaml") -> Path:
    project = tmp_path / "project.yaml"
    binding = tmp_path / "bindings.yaml"
    text = Path(source).read_text(encoding="utf-8")
    text = text.replace(
        "  binding_path: configs/langfuse/evaluator_bindings/rewrite-quality.yaml",
        f"  binding_path: {binding.as_posix()}",
    )
    project.write_text(text, encoding="utf-8")
    return project


def test_sync_judge_evaluators_dry_run_reports_preview_plan(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("EVALUATOR_HARNESS_LIVE", "0")
    project = _project_with_binding(tmp_path)
    result = CliRunner().invoke(
        app,
        [
            "sync-judge-evaluators",
            "--project",
            str(project),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "mode: preview" in result.output
    assert "operation: block" in result.output
    assert "source: custom" in result.output
    assert "sampling: 100" in result.output
    assert "historical-backfill: disabled" in result.output
    assert "sync-score-configs" in result.output
    assert "score-config:" in result.output


def test_sync_judge_evaluators_dry_run_reports_score_config_name_and_id(
    monkeypatch,
) -> None:
    class FakeRunner:
        def sync_judge_evaluators(self, *args, **kwargs):
            return SimpleNamespace(
                project="rewrite-quality",
                project_version="v1",
                mode="preview",
                overall_status="success",
                binding_path=Path("bindings.yaml"),
                evaluators=[
                    SimpleNamespace(
                        evaluator_name="clarity",
                        evaluator_version="v1",
                        source_type="custom",
                        target="observation",
                        operation=SimpleNamespace(value="create"),
                        managed_display_name="EH_rewrite-quality_v1_judge_clarity_v1_custom_observation",
                        score_target=SimpleNamespace(
                            name="eh_rewrite_quality_clarity",
                            score_config_id="score-config-1",
                        ),
                        judge_model="gpt-4.1",
                        llm_connection="lf-connection-default",
                        activation_state="active-on-apply",
                        sampling_percent=100,
                        backfill_status=SimpleNamespace(value="disabled"),
                        binding_status="will-create",
                        filters={},
                        variables={},
                        remediation=None,
                    )
                ],
            )

    monkeypatch.setattr(cli_module, "ExperimentRunner", FakeRunner)

    result = CliRunner().invoke(
        app,
        [
            "sync-judge-evaluators",
            "--project",
            "tests/fixtures/projects/valid_rewrite_quality.yaml",
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "score-config: eh_rewrite_quality_clarity (score-config-1)" in result.output


def test_sync_judge_evaluators_dry_run_reports_missing_score_config_id(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("EVALUATOR_HARNESS_LIVE", "0")
    project = _project_with_binding(tmp_path)

    result = CliRunner().invoke(
        app,
        [
            "sync-judge-evaluators",
            "--project",
            str(project),
            "--dry-run",
        ],
    )

    assert result.exit_code == 0
    assert "operation: block" in result.output
    assert "sync-score-configs" in result.output


def test_sync_judge_evaluators_apply_reports_status(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("EVALUATOR_HARNESS_LIVE", "0")
    project = _project_with_binding(tmp_path)
    binding_path = tmp_path / "bindings.yaml"

    result = CliRunner().invoke(
        app,
        [
            "sync-judge-evaluators",
            "--project",
            str(project),
        ],
    )

    assert result.exit_code == 0
    assert "mode: apply" in result.output
    assert "status: success" in result.output
    assert "binding: created" in result.output
    assert binding_path.exists()


def test_sync_judge_evaluators_audit_reports_non_mutating_audit(
    tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.setenv("EVALUATOR_HARNESS_LIVE", "0")
    project = _project_with_binding(tmp_path)
    result = CliRunner().invoke(
        app,
        [
            "sync-judge-evaluators",
            "--project",
            str(project),
            "--audit",
        ],
    )

    assert result.exit_code == 0
    assert "mode: audit" in result.output
    assert "binding-file:" in result.output


def test_sync_judge_evaluators_returns_validation_failure_exit_code(monkeypatch) -> None:
    monkeypatch.setenv("EVALUATOR_HARNESS_LIVE", "0")

    result = CliRunner().invoke(
        app,
        [
            "sync-judge-evaluators",
            "--project",
            "tests/fixtures/projects/invalid_judge_setup_missing_connection.yaml",
            "--dry-run",
        ],
    )

    assert result.exit_code == 1
    assert "judge model or LLM connection" in result.output


def test_sync_judge_evaluators_returns_unsupported_operation_exit_code(monkeypatch) -> None:
    class UnsupportedRunner:
        def sync_judge_evaluators(self, *args, **kwargs):
            raise NotImplementedError("Installed Langfuse SDK/API does not expose evaluator creation")

    monkeypatch.setattr(cli_module, "ExperimentRunner", UnsupportedRunner)

    result = CliRunner().invoke(
        app,
        [
            "sync-judge-evaluators",
            "--project",
            "tests/fixtures/projects/valid_rewrite_quality.yaml",
        ],
    )

    assert result.exit_code == 2
    assert "does not expose evaluator creation" in result.output
