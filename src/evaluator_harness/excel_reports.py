from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

from evaluator_harness.comparison_reports import (
    CombinedReportRow,
    ComparisonReportPayload,
    ReportFormat,
    RunSummary,
    ScoreObservation,
    build_comparison_payload,
)
from evaluator_harness.errors import RuntimeDependencyError


@dataclass(frozen=True)
class WorkbookOutput:
    output_path: Path
    report_count: int
    row_count: int
    score_observation_count: int
    warnings: tuple[str, ...] = ()


WorkbookPayload = ComparisonReportPayload


class ExcelWorkbookWriter(Protocol):
    def write(self, payload: ComparisonReportPayload) -> None:
        """Write a workbook from normalized report payload data."""


def create_excel_report(
    baseline_run_id: str,
    *,
    reports_dir: Path = Path("reports"),
    output_path: Path | None = None,
    overwrite: bool = False,
    writer: ExcelWorkbookWriter | None = None,
) -> WorkbookOutput:
    payload = build_comparison_payload(
        baseline_run_id,
        reports_dir=reports_dir,
        report_format=ReportFormat.EXCEL,
        output_path=output_path,
        overwrite=overwrite,
    )
    default_writer = writer is None
    (writer or ExcelComWorkbookWriter()).write(payload)
    if default_writer and not payload.output_path.exists():
        raise RuntimeDependencyError(
            f"Excel workbook creation completed but no file was found at {payload.output_path}."
        )
    return WorkbookOutput(
        output_path=payload.output_path,
        report_count=len(payload.run_summaries),
        row_count=len(payload.combined_rows),
        score_observation_count=len(payload.score_observations),
        warnings=tuple(payload.warnings),
    )


class ExcelComWorkbookWriter:
    def write(self, payload: ComparisonReportPayload) -> None:
        try:
            import pythoncom  # type: ignore[import-not-found]
            import win32com.client  # type: ignore[import-not-found]
        except ImportError as exc:
            raise RuntimeDependencyError(
                "Native Excel automation is unavailable. Install pywin32 on Windows "
                "with Microsoft Excel installed, or run this command on a Windows "
                "workstation that has Excel."
            ) from exc

        excel = None
        workbook = None
        pythoncom.CoInitialize()
        try:
            excel = win32com.client.DispatchEx("Excel.Application")
            excel.Visible = False
            excel.DisplayAlerts = False
            workbook = excel.Workbooks.Add()
            _reset_workbook_sheets(workbook)
            _write_table(workbook, "Run Summary", _run_summary_rows(payload.run_summaries))
            _write_table(workbook, "Combined Data", _combined_data_rows(payload.combined_rows))
            _write_table(workbook, "Score Data", _score_data_rows(payload.score_observations))
            if payload.create_native_pivot:
                _create_pivot_and_chart(workbook)
            else:
                _write_table(
                    workbook,
                    "Score Notes",
                    [{"message": "No numeric score columns found."}],
                )
            _save_workbook_as_xlsx(workbook, payload.output_path)
        except Exception as exc:  # pragma: no cover - exercised only with Excel installed
            raise RuntimeDependencyError(f"Excel workbook creation failed: {exc}") from exc
        finally:
            if workbook is not None:
                workbook.Close(SaveChanges=False)
            if excel is not None:
                excel.Quit()
            pythoncom.CoUninitialize()


def _reset_workbook_sheets(workbook: object) -> None:
    while workbook.Worksheets.Count > 1:
        workbook.Worksheets(workbook.Worksheets.Count).Delete()
    workbook.Worksheets(1).Name = "Run Summary"


def _sheet(workbook: object, name: str) -> object:
    for index in range(1, workbook.Worksheets.Count + 1):
        worksheet = workbook.Worksheets(index)
        if worksheet.Name == name:
            return worksheet
    worksheet = workbook.Worksheets.Add(After=workbook.Worksheets(workbook.Worksheets.Count))
    worksheet.Name = name
    return worksheet


def _write_table(workbook: object, sheet_name: str, rows: list[dict[str, object]]) -> None:
    worksheet = _sheet(workbook, sheet_name)
    worksheet.Cells.Clear()
    if not rows:
        rows = [{"message": "No rows"}]
    headers = list(rows[0].keys())
    for column_index, header in enumerate(headers, start=1):
        worksheet.Cells(1, column_index).Value = header
    for row_index, row in enumerate(rows, start=2):
        for column_index, header in enumerate(headers, start=1):
            worksheet.Cells(row_index, column_index).Value = row.get(header, "")
    worksheet.Columns.AutoFit()


def _run_summary_rows(summaries: list[RunSummary]) -> list[dict[str, object]]:
    return [asdict(summary) for summary in summaries]


def _combined_data_rows(rows: list[CombinedReportRow]) -> list[dict[str, object]]:
    all_columns: list[str] = []
    for row in rows:
        for key in row.values:
            if key not in all_columns:
                all_columns.append(key)
    combined: list[dict[str, object]] = []
    for row in rows:
        values = {
            "source_report": row.source_report,
            "included_run_id": row.included_run_id,
            "included_run_type": row.included_run_type,
        }
        values.update({key: row.values.get(key, "") for key in all_columns})
        combined.append(values)
    return combined


def _score_data_rows(observations: list[ScoreObservation]) -> list[dict[str, object]]:
    return [asdict(observation) for observation in observations]


def _save_workbook_as_xlsx(workbook: object, output_path: Path) -> None:
    path = output_path.resolve()
    workbook.SaveAs(Filename=str(path), FileFormat=51)
    if not path.exists():
        workbook.SaveCopyAs(str(path))
    if not path.exists():
        full_name = getattr(workbook, "FullName", "unknown")
        raise RuntimeDependencyError(
            f"Excel reported workbook path '{full_name}', but no .xlsx file was "
            f"created at {path}."
        )


def _create_pivot_and_chart(workbook: object) -> None:
    score_sheet = _sheet(workbook, "Score Data")
    pivot_sheet = _sheet(workbook, "Score Pivot")
    chart_sheet = _sheet(workbook, "Score Chart")
    last_row = score_sheet.Cells(score_sheet.Rows.Count, 1).End(-4162).Row
    last_column = score_sheet.Cells(1, score_sheet.Columns.Count).End(-4159).Column
    source_range = score_sheet.Range(
        score_sheet.Cells(1, 1),
        score_sheet.Cells(last_row, last_column),
    )
    pivot_cache = workbook.PivotCaches().Create(SourceType=1, SourceData=source_range)
    pivot_table = pivot_cache.CreatePivotTable(
        TableDestination=pivot_sheet.Range("A3"),
        TableName="AverageEvaluatorScores",
    )
    pivot_table.PivotFields("score_name").Orientation = 1
    pivot_table.PivotFields("run_label").Orientation = 2
    value_field = pivot_table.AddDataField(
        pivot_table.PivotFields("score_value"),
        "Average of score_value",
        -4106,
    )
    value_field.NumberFormat = "0.000"
    chart_object = chart_sheet.ChartObjects().Add(Left=20, Top=20, Width=720, Height=380)
    chart_object.Chart.SetSourceData(pivot_table.TableRange2)
    chart_object.Chart.ChartType = 51
    chart_object.Chart.HasTitle = True
    chart_object.Chart.ChartTitle.Text = "Average evaluator scores by run"
