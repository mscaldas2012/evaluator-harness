from __future__ import annotations

import csv
from pathlib import Path

import pytest

from evaluator_harness.errors import ConfigError
from evaluator_harness.excel_reports import (
    WorkbookPayload,
    create_excel_report,
    _save_workbook_as_xlsx,
)


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


def test_validates_selection_inputs(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    existing = reports_dir / "baseline-1-comparison.xlsx"
    existing.write_text("existing", encoding="utf-8")

    with pytest.raises(ConfigError, match="baseline"):
        create_excel_report("", reports_dir=reports_dir, writer=FakeWorkbookWriter())

    with pytest.raises(ConfigError, match="reports directory"):
        create_excel_report(
            "baseline-1",
            reports_dir=tmp_path / "missing",
            writer=FakeWorkbookWriter(),
        )

    with pytest.raises(ConfigError, match=".xlsx"):
        create_excel_report(
            "baseline-1",
            reports_dir=reports_dir,
            output_path=reports_dir / "bad.txt",
            writer=FakeWorkbookWriter(),
        )

    with pytest.raises(ConfigError, match="already exists"):
        create_excel_report(
            "baseline-1",
            reports_dir=reports_dir,
            output_path=existing,
            writer=FakeWorkbookWriter(),
        )


def test_discovers_baseline_and_associated_candidates(tmp_path: Path) -> None:
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
                "score_quality": "0.8",
            }
        ],
    )
    _write_csv(
        reports_dir / "candidate-b.csv",
        [
            {
                "run_id": "candidate-b",
                "run_type": "candidate",
                "baseline_run_id": "baseline-1",
                "project": "gso",
                "dataset": "gso/v1",
                "model": "gpt-4.1-mini",
                "score_quality": "0.7",
            }
        ],
    )
    _write_csv(
        reports_dir / "unrelated.csv",
        [{"run_id": "candidate-x", "baseline_run_id": "baseline-x", "score_quality": "1"}],
    )
    fake_writer = FakeWorkbookWriter()

    result = create_excel_report(
        "baseline-1",
        reports_dir=reports_dir,
        writer=fake_writer,
    )

    assert result.report_count == 2
    assert result.row_count == 2
    assert result.output_path == (reports_dir / "baseline-1-comparison.xlsx").resolve()
    payload = fake_writer.payloads[0]
    assert [summary.run_id for summary in payload.run_summaries] == [
        "baseline-1",
        "candidate-b",
    ]
    assert [row.included_run_type for row in payload.combined_rows] == [
        "baseline",
        "candidate",
    ]


def test_included_reports_are_baseline_first_then_candidates_sorted(
    tmp_path: Path,
) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    _write_csv(reports_dir / "candidate-z.csv", [{"run_id": "candidate-z", "baseline_run_id": "baseline-1"}])
    _write_csv(reports_dir / "baseline.csv", [{"run_id": "baseline-1", "run_type": "baseline"}])
    _write_csv(reports_dir / "candidate-a.csv", [{"run_id": "candidate-a", "baseline_run_id": "baseline-1"}])
    fake_writer = FakeWorkbookWriter()

    create_excel_report("baseline-1", reports_dir=reports_dir, writer=fake_writer)

    assert [summary.run_id for summary in fake_writer.payloads[0].run_summaries] == [
        "baseline-1",
        "candidate-a",
        "candidate-z",
    ]


def test_missing_baseline_and_malformed_csv_raise_config_errors(
    tmp_path: Path,
) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    _write_csv(reports_dir / "candidate.csv", [{"run_id": "candidate-1", "baseline_run_id": "baseline-1"}])

    with pytest.raises(ConfigError, match="baseline-2"):
        create_excel_report("baseline-2", reports_dir=reports_dir, writer=FakeWorkbookWriter())

    (reports_dir / "bad.csv").write_text("", encoding="utf-8")
    with pytest.raises(ConfigError, match="bad.csv"):
        create_excel_report("baseline-1", reports_dir=reports_dir, writer=FakeWorkbookWriter())


def test_extracts_run_summary_metadata_and_warnings(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    _write_csv(
        reports_dir / "baseline.csv",
        [
            {
                "run_id": "baseline-1",
                "run_type": "baseline",
                "project": "gso",
                "project_version": "v1",
                "dataset": "gso/v1",
                "prompt_version": "prompt-a",
                "model": "gpt-4.1",
                "temperature": "0",
            },
            {
                "run_id": "baseline-1",
                "run_type": "baseline",
                "project": "gso",
                "dataset": "gso/v1",
            },
        ],
    )
    _write_csv(
        reports_dir / "candidate.csv",
        [
            {
                "run_id": "candidate-1",
                "baseline_run_id": "baseline-1",
                "project": "other",
                "project_version": "v1",
                "dataset": "gso/v2",
                "prompt_version": "",
                "model": "gpt-4.1-mini",
            }
        ],
    )
    fake_writer = FakeWorkbookWriter()

    create_excel_report("baseline-1", reports_dir=reports_dir, writer=fake_writer)

    baseline_summary, candidate_summary = fake_writer.payloads[0].run_summaries
    assert baseline_summary.model == "gpt-4.1"
    assert baseline_summary.parameters == "temperature=0"
    assert baseline_summary.row_count == 2
    assert candidate_summary.prompt_version == "unknown"
    assert any("project differs" in warning for warning in fake_writer.payloads[0].warnings)
    assert any("dataset differs" in warning for warning in fake_writer.payloads[0].warnings)


def test_normalizes_numeric_score_columns(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    _write_csv(
        reports_dir / "baseline.csv",
        [
            {
                "run_id": "baseline-1",
                "run_type": "baseline",
                "item_id": "row-1",
                "trace_id": "trace-1",
                "score_quality": "0.8",
                "score_quality_comment": "good",
                "score_accuracy": "",
                "score_style": "not-a-number",
            }
        ],
    )
    fake_writer = FakeWorkbookWriter()

    result = create_excel_report("baseline-1", reports_dir=reports_dir, writer=fake_writer)

    assert result.score_observation_count == 1
    observation = fake_writer.payloads[0].score_observations[0]
    assert observation.score_name == "quality"
    assert observation.score_value == 0.8
    assert observation.item_id == "row-1"
    assert observation.trace_id == "trace-1"


def test_warns_when_no_numeric_scores(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    _write_csv(reports_dir / "baseline.csv", [{"run_id": "baseline-1", "score_quality": ""}])
    fake_writer = FakeWorkbookWriter()

    result = create_excel_report("baseline-1", reports_dir=reports_dir, writer=fake_writer)

    assert result.score_observation_count == 0
    assert any("No numeric score columns" in warning for warning in result.warnings)


def test_no_candidate_warning_lists_available_candidate_baseline_refs(
    tmp_path: Path,
) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    _write_csv(reports_dir / "baseline.csv", [{"run_id": "baseline-1"}])
    _write_csv(
        reports_dir / "candidate.csv",
        [{"run_id": "candidate-1", "baseline_run_id": "baseline-other"}],
    )

    result = create_excel_report(
        "baseline-1",
        reports_dir=reports_dir,
        writer=FakeWorkbookWriter(),
    )

    assert any(
        "baseline-other" in warning and "Available candidate reports" in warning
        for warning in result.warnings
    )


def test_excel_save_uses_explicit_xlsx_format(tmp_path: Path) -> None:
    output_path = tmp_path / "comparison.xlsx"

    class FakeWorkbook:
        FullName = "Book1"

        def __init__(self) -> None:
            self.save_as_kwargs: dict[str, object] = {}

        def SaveAs(self, **kwargs) -> None:
            self.save_as_kwargs = kwargs
            output_path.write_bytes(b"xlsx")

        def SaveCopyAs(self, _filename: str) -> None:
            raise AssertionError("fallback should not be needed")

    workbook = FakeWorkbook()

    _save_workbook_as_xlsx(workbook, output_path)

    assert workbook.save_as_kwargs["Filename"] == str(output_path.resolve())
    assert workbook.save_as_kwargs["FileFormat"] == 51


def test_excel_save_falls_back_to_save_copy_as(tmp_path: Path) -> None:
    output_path = tmp_path / "comparison.xlsx"

    class FakeWorkbook:
        FullName = "Book1"

        def SaveAs(self, **_kwargs) -> None:
            return None

        def SaveCopyAs(self, filename: str) -> None:
            Path(filename).write_bytes(b"xlsx")

    _save_workbook_as_xlsx(FakeWorkbook(), output_path)

    assert output_path.exists()
