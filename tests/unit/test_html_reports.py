from __future__ import annotations

from pathlib import Path


def _payload(output_path: Path):
    from evaluator_harness.comparison_reports import (
        CombinedReportRow,
        ComparisonReportPayload,
        RunSummary,
        ScoreAggregate,
        ScoreObservation,
    )

    return ComparisonReportPayload(
        baseline_run_id="baseline-1",
        output_path=output_path,
        run_summaries=[
            RunSummary(
                run_id="baseline-1",
                run_type="baseline",
                baseline_run_id="baseline-1",
                source_report="baseline.csv",
                row_count=2,
                project="rewrite",
                project_version="v1",
                dataset="rewrite/v1",
                dataset_version="v1",
                prompt_version="p1",
                model="gpt-4.1",
                parameters="temperature=0",
                candidate="",
                variant="",
            ),
            RunSummary(
                run_id="candidate-1",
                run_type="candidate",
                baseline_run_id="baseline-1",
                source_report="candidate.csv",
                row_count=2,
                project="rewrite",
                project_version="v1",
                dataset="rewrite/v1",
                dataset_version="v1",
                prompt_version="p1",
                model="gpt-4.1-mini",
                parameters="temperature=0.2",
                candidate="candidate-a",
                variant="model",
            ),
        ],
        combined_rows=[
            CombinedReportRow(
                source_report="baseline.csv",
                included_run_id="baseline-1",
                included_run_type="baseline",
                values={"input": "<unsafe>", "output": "safe"},
            )
        ],
        score_observations=[
            ScoreObservation(
                run_id="baseline-1",
                run_label="baseline-1",
                run_type="baseline",
                score_name="quality",
                score_value=0.75,
                source_report="baseline.csv",
                trace_id="trace-1",
                item_id="row-1",
            )
        ],
        score_aggregates=[
            ScoreAggregate("quality", "baseline-1", "baseline-1", 0.75, 1),
            ScoreAggregate("quality", "candidate-1", "candidate-1", 0.9, 1),
            ScoreAggregate("brevity", "baseline-1", "baseline-1", 0.8, 1),
            ScoreAggregate("brevity", "candidate-1", "candidate-1", 0.6, 1),
        ],
        warnings=["No associated candidate reports found."],
        generated_at="2026-06-13T10:00:00",
    )


def test_html_writer_creates_polished_self_contained_report(tmp_path: Path) -> None:
    from evaluator_harness.html_reports import HtmlReportWriter

    output_path = tmp_path / "comparison.html"

    HtmlReportWriter().write(_payload(output_path))

    html = output_path.read_text(encoding="utf-8")
    assert html.startswith("<!doctype html>")
    assert "Run Summary" in html
    assert "Score Pivot" in html
    assert "Average evaluator scores" in html
    assert "<svg" in html
    assert "baseline-1" in html
    assert "candidate-1" in html
    assert "&lt;unsafe&gt;" in html
    assert "https://" not in html
    assert "http://" not in html
    assert "--ink:" in html
    assert "@media" in html
    assert "aria-label=\"Average evaluator scores by run\"" in html
    assert "report-shell" in html
    assert 'class="score-delta score-up"' in html
    assert 'class="score-delta score-down"' in html
    assert "▲ +0.150" in html
    assert "▼ -0.200" in html
    assert 'class="pivot-run-diff"' in html
    assert '<span class="pivot-run-diff-item">model: gpt-4.1-mini</span>' in html
    assert '<span class="pivot-run-diff-item">temp: 0.2</span>' in html
    assert '<tfoot class="pivot-summary-footer"><tr><th scope="row">Candidate summary</th>' in html
    assert 'class="pivot-run-summary"' in html
    assert "▲ 1 / ▼ 1 · avg Δ -0.025" in html
    assert "<details class=\"source-data-panel\">" in html
    assert "<summary>Source Data Preview</summary>" in html
    assert html.index("Average evaluator scores") < html.index("Source Data Preview")


def test_html_writer_renders_no_score_state(tmp_path: Path) -> None:
    from evaluator_harness.comparison_reports import ComparisonReportPayload
    from evaluator_harness.html_reports import HtmlReportWriter

    output_path = tmp_path / "comparison.html"
    payload = _payload(output_path)
    payload = ComparisonReportPayload(
        baseline_run_id=payload.baseline_run_id,
        output_path=payload.output_path,
        run_summaries=payload.run_summaries[:1],
        combined_rows=payload.combined_rows,
        score_observations=[],
        score_aggregates=[],
        warnings=["No numeric score columns found."],
        generated_at=payload.generated_at,
    )

    HtmlReportWriter().write(payload)

    html = output_path.read_text(encoding="utf-8")
    assert "No numeric score columns found." in html
    assert html.count("No numeric score columns found.") >= 2
    assert "notice-panel" in html
