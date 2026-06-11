from __future__ import annotations

import csv
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Protocol

from evaluator_harness.errors import ConfigError, RuntimeDependencyError


@dataclass(frozen=True)
class BaselineRunSelection:
    baseline_run_id: str
    reports_dir: Path = Path("reports")
    output_path: Path | None = None
    overwrite: bool = False


@dataclass(frozen=True)
class CsvReportInput:
    path: Path
    run_id: str
    run_type: str
    baseline_run_id: str | None
    rows: list[dict[str, str]]
    columns: list[str]


@dataclass(frozen=True)
class RunSummary:
    run_id: str
    run_type: str
    baseline_run_id: str
    source_report: str
    row_count: int
    project: str
    project_version: str
    dataset: str
    prompt_version: str
    model: str
    parameters: str


@dataclass(frozen=True)
class CombinedReportRow:
    source_report: str
    included_run_id: str
    included_run_type: str
    values: dict[str, str]


@dataclass(frozen=True)
class ScoreObservation:
    run_id: str
    run_label: str
    run_type: str
    score_name: str
    score_value: float
    source_report: str
    trace_id: str
    item_id: str


@dataclass(frozen=True)
class WorkbookPayload:
    output_path: Path
    run_summaries: list[RunSummary]
    combined_rows: list[CombinedReportRow]
    score_observations: list[ScoreObservation]
    warnings: list[str]
    worksheet_order: list[str]
    create_native_pivot: bool
    create_clustered_column_chart: bool


@dataclass(frozen=True)
class WorkbookOutput:
    output_path: Path
    report_count: int
    row_count: int
    score_observation_count: int
    warnings: tuple[str, ...] = ()


class ExcelWorkbookWriter(Protocol):
    def write(self, payload: WorkbookPayload) -> None:
        """Write a workbook from normalized report payload data."""


def create_excel_report(
    baseline_run_id: str,
    *,
    reports_dir: Path = Path("reports"),
    output_path: Path | None = None,
    overwrite: bool = False,
    writer: ExcelWorkbookWriter | None = None,
) -> WorkbookOutput:
    selection = BaselineRunSelection(
        baseline_run_id=baseline_run_id,
        reports_dir=reports_dir,
        output_path=output_path,
        overwrite=overwrite,
    )
    output = _derive_output_path(selection)
    available_reports = _discover_reports(selection.reports_dir)
    reports = _select_reports(selection, available_reports)
    summaries = [_build_run_summary(report, selection.baseline_run_id) for report in reports]
    combined_rows = _build_combined_rows(reports)
    score_observations = _build_score_observations(reports)
    warnings = _build_warnings(
        summaries,
        score_observations,
        _candidate_baseline_references(available_reports),
    )
    create_score_visuals = bool(score_observations)
    worksheet_order = ["Run Summary", "Combined Data", "Score Data"]
    if create_score_visuals:
        worksheet_order.extend(["Score Pivot", "Score Chart"])

    payload = WorkbookPayload(
        output_path=output,
        run_summaries=summaries,
        combined_rows=combined_rows,
        score_observations=score_observations,
        warnings=warnings,
        worksheet_order=worksheet_order,
        create_native_pivot=create_score_visuals,
        create_clustered_column_chart=create_score_visuals,
    )
    default_writer = writer is None
    (writer or ExcelComWorkbookWriter()).write(payload)
    if default_writer and not output.exists():
        raise RuntimeDependencyError(
            f"Excel workbook creation completed but no file was found at {output}."
        )
    return WorkbookOutput(
        output_path=output,
        report_count=len(reports),
        row_count=len(combined_rows),
        score_observation_count=len(score_observations),
        warnings=tuple(warnings),
    )


def _derive_output_path(selection: BaselineRunSelection) -> Path:
    baseline_run_id = selection.baseline_run_id.strip()
    if not baseline_run_id:
        raise ConfigError("A non-empty baseline run ID is required.")
    reports_dir = Path(selection.reports_dir)
    if not reports_dir.exists() or not reports_dir.is_dir():
        raise ConfigError(f"Excel report reports directory does not exist: {reports_dir}")

    output = (
        Path(selection.output_path)
        if selection.output_path is not None
        else reports_dir / f"{baseline_run_id}-comparison.xlsx"
    )
    output = output.resolve()
    if output.suffix.lower() != ".xlsx":
        raise ConfigError("Excel comparison report output must use a .xlsx extension.")
    if output.exists() and not selection.overwrite:
        raise ConfigError(
            f"Workbook already exists: {output}. Pass --overwrite to replace it."
        )
    if output.parent and not output.parent.exists():
        raise ConfigError(f"Workbook output directory does not exist: {output.parent}")
    return output


def _discover_reports(reports_dir: Path) -> list[CsvReportInput]:
    return [_read_csv_report(path) for path in sorted(reports_dir.glob("*.csv"))]


def _select_reports(
    selection: BaselineRunSelection,
    reports: list[CsvReportInput] | None = None,
) -> list[CsvReportInput]:
    if reports is None:
        reports = _discover_reports(selection.reports_dir)
    baseline_reports = [
        report for report in reports if report.run_id == selection.baseline_run_id
    ]
    if not baseline_reports:
        raise ConfigError(
            f"No CSV report contains baseline run '{selection.baseline_run_id}'."
        )
    if len(baseline_reports) > 1:
        raise ConfigError(
            f"Multiple CSV reports contain baseline run '{selection.baseline_run_id}'."
        )

    candidates = [
        report
        for report in reports
        if report.run_id != selection.baseline_run_id
        and report.baseline_run_id == selection.baseline_run_id
    ]
    return [baseline_reports[0], *sorted(candidates, key=lambda report: report.run_id)]


def _read_csv_report(path: Path) -> CsvReportInput:
    try:
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                raise ConfigError(f"Malformed CSV report {path.name}: missing header row.")
            columns = [str(column) for column in reader.fieldnames]
            rows = [
                {key: value or "" for key, value in row.items() if key is not None}
                for row in reader
            ]
    except csv.Error as exc:
        raise ConfigError(f"Malformed CSV report {path.name}: {exc}") from exc

    if "run_id" not in columns:
        raise ConfigError(f"Malformed CSV report {path.name}: missing run_id column.")
    run_id = _first_non_empty(rows, ["run_id"])
    if not run_id:
        raise ConfigError(f"Malformed CSV report {path.name}: missing run_id value.")
    baseline_run_id = _first_non_empty(rows, ["baseline_run_id"]) or None
    run_type = _first_non_empty(rows, ["run_type"])
    if not run_type:
        run_type = "candidate" if baseline_run_id else "baseline"
    return CsvReportInput(
        path=path,
        run_id=run_id,
        run_type=run_type,
        baseline_run_id=baseline_run_id,
        rows=rows,
        columns=columns,
    )


def _build_run_summary(report: CsvReportInput, baseline_run_id: str) -> RunSummary:
    model = _first_non_empty(
        report.rows,
        ["model", "model_name", "provider_model", "candidate_model", "baseline_model"],
    )
    parameters = _parameter_summary(report.rows)
    return RunSummary(
        run_id=report.run_id,
        run_type=report.run_type,
        baseline_run_id=report.baseline_run_id or baseline_run_id,
        source_report=report.path.name,
        row_count=len(report.rows),
        project=_first_non_empty(report.rows, ["project", "project_name"]) or "unknown",
        project_version=_first_non_empty(report.rows, ["project_version"]) or "unknown",
        dataset=_first_non_empty(report.rows, ["dataset", "dataset_name"]) or "unknown",
        prompt_version=_first_non_empty(report.rows, ["prompt_version", "task_prompt_version"])
        or "unknown",
        model=model or "unknown",
        parameters=parameters or "unknown",
    )


def _parameter_summary(rows: list[dict[str, str]]) -> str:
    candidates = [
        "parameters",
        "model_parameters",
        "temperature",
        "top_p",
        "max_tokens",
        "seed",
    ]
    first = rows[0] if rows else {}
    explicit = first.get("parameters") or first.get("model_parameters")
    if explicit:
        return explicit
    values = [
        f"{key}={first[key]}"
        for key in candidates[2:]
        if key in first and str(first[key]).strip()
    ]
    return ", ".join(values)


def _build_combined_rows(reports: list[CsvReportInput]) -> list[CombinedReportRow]:
    combined: list[CombinedReportRow] = []
    for report in reports:
        for row in report.rows:
            combined.append(
                CombinedReportRow(
                    source_report=report.path.name,
                    included_run_id=report.run_id,
                    included_run_type=report.run_type,
                    values=dict(row),
                )
            )
    return combined


def _build_score_observations(reports: list[CsvReportInput]) -> list[ScoreObservation]:
    observations: list[ScoreObservation] = []
    for report in reports:
        score_columns = [
            column
            for column in report.columns
            if column.startswith("score_") and not column.endswith("_comment")
        ]
        for row in report.rows:
            for column in score_columns:
                value = _parse_float(row.get(column, ""))
                if value is None:
                    continue
                observations.append(
                    ScoreObservation(
                        run_id=report.run_id,
                        run_label=report.run_id,
                        run_type=report.run_type,
                        score_name=column.removeprefix("score_"),
                        score_value=value,
                        source_report=report.path.name,
                        trace_id=row.get("trace_id", ""),
                        item_id=row.get("item_id", row.get("dataset_item_id", "")),
                    )
                )
    return observations


def _build_warnings(
    summaries: list[RunSummary],
    score_observations: list[ScoreObservation],
    candidate_baseline_references: list[str] | None = None,
) -> list[str]:
    warnings: list[str] = []
    if len(summaries) == 1:
        message = "No associated candidate reports found."
        if candidate_baseline_references:
            message += (
                " Available candidate reports reference baseline_run_id values: "
                + ", ".join(candidate_baseline_references)
                + "."
            )
        warnings.append(message)
    if not score_observations:
        warnings.append("No numeric score columns found.")
    baseline = summaries[0] if summaries else None
    if baseline is None:
        return warnings
    for summary in summaries[1:]:
        for field_name in ("project", "dataset", "prompt_version"):
            baseline_value = getattr(baseline, field_name)
            candidate_value = getattr(summary, field_name)
            if (
                baseline_value != "unknown"
                and candidate_value != "unknown"
                and baseline_value != candidate_value
            ):
                warnings.append(
                    f"Candidate {summary.run_id} {field_name} differs from baseline: "
                    f"{candidate_value} != {baseline_value}."
                )
    return warnings


def _candidate_baseline_references(reports: list[CsvReportInput]) -> list[str]:
    references = {
        str(report.baseline_run_id).strip()
        for report in reports
        if report.baseline_run_id and report.run_type == "candidate"
    }
    return sorted(references)


def _first_non_empty(rows: list[dict[str, str]], keys: list[str]) -> str:
    for row in rows:
        for key in keys:
            value = str(row.get(key, "")).strip()
            if value:
                return value
    return ""


def _parse_float(value: str) -> float | None:
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


class ExcelComWorkbookWriter:
    def write(self, payload: WorkbookPayload) -> None:
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
