from __future__ import annotations

import csv
from pathlib import Path


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    fieldnames: list[str] = []
    for row in rows:
        for key in row:
            if key not in fieldnames:
                fieldnames.append(key)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def test_create_html_report_from_csv_reports(tmp_path: Path) -> None:
    from evaluator_harness.html_reports import create_html_report

    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    _write_csv(
        reports_dir / "baseline.csv",
        [{"run_id": "baseline-1", "run_type": "baseline", "model": "gpt-4.1", "score_quality": "0.7"}],
    )
    _write_csv(
        reports_dir / "candidate.csv",
        [
            {
                "run_id": "candidate-1",
                "run_type": "candidate",
                "baseline_run_id": "baseline-1",
                "candidate": "candidate-a",
                "model": "gpt-4.1-mini",
                "score_quality": "0.9",
            }
        ],
    )

    result = create_html_report("baseline-1", reports_dir=reports_dir)

    assert result.output_path == (reports_dir / "baseline-1-comparison.html").resolve()
    assert result.report_count == 2
    assert result.row_count == 2
    assert result.score_observation_count == 2
    html = result.output_path.read_text(encoding="utf-8")
    assert "candidate-a" in html
    assert "quality" in html
    assert "grid-template-columns" in html

