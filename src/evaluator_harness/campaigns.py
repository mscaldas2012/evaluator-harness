from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from evaluator_harness.comparison_reports import (
    ComparisonReportOutput,
)
from evaluator_harness.config import ProjectConfig
from evaluator_harness.errors import ConfigError, HarnessError
from evaluator_harness.excel_reports import WorkbookOutput
from evaluator_harness.exports import ExportResult

if TYPE_CHECKING:
    from evaluator_harness.runner import RunResult


@dataclass(frozen=True)
class CampaignCandidateSelection:
    candidate_name: str
    included: bool
    reason: str


@dataclass(frozen=True)
class CampaignCandidateRun:
    candidate_name: str
    run_result: RunResult | None
    csv_report: ExportResult | None
    status: str
    message: str | None = None


@dataclass(frozen=True)
class CampaignRunResult:
    baseline_run: RunResult | None
    candidate_runs: list[CampaignCandidateRun]
    skipped_candidates: list[CampaignCandidateSelection]
    csv_reports: list[ExportResult]
    excel_report: WorkbookOutput | ComparisonReportOutput | None
    warnings: list[str]
    final_reports: list[ComparisonReportOutput] | None = None


RunCallback = Callable[..., "RunResult"]
ExportCallback = Callable[..., ExportResult]
MixedAxesCallback = Callable[[Path, str], list[str]]
CreateReportsCallback = Callable[..., list[ComparisonReportOutput]]
CandidateSelectionsCallback = Callable[
    [ProjectConfig], list[CampaignCandidateSelection]
]


def run_campaign(
    *,
    config: ProjectConfig,
    project_path: Path,
    run: RunCallback,
    export: ExportCallback,
    mixed_variant_axes: MixedAxesCallback,
    create_reports: CreateReportsCallback,
    select_candidates: CandidateSelectionsCallback,
    skip_sync: bool = False,
    select_human_review: bool = True,
    no_report: bool = False,
    overwrite: bool = False,
    report_format: str = "excel",
    confirm_mixed_variant: bool = False,
    on_run_start: Callable[[str, str], None] | None = None,
) -> CampaignRunResult:
    selections = select_candidates(config)
    included_names = [
        selection.candidate_name for selection in selections if selection.included
    ]
    skipped = [selection for selection in selections if not selection.included]
    if not included_names:
        return CampaignRunResult(
            baseline_run=None,
            candidate_runs=[],
            skipped_candidates=skipped,
            csv_reports=[],
            excel_report=None,
            warnings=["no candidates eligible for campaign"],
            final_reports=[],
        )

    if on_run_start is not None:
        on_run_start("baseline", config.baseline.name)
    baseline_run = run(
        project_path,
        "baseline",
        select_human_review=select_human_review,
        skip_sync=skip_sync,
    )
    csv_reports = export_baseline_report(
        project_path=project_path,
        baseline_run=baseline_run,
        export=export,
        no_report=no_report,
    )
    candidate_runs = run_campaign_candidates(
        project_path=project_path,
        included_names=included_names,
        baseline_run=baseline_run,
        run=run,
        export=export,
        mixed_variant_axes=mixed_variant_axes,
        skip_sync=skip_sync,
        select_human_review=select_human_review,
        no_report=no_report,
        confirm_mixed_variant=confirm_mixed_variant,
        on_run_start=on_run_start,
    )
    for candidate_run in candidate_runs:
        if candidate_run.csv_report is not None:
            csv_reports.append(candidate_run.csv_report)

    final_reports, excel_report, final_report_warnings = build_campaign_final_reports(
        config=config,
        baseline_run_id=baseline_run.run_id,
        candidate_runs=candidate_runs,
        create_reports=create_reports,
        no_report=no_report,
        overwrite=overwrite,
        report_format=report_format,
    )
    csv_warnings = campaign_csv_warnings(csv_reports)
    result = CampaignRunResult(
        baseline_run=baseline_run,
        candidate_runs=candidate_runs,
        skipped_candidates=skipped,
        csv_reports=csv_reports,
        excel_report=excel_report,
        warnings=[*csv_warnings, *final_report_warnings],
        final_reports=final_reports,
    )
    _write_campaign_manifest(config, result)
    return result


def campaign_candidate_selections(
    config: ProjectConfig,
) -> list[CampaignCandidateSelection]:
    selections: list[CampaignCandidateSelection] = []
    for candidate in config.candidates:
        included = candidate.exclude_from_campaign is False
        reason = (
            "exclude-from-campaign=false" if included else "exclude-from-campaign=true"
        )
        selections.append(
            CampaignCandidateSelection(
                candidate_name=candidate.name,
                included=included,
                reason=reason,
            )
        )
    return selections


def export_baseline_report(
    *,
    project_path: Path,
    baseline_run: RunResult,
    export: ExportCallback,
    no_report: bool,
) -> list[ExportResult]:
    if no_report:
        return []
    return [
        export(
            project_path,
            baseline_run.run_id,
            "csv",
            expected_count=baseline_run.completed_count + baseline_run.failed_count,
            strict_linkage=False,
        )
    ]


def run_campaign_candidates(
    *,
    project_path: Path,
    included_names: list[str],
    baseline_run: RunResult,
    run: RunCallback,
    export: ExportCallback,
    mixed_variant_axes: MixedAxesCallback,
    skip_sync: bool,
    select_human_review: bool,
    no_report: bool,
    confirm_mixed_variant: bool,
    on_run_start: Callable[[str, str], None] | None,
) -> list[CampaignCandidateRun]:
    candidate_runs: list[CampaignCandidateRun] = []
    for candidate_name in included_names:
        try:
            candidate_runs.append(
                run_one_campaign_candidate(
                    project_path=project_path,
                    candidate_name=candidate_name,
                    baseline_run_id=baseline_run.run_id,
                    run=run,
                    export=export,
                    mixed_variant_axes=mixed_variant_axes,
                    skip_sync=skip_sync,
                    select_human_review=select_human_review,
                    no_report=no_report,
                    confirm_mixed_variant=confirm_mixed_variant,
                    on_run_start=on_run_start,
                )
            )
        except HarnessError as exc:
            candidate_runs.append(
                CampaignCandidateRun(
                    candidate_name=candidate_name,
                    run_result=None,
                    csv_report=None,
                    status="failed",
                    message=str(exc),
                )
            )
    return candidate_runs


def run_one_campaign_candidate(
    *,
    project_path: Path,
    candidate_name: str,
    baseline_run_id: str,
    run: RunCallback,
    export: ExportCallback,
    mixed_variant_axes: MixedAxesCallback,
    skip_sync: bool,
    select_human_review: bool,
    no_report: bool,
    confirm_mixed_variant: bool,
    on_run_start: Callable[[str, str], None] | None,
) -> CampaignCandidateRun:
    if on_run_start is not None:
        on_run_start("candidate", candidate_name)
    if not confirm_mixed_variant:
        axes = mixed_variant_axes(project_path, candidate_name)
        if "prompt" in axes and len(axes) > 1:
            raise ConfigError(
                "Candidate variant changes multiple comparison axes: "
                + ", ".join(axes)
                + ". Pass --confirm-mixed-variant to continue."
            )
    candidate_result = run(
        project_path,
        "candidate",
        candidate=candidate_name,
        baseline=baseline_run_id,
        select_human_review=select_human_review,
        skip_sync=skip_sync,
    )
    csv_report = export_candidate_report(
        project_path=project_path,
        candidate_result=candidate_result,
        export=export,
        no_report=no_report,
    )
    return CampaignCandidateRun(
        candidate_name=candidate_name,
        run_result=candidate_result,
        csv_report=csv_report,
        status="completed",
    )


def export_candidate_report(
    *,
    project_path: Path,
    candidate_result: RunResult,
    export: ExportCallback,
    no_report: bool,
) -> ExportResult | None:
    if no_report:
        return None
    return export(
        project_path,
        candidate_result.run_id,
        "csv",
        expected_count=candidate_result.completed_count + candidate_result.failed_count,
        strict_linkage=False,
    )


def campaign_csv_warnings(csv_reports: list[ExportResult]) -> list[str]:
    warnings: list[str] = []
    for report in csv_reports:
        run_label = report.output_path.stem
        for warning in report.warnings:
            warnings.append(f"{run_label}: {warning}")
    return warnings


def build_campaign_final_reports(
    *,
    config: ProjectConfig,
    baseline_run_id: str,
    candidate_runs: list[CampaignCandidateRun],
    create_reports: CreateReportsCallback,
    no_report: bool,
    overwrite: bool,
    report_format: str,
) -> tuple[
    list[ComparisonReportOutput],
    WorkbookOutput | ComparisonReportOutput | None,
    list[str],
]:
    if no_report:
        return [], None, []
    include_run_ids = [baseline_run_id]
    include_run_ids.extend(
        candidate.run_result.run_id
        for candidate in candidate_runs
        if candidate.run_result is not None
    )
    try:
        final_reports = create_reports(
            baseline_run_id=baseline_run_id,
            reports_dir=_project_reports_dir(config),
            formats=report_format,
            overwrite=overwrite,
            include_run_ids=include_run_ids,
        )
    except HarnessError as exc:
        return [], None, [str(exc)]
    excel_report = next(
        (report for report in final_reports if report.format == "excel"),
        None,
    )
    warnings: list[str] = []
    seen_warnings: set[str] = set()
    for report in final_reports:
        warnings.extend(report.warnings)
    deduped_warnings: list[str] = []
    for warning in warnings:
        if warning in seen_warnings:
            continue
        seen_warnings.add(warning)
        deduped_warnings.append(warning)
    return final_reports, excel_report, deduped_warnings


def _project_reports_dir(config: ProjectConfig) -> Path:
    return Path("reports") / config.project.name


def _write_campaign_manifest(
    config: ProjectConfig,
    result: CampaignRunResult,
) -> None:
    from evaluator_harness.campaign_calibration import (
        write_campaign_manifest_from_result,
    )

    try:
        write_campaign_manifest_from_result(
            config=config,
            result=result,
            reports_dir=_project_reports_dir(config),
        )
    except ConfigError as exc:
        result.warnings.append(str(exc))
