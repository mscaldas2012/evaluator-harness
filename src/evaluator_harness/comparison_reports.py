from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Protocol
from collections.abc import Callable

from evaluator_harness.errors import ConfigError, RuntimeDependencyError


class ReportFormat(StrEnum):
    EXCEL = "excel"
    HTML = "html"


@dataclass(frozen=True)
class BaselineRunSelection:
    baseline_run_id: str
    reports_dir: Path = Path("reports")
    report_format: ReportFormat = ReportFormat.EXCEL
    output_path: Path | None = None
    output_dir: Path | None = None
    overwrite: bool = False
    include_run_ids: tuple[str, ...] | None = None


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
    dataset_version: str
    prompt_version: str
    model: str
    parameters: str
    candidate: str = ""
    variant: str = ""


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
class ScoreAggregate:
    score_name: str
    run_id: str
    run_label: str
    average_score: float
    observation_count: int


@dataclass(frozen=True)
class ComparisonReportPayload:
    baseline_run_id: str
    output_path: Path
    run_summaries: list[RunSummary]
    combined_rows: list[CombinedReportRow]
    score_observations: list[ScoreObservation]
    score_aggregates: list[ScoreAggregate]
    warnings: list[str]
    generated_at: str
    worksheet_order: list[str] | None = None
    create_native_pivot: bool = False
    create_clustered_column_chart: bool = False


@dataclass(frozen=True)
class ComparisonReportOutput:
    format: str
    output_path: Path
    report_count: int
    row_count: int
    score_observation_count: int
    warnings: tuple[str, ...] = ()


class ComparisonReportWriter(Protocol):
    def write(self, payload: ComparisonReportPayload) -> None:
        """Write a comparison report from a normalized payload."""


WriterLike = ComparisonReportWriter | Callable[[ComparisonReportPayload], None]


def parse_report_format(value: str | ReportFormat) -> tuple[ReportFormat, ...]:
    text = str(value).strip().lower()
    if text == "both":
        return (ReportFormat.EXCEL, ReportFormat.HTML)
    try:
        return (ReportFormat(text),)
    except ValueError as exc:
        raise ConfigError(
            f"Unsupported report format '{value}'. Supported formats: excel, html, both."
        ) from exc


def build_comparison_payload(
    baseline_run_id: str,
    *,
    reports_dir: Path = Path("reports"),
    report_format: ReportFormat = ReportFormat.EXCEL,
    output_path: Path | None = None,
    output_dir: Path | None = None,
    overwrite: bool = False,
    include_run_ids: tuple[str, ...] | list[str] | None = None,
) -> ComparisonReportPayload:
    selection = BaselineRunSelection(
        baseline_run_id=baseline_run_id,
        reports_dir=reports_dir,
        report_format=report_format,
        output_path=output_path,
        output_dir=output_dir,
        overwrite=overwrite,
        include_run_ids=tuple(include_run_ids) if include_run_ids else None,
    )
    output = derive_output_path(selection)
    available_reports, discovery_warnings = discover_reports_with_warnings(
        selection.reports_dir
    )
    reports = select_reports(selection, available_reports)
    summaries = [build_run_summary(report, selection.baseline_run_id) for report in reports]
    combined_rows = build_combined_rows(reports)
    score_observations = build_score_observations(reports)
    warnings = [
        *discovery_warnings,
        *build_warnings(
        summaries,
        score_observations,
        candidate_baseline_references(available_reports),
        score_column_names(reports),
        ),
    ]
    score_aggregates = build_score_aggregates(score_observations)
    create_score_visuals = bool(score_observations)
    worksheet_order = ["Run Summary", "Combined Data", "Score Data"]
    if create_score_visuals:
        worksheet_order.extend(["Score Pivot", "Score Chart"])
    return ComparisonReportPayload(
        baseline_run_id=selection.baseline_run_id,
        output_path=output,
        run_summaries=summaries,
        combined_rows=combined_rows,
        score_observations=score_observations,
        score_aggregates=score_aggregates,
        warnings=warnings,
        generated_at=datetime.now(UTC).replace(microsecond=0).isoformat(),
        worksheet_order=worksheet_order,
        create_native_pivot=create_score_visuals,
        create_clustered_column_chart=create_score_visuals,
    )


def create_comparison_reports(
    baseline_run_id: str,
    *,
    reports_dir: Path = Path("reports"),
    formats: str | ReportFormat = ReportFormat.EXCEL,
    output_path: Path | None = None,
    output_dir: Path | None = None,
    overwrite: bool = False,
    include_run_ids: tuple[str, ...] | list[str] | None = None,
    excel_writer: WriterLike | None = None,
    html_writer: WriterLike | None = None,
) -> list[ComparisonReportOutput]:
    requested_formats = parse_report_format(formats)
    if output_path is not None and len(requested_formats) > 1:
        raise ConfigError("--output can only be used when generating one report format.")

    outputs: list[ComparisonReportOutput] = []
    for report_format in requested_formats:
        payload = build_comparison_payload(
            baseline_run_id,
            reports_dir=reports_dir,
            report_format=report_format,
            output_path=output_path if len(requested_formats) == 1 else None,
            output_dir=output_dir,
            overwrite=overwrite,
            include_run_ids=include_run_ids,
        )
        writer = _default_writer(report_format, excel_writer, html_writer)
        _write_report(writer, payload)
        if not payload.output_path.exists():
            raise RuntimeDependencyError(
                f"{report_format.value} report creation completed but no file was "
                f"found at {payload.output_path}."
            )
        outputs.append(
            ComparisonReportOutput(
                format=report_format.value,
                output_path=payload.output_path,
                report_count=len(payload.run_summaries),
                row_count=len(payload.combined_rows),
                score_observation_count=len(payload.score_observations),
                warnings=tuple(payload.warnings),
            )
        )
    return outputs


def derive_output_path(selection: BaselineRunSelection) -> Path:
    baseline_run_id = selection.baseline_run_id.strip()
    if not baseline_run_id:
        raise ConfigError("A non-empty baseline run ID is required.")
    reports_dir = Path(selection.reports_dir)
    if not reports_dir.exists() or not reports_dir.is_dir():
        raise ConfigError(f"Comparison report reports directory does not exist: {reports_dir}")

    suffix = ".xlsx" if selection.report_format == ReportFormat.EXCEL else ".html"
    format_name = "Excel" if selection.report_format == ReportFormat.EXCEL else "HTML"
    if selection.output_path is not None:
        output = Path(selection.output_path)
    else:
        output_dir = Path(selection.output_dir) if selection.output_dir is not None else reports_dir
        output = output_dir / f"{baseline_run_id}-comparison{suffix}"
    output = output.resolve()
    if output.suffix.lower() != suffix:
        raise ConfigError(f"{format_name} comparison report output must use a {suffix} extension.")
    if output.exists() and not selection.overwrite:
        artifact = "Workbook" if selection.report_format == ReportFormat.EXCEL else "HTML report"
        raise ConfigError(
            f"{artifact} already exists: {output}. Pass --overwrite to replace it."
        )
    if output.parent and not output.parent.exists():
        raise ConfigError(f"Comparison report output directory does not exist: {output.parent}")
    return output


def discover_reports(reports_dir: Path) -> list[CsvReportInput]:
    return [read_csv_report(path) for path in sorted(Path(reports_dir).glob("*.csv"))]


def discover_reports_with_warnings(
    reports_dir: Path,
) -> tuple[list[CsvReportInput], list[str]]:
    reports: list[CsvReportInput] = []
    warnings: list[str] = []
    for path in sorted(Path(reports_dir).glob("*.csv")):
        try:
            reports.append(read_csv_report(path))
        except ConfigError as exc:
            warnings.append(str(exc))
    return reports, warnings


def select_reports(
    selection: BaselineRunSelection,
    reports: list[CsvReportInput] | None = None,
) -> list[CsvReportInput]:
    if reports is None:
        reports = discover_reports(selection.reports_dir)
    if selection.include_run_ids:
        reports_by_run_id = {report.run_id: report for report in reports}
        requested = [run_id for run_id in selection.include_run_ids if run_id]
        if selection.baseline_run_id not in requested:
            requested = [selection.baseline_run_id, *requested]
        selected = [reports_by_run_id[run_id] for run_id in requested if run_id in reports_by_run_id]
        if not selected or selection.baseline_run_id not in {
            report.run_id for report in selected
        }:
            raise ConfigError(
                f"No CSV report contains baseline run '{selection.baseline_run_id}'."
            )
        return selected
    baseline_reports = [report for report in reports if report.run_id == selection.baseline_run_id]
    if not baseline_reports:
        raise ConfigError(f"No CSV report contains baseline run '{selection.baseline_run_id}'.")
    if len(baseline_reports) > 1:
        raise ConfigError(f"Multiple CSV reports contain baseline run '{selection.baseline_run_id}'.")
    candidates = [
        report
        for report in reports
        if report.run_id != selection.baseline_run_id
        and report.baseline_run_id == selection.baseline_run_id
    ]
    return [baseline_reports[0], *sorted(candidates, key=lambda report: report.run_id)]


def read_csv_report(path: Path) -> CsvReportInput:
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
    run_id = first_non_empty(rows, ["run_id"]) or infer_run_id_from_path(path)
    if not run_id:
        raise ConfigError(f"Malformed CSV report {path.name}: missing run_id value.")
    baseline_run_id = first_non_empty(rows, ["baseline_run_id"]) or None
    run_type = first_non_empty(rows, ["run_type"])
    if not run_type:
        if run_id.startswith("candidate-"):
            run_type = "candidate"
        elif run_id.startswith("baseline-"):
            run_type = "baseline"
        else:
            run_type = "candidate" if baseline_run_id else "baseline"
    return CsvReportInput(
        path=path,
        run_id=run_id,
        run_type=run_type,
        baseline_run_id=baseline_run_id,
        rows=rows,
        columns=columns,
    )


def build_run_summary(report: CsvReportInput, baseline_run_id: str) -> RunSummary:
    model = first_non_empty(
        report.rows,
        ["model", "model_name", "provider_model", "candidate_model", "baseline_model"],
    )
    return RunSummary(
        run_id=report.run_id,
        run_type=report.run_type,
        baseline_run_id=report.baseline_run_id or baseline_run_id,
        source_report=report.path.name,
        row_count=len(report.rows),
        project=first_non_empty(report.rows, ["project", "project_name"]) or "unknown",
        project_version=first_non_empty(report.rows, ["project_version"]) or "unknown",
        dataset=first_non_empty(report.rows, ["dataset", "dataset_name"]) or "unknown",
        dataset_version=first_non_empty(report.rows, ["dataset_version"]) or "unknown",
        prompt_version=first_non_empty(
            report.rows,
            ["prompt_version", "task_prompt_version"],
        )
        or "unknown",
        model=model or "unknown",
        parameters=parameter_summary(report.rows) or "unknown",
        candidate=first_non_empty(report.rows, ["candidate", "candidate_name"]) or "",
        variant=first_non_empty(report.rows, ["variant", "variant_type"]) or "",
    )


def parameter_summary(rows: list[dict[str, str]]) -> str:
    candidates = ["parameters", "model_parameters", "temperature", "top_p", "max_tokens", "seed"]
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


def build_combined_rows(reports: list[CsvReportInput]) -> list[CombinedReportRow]:
    return [
        CombinedReportRow(
            source_report=report.path.name,
            included_run_id=report.run_id,
            included_run_type=report.run_type,
            values=dict(row),
        )
        for report in reports
        for row in report.rows
    ]


def build_score_observations(reports: list[CsvReportInput]) -> list[ScoreObservation]:
    observations: list[ScoreObservation] = []
    for report in reports:
        score_columns = score_columns_for_report(report)
        for row in report.rows:
            for column in score_columns:
                value = parse_float(row.get(column, ""))
                if value is None:
                    continue
                observations.append(
                    ScoreObservation(
                        run_id=report.run_id,
                        run_label=report.run_id,
                        run_type=report.run_type,
                        score_name=score_name_for_column(column),
                        score_value=value,
                        source_report=report.path.name,
                        trace_id=row.get("trace_id", ""),
                        item_id=row.get("item_id", row.get("dataset_item_id", "")),
                    )
                )
    return observations


def build_score_aggregates(observations: list[ScoreObservation]) -> list[ScoreAggregate]:
    buckets: dict[tuple[str, str, str], list[float]] = {}
    run_types: dict[tuple[str, str, str], str] = {}
    for observation in observations:
        key = (observation.score_name, observation.run_id, observation.run_label)
        buckets.setdefault(key, []).append(observation.score_value)
        run_types[key] = observation.run_type
    aggregates: list[ScoreAggregate] = []
    for score_name, run_id, run_label in sorted(
        buckets,
        key=lambda item: (item[0], 0 if run_types[item] == "baseline" else 1, item[1]),
    ):
        values = buckets[(score_name, run_id, run_label)]
        aggregates.append(
            ScoreAggregate(
                score_name=score_name,
                run_id=run_id,
                run_label=run_label,
                average_score=sum(values) / len(values),
                observation_count=len(values),
            )
        )
    return aggregates


def build_warnings(
    summaries: list[RunSummary],
    score_observations: list[ScoreObservation],
    candidate_baseline_references: list[str] | None = None,
    score_columns: list[str] | None = None,
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
    if not score_observations and score_columns == []:
        warnings.append("No score columns found in included CSV reports.")
    elif not score_observations:
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


def candidate_baseline_references(reports: list[CsvReportInput]) -> list[str]:
    references = {
        str(report.baseline_run_id).strip()
        for report in reports
        if report.baseline_run_id and report.run_type == "candidate"
    }
    return sorted(references)


def score_column_names(reports: list[CsvReportInput]) -> list[str]:
    names = {
        column
        for report in reports
        for column in score_columns_for_report(report)
    }
    return sorted(names)


def score_columns_for_report(report: CsvReportInput) -> list[str]:
    evaluator_names = evaluator_names_from_rows(report.rows)
    columns: list[str] = []
    for column in report.columns:
        if column.endswith("_comment"):
            continue
        if column.startswith("score_"):
            columns.append(column)
            continue
        if column in evaluator_names:
            columns.append(column)
    return columns


def evaluator_names_from_rows(rows: list[dict[str, str]]) -> set[str]:
    names: set[str] = set()
    for row in rows:
        for item in str(row.get("evaluator_set_id", "")).split(","):
            name = item.strip().split(":", 1)[0].strip()
            if name:
                names.add(name)
    return names


def score_name_for_column(column: str) -> str:
    return column.removeprefix("score_")


def first_non_empty(rows: list[dict[str, str]], keys: list[str]) -> str:
    for row in rows:
        for key in keys:
            value = str(row.get(key, "")).strip()
            if value:
                return value
    return ""


def parse_float(value: str) -> float | None:
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def infer_run_id_from_path(path: Path) -> str:
    stem = path.stem.strip()
    if stem.startswith("baseline-") or stem.startswith("candidate-"):
        return stem
    return ""


def _default_writer(
    report_format: ReportFormat,
    excel_writer: WriterLike | None,
    html_writer: WriterLike | None,
) -> WriterLike:
    if report_format == ReportFormat.EXCEL:
        if excel_writer is not None:
            return excel_writer
        from evaluator_harness.excel_reports import ExcelComWorkbookWriter

        return ExcelComWorkbookWriter()
    if html_writer is not None:
        return html_writer
    from evaluator_harness.html_reports import HtmlReportWriter

    return HtmlReportWriter()


def _write_report(writer: WriterLike, payload: ComparisonReportPayload) -> None:
    write = getattr(writer, "write", None)
    if callable(write):
        write(payload)
        return
    if callable(writer):
        writer(payload)
        return
    raise TypeError("report writer must be callable or provide write(payload)")
