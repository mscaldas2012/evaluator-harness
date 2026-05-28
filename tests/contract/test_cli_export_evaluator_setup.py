from __future__ import annotations

from typer.testing import CliRunner

from evaluator_harness.cli import app


def test_export_evaluator_setup_writes_setup_markdown() -> None:
    result = CliRunner().invoke(
        app,
        ["export-evaluator-setup", "--project", "configs/projects/rewrite_quality.yaml"],
    )

    from pathlib import Path

    output = Path("reports/evaluator-setup-rewrite-quality-v1.md")
    assert result.exit_code == 0
    assert output.exists()
    text = output.read_text(encoding="utf-8")
    assert "eh_rewrite_quality_clarity" in text
    assert "llm_judge: EVAL" in text
    assert "human_annotation: ANNOTATION" in text
    assert "source_type: custom" in text
    assert "sampling: 100" in text
    assert "historical_backfill: disabled" in text
