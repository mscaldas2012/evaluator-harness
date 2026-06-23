from __future__ import annotations

import csv
from pathlib import Path

import pytest

from evaluator_harness.errors import ConfigError


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


def test_builds_shared_payload_with_baseline_candidates_and_score_averages(
    tmp_path: Path,
) -> None:
    from evaluator_harness.comparison_reports import build_comparison_payload

    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    _write_csv(
        reports_dir / "baseline.csv",
        [
            {
                "run_id": "baseline-1",
                "run_type": "baseline",
                "project": "rewrite",
                "project_version": "v1",
                "dataset": "rewrite/v1",
                "dataset_version": "v1",
                "prompt_version": "p1",
                "model": "gpt-4.1",
                "temperature": "0",
                "trace_id": "trace-b1",
                "item_id": "row-1",
                "score_quality": "0.8",
                "score_quality_comment": "good",
            },
            {
                "run_id": "baseline-1",
                "run_type": "baseline",
                "trace_id": "trace-b2",
                "item_id": "row-2",
                "score_quality": "0.6",
            },
        ],
    )
    _write_csv(
        reports_dir / "candidate.csv",
        [
            {
                "run_id": "candidate-1",
                "run_type": "candidate",
                "baseline_run_id": "baseline-1",
                "project": "rewrite",
                "project_version": "v1",
                "dataset": "rewrite/v1",
                "dataset_version": "v1",
                "prompt_version": "p1",
                "candidate": "candidate-a",
                "model": "gpt-4.1-mini",
                "trace_id": "trace-c1",
                "item_id": "row-1",
                "score_quality": "0.9",
            }
        ],
    )

    payload = build_comparison_payload("baseline-1", reports_dir=reports_dir)

    assert payload.output_path == (reports_dir / "baseline-1-comparison.xlsx").resolve()
    assert [summary.run_id for summary in payload.run_summaries] == [
        "baseline-1",
        "candidate-1",
    ]
    assert payload.run_summaries[0].dataset_version == "v1"
    assert payload.run_summaries[1].candidate == "candidate-a"
    assert len(payload.combined_rows) == 3
    assert len(payload.score_observations) == 3
    assert [(item.score_name, item.run_id, item.average_score) for item in payload.score_aggregates] == [
        ("quality", "baseline-1", 0.7),
        ("quality", "candidate-1", 0.9),
    ]


def test_warns_when_included_csv_reports_have_no_score_columns(tmp_path: Path) -> None:
    from evaluator_harness.comparison_reports import build_comparison_payload

    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    _write_csv(
        reports_dir / "baseline.csv",
        [{"run_id": "baseline-1", "run_type": "baseline", "output": "answer"}],
    )

    payload = build_comparison_payload("baseline-1", reports_dir=reports_dir)

    assert "No score columns found in included CSV reports." in payload.warnings
    assert "No numeric score columns found." not in payload.warnings


def test_uses_evaluator_name_columns_as_score_columns(tmp_path: Path) -> None:
    from evaluator_harness.comparison_reports import build_comparison_payload

    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    _write_csv(
        reports_dir / "baseline.csv",
        [
            {
                "run_id": "baseline-1",
                "run_type": "baseline",
                "evaluator_set_id": "lists_preserved:v3,active_voice:v3",
                "trace_id": "trace-b1",
                "item_id": "row-1",
                "lists_preserved": "0.8",
                "active_voice": "1",
            },
            {
                "run_id": "baseline-1",
                "run_type": "baseline",
                "evaluator_set_id": "lists_preserved:v3,active_voice:v3",
                "trace_id": "trace-b2",
                "item_id": "row-2",
                "lists_preserved": "0.6",
                "active_voice": "0.5",
            },
        ],
    )

    payload = build_comparison_payload("baseline-1", reports_dir=reports_dir)

    assert [(item.score_name, item.run_id, item.average_score) for item in payload.score_aggregates] == [
        ("active_voice", "baseline-1", 0.75),
        ("lists_preserved", "baseline-1", 0.7),
    ]
    assert "No score columns found in included CSV reports." not in payload.warnings


def test_validates_comparison_output_paths_and_formats(tmp_path: Path) -> None:
    from evaluator_harness.comparison_reports import (
        ReportFormat,
        build_comparison_payload,
        parse_report_format,
    )

    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    _write_csv(reports_dir / "baseline.csv", [{"run_id": "baseline-1"}])
    existing = reports_dir / "baseline-1-comparison.html"
    existing.write_text("existing", encoding="utf-8")

    assert parse_report_format("both") == (ReportFormat.EXCEL, ReportFormat.HTML)

    with pytest.raises(ConfigError, match="Supported formats"):
        parse_report_format("pdf")

    with pytest.raises(ConfigError, match=".html"):
        build_comparison_payload(
            "baseline-1",
            reports_dir=reports_dir,
            report_format=ReportFormat.HTML,
            output_path=reports_dir / "bad.txt",
        )

    with pytest.raises(ConfigError, match="already exists"):
        build_comparison_payload(
            "baseline-1",
            reports_dir=reports_dir,
            report_format=ReportFormat.HTML,
        )


def test_create_comparison_reports_invokes_requested_writers(tmp_path: Path) -> None:
    from evaluator_harness.comparison_reports import create_comparison_reports

    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    _write_csv(reports_dir / "baseline.csv", [{"run_id": "baseline-1", "score_quality": "1"}])
    calls: list[tuple[str, Path]] = []

    def excel_writer(payload):
        calls.append(("excel", payload.output_path))
        payload.output_path.write_bytes(b"xlsx")

    def html_writer(payload):
        calls.append(("html", payload.output_path))
        payload.output_path.write_text("<!doctype html>", encoding="utf-8")

    outputs = create_comparison_reports(
        "baseline-1",
        reports_dir=reports_dir,
        formats="both",
        overwrite=True,
        excel_writer=excel_writer,
        html_writer=html_writer,
    )

    assert [output.format for output in outputs] == ["excel", "html"]
    assert calls == [
        ("excel", (reports_dir / "baseline-1-comparison.xlsx").resolve()),
        ("html", (reports_dir / "baseline-1-comparison.html").resolve()),
    ]


def test_create_comparison_reports_ignores_malformed_unrelated_csv(tmp_path: Path) -> None:
    from evaluator_harness.comparison_reports import create_comparison_reports

    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    _write_csv(
        reports_dir / "baseline.csv",
        [{"run_id": "baseline-1", "run_type": "baseline", "score_quality": "1"}],
    )
    _write_csv(
        reports_dir / "candidate.csv",
        [
            {
                "run_id": "candidate-1",
                "run_type": "candidate",
                "baseline_run_id": "baseline-1",
                "score_quality": "0.9",
            }
        ],
    )
    _write_csv(
        reports_dir / "broken.csv",
        [{"run_id": "", "run_type": "baseline", "score_quality": "0.5"}],
    )

    def excel_writer(payload):
        payload.output_path.write_bytes(b"xlsx")

    def html_writer(payload):
        payload.output_path.write_text("<!doctype html>", encoding="utf-8")

    outputs = create_comparison_reports(
        "baseline-1",
        reports_dir=reports_dir,
        formats="both",
        overwrite=True,
        excel_writer=excel_writer,
        html_writer=html_writer,
    )

    assert [output.format for output in outputs] == ["excel", "html"]
    for output in outputs:
        assert any(
            "Malformed CSV report broken.csv: missing run_id value." in warning
            for warning in output.warnings
        )


def test_create_comparison_reports_can_target_specific_run_ids(tmp_path: Path) -> None:
    from evaluator_harness.comparison_reports import create_comparison_reports

    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    _write_csv(
        reports_dir / "baseline-current.csv",
        [{"run_id": "baseline-current", "run_type": "baseline", "score_quality": "1"}],
    )
    _write_csv(
        reports_dir / "candidate-current.csv",
        [
            {
                "run_id": "candidate-current",
                "run_type": "candidate",
                "baseline_run_id": "baseline-current",
                "score_quality": "0.9",
            }
        ],
    )
    _write_csv(
        reports_dir / "baseline-stale.csv",
        [{"run_id": "baseline-stale", "run_type": "baseline", "score_quality": "0.1"}],
    )

    def excel_writer(payload):
        payload.output_path.write_bytes(b"xlsx")

    outputs = create_comparison_reports(
        "baseline-current",
        reports_dir=reports_dir,
        formats="excel",
        overwrite=True,
        include_run_ids=["baseline-current", "candidate-current"],
        excel_writer=excel_writer,
    )

    assert outputs[0].report_count == 2


def test_read_csv_report_infers_run_id_from_filename_for_header_only_csv(
    tmp_path: Path,
) -> None:
    from evaluator_harness.comparison_reports import read_csv_report

    report_path = tmp_path / "baseline-abc123.csv"
    report_path.write_text("run_id,run_type\n", encoding="utf-8")

    report = read_csv_report(report_path)

    assert report.run_id == "baseline-abc123"
    assert report.run_type == "baseline"
