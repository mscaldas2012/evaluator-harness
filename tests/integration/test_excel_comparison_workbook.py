from __future__ import annotations

import csv
from pathlib import Path

from evaluator_harness.excel_reports import WorkbookPayload, create_excel_report


class FakeWorkbookWriter:
    def __init__(self) -> None:
        self.payloads: list[WorkbookPayload] = []

    def write(self, payload: WorkbookPayload) -> None:
        self.payloads.append(payload)


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


def test_excel_report_orchestrates_discovery_summary_and_scores(
    tmp_path: Path,
) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    _write_csv(
        reports_dir / "baseline.csv",
        [
            {
                "run_id": "baseline-1",
                "run_type": "baseline",
                "project": "gso",
                "dataset": "gso/v1",
                "model": "gpt-4.1",
                "item_id": "1",
                "score_quality": "0.9",
            }
        ],
    )
    _write_csv(
        reports_dir / "candidate.csv",
        [
            {
                "run_id": "candidate-1",
                "run_type": "candidate",
                "baseline_run_id": "baseline-1",
                "project": "gso",
                "dataset": "gso/v1",
                "model": "gpt-4.1-mini",
                "item_id": "1",
                "score_quality": "0.7",
            }
        ],
    )
    fake_writer = FakeWorkbookWriter()

    result = create_excel_report("baseline-1", reports_dir=reports_dir, writer=fake_writer)

    assert result.output_path == (reports_dir / "baseline-1-comparison.xlsx").resolve()
    payload = fake_writer.payloads[0]
    assert payload.worksheet_order[:3] == ["Run Summary", "Combined Data", "Score Data"]
    assert payload.create_native_pivot is True
    assert payload.create_clustered_column_chart is True
    assert len(payload.run_summaries) == 2
    assert len(payload.combined_rows) == 2
    assert len(payload.score_observations) == 2


def test_excel_report_no_numeric_scores_skips_pivot_and_chart(
    tmp_path: Path,
) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    _write_csv(reports_dir / "baseline.csv", [{"run_id": "baseline-1", "score_quality": ""}])
    fake_writer = FakeWorkbookWriter()

    result = create_excel_report("baseline-1", reports_dir=reports_dir, writer=fake_writer)

    payload = fake_writer.payloads[0]
    assert payload.create_native_pivot is False
    assert payload.create_clustered_column_chart is False
    assert any("No numeric score columns" in warning for warning in result.warnings)
