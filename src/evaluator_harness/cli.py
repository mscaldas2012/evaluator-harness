from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Annotated, Any, TypeVar

import typer
from rich.console import Console

from evaluator_harness.cli_presenters import (
    ComparisonReportPresentationResult,
    RunPresentationResult,
    present_calibration_capture_result,
    present_calibration_summary_result,
    present_campaign_calibration_result,
    present_campaign_result,
    present_comparison_report_result,
    present_export_evaluator_setup_result,
    present_export_result,
    present_judge_setup_result,
    present_render_judge_prompts_result,
    present_run_result,
    present_select_review_result,
    present_sync_all_result,
    present_sync_annotation_queue_result,
    present_sync_dataset_result,
    present_sync_prompts_result,
    present_sync_score_configs_result,
    present_validate_result,
)
from evaluator_harness.comparison_reports import (
    create_comparison_reports,
    parse_report_format,
)
from evaluator_harness.config import load_project_config
from evaluator_harness.errors import HarnessError
from evaluator_harness.progress import RichProgressReporter
from evaluator_harness.review_selection import SampleStrategy
from evaluator_harness.runner import ExperimentRunner

app = typer.Typer(no_args_is_help=True)
console = Console()
_DEFAULT_RUNNER_CLASS = ExperimentRunner
TCommandResult = TypeVar("TCommandResult")


def _runner() -> ExperimentRunner:
    try:
        return ExperimentRunner(progress=RichProgressReporter(console))
    except TypeError:
        if ExperimentRunner is _DEFAULT_RUNNER_CLASS:
            raise
        return ExperimentRunner()


def _handle_command(callback: Callable[[], TCommandResult]) -> TCommandResult | None:
    try:
        result = callback()
        return result
    except HarnessError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc
    except NotImplementedError as exc:
        console.print(f"[yellow]{exc}[/yellow]")
        raise typer.Exit(code=2) from exc


def _resolve_project_path(project: Path) -> Path:
    if project.parent == Path(".") and project.suffix == "":
        return Path("configs/projects") / f"{project.name}.yaml"
    return project


def _selected_reports_dir(project: Path | None, reports_dir: Path | None) -> Path:
    if reports_dir is not None:
        return reports_dir
    if project is None:
        return Path("reports")
    config = load_project_config(_resolve_project_path(project))
    return Path("reports") / config.project.name


@app.command()
def validate(project: Annotated[Path, typer.Option("--project")]) -> None:
    project = _resolve_project_path(project)
    result = _handle_command(lambda: ExperimentRunner().validate_project(project))
    if result is not None:
        present_validate_result(result, console)


@app.command("sync-dataset")
def sync_dataset(
    project: Annotated[Path, typer.Option("--project")],
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    project = _resolve_project_path(project)
    result = _handle_command(lambda: _runner().sync_dataset(project, dry_run=dry_run))
    if result is not None:
        present_sync_dataset_result(result, console)


@app.command("sync-score-configs")
def sync_score_configs(
    project: Annotated[Path, typer.Option("--project")],
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    project = _resolve_project_path(project)
    results = _handle_command(
        lambda: _runner().sync_score_configs(project, dry_run=dry_run)
    )
    if results is not None:
        present_sync_score_configs_result(results, console)


@app.command("sync-prompts")
def sync_prompts(
    project: Annotated[Path, typer.Option("--project")],
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            "--audit",
            help=(
                "Preview prompt sync actions without creating Langfuse prompts "
                "or writing bindings."
            ),
        ),
    ] = False,
) -> None:
    project = _resolve_project_path(project)
    result = _handle_command(lambda: _runner().sync_prompts(project, dry_run=dry_run))
    if result is not None:
        present_sync_prompts_result(result, console)
        if result.conflict_count or result.failed_count:
            raise typer.Exit(code=1)


@app.command("sync-all")
def sync_all(
    project: Annotated[Path, typer.Option("--project")],
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    project = _resolve_project_path(project)
    result = _handle_command(lambda: _runner().sync_all(project, dry_run=dry_run))
    if result is not None:
        present_sync_all_result(result, console)
        if (
            result.prompts.conflict_count
            or result.prompts.failed_count
            or result.annotation_queue.status == "conflict"
            or result.judge_evaluators.overall_status not in {"success", "warning"}
        ):
            raise typer.Exit(code=1)


@app.command("sync-annotation-queue")
def sync_annotation_queue(
    project: Annotated[Path, typer.Option("--project")],
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    project = _resolve_project_path(project)
    result = _handle_command(
        lambda: _runner().sync_annotation_queue(project, dry_run=dry_run)
    )
    if result is not None:
        present_sync_annotation_queue_result(result, console)
        if result.status == "conflict":
            raise typer.Exit(code=1)


@app.command("render-judge-prompts")
def render_judge_prompts(project: Annotated[Path, typer.Option("--project")]) -> None:
    project = _resolve_project_path(project)
    results = _handle_command(lambda: ExperimentRunner().render_judge_prompts(project))
    if results is not None:
        present_render_judge_prompts_result(results, console)


@app.command("export-evaluator-setup")
def export_evaluator_setup(project: Annotated[Path, typer.Option("--project")]) -> None:
    project = _resolve_project_path(project)
    result = _handle_command(lambda: ExperimentRunner().export_evaluator_setup(project))
    if result is not None:
        present_export_evaluator_setup_result(result, console)


@app.command("sync-judge-evaluators")
def sync_judge_evaluators(
    project: Annotated[Path, typer.Option("--project")],
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    audit: Annotated[bool, typer.Option("--audit")] = False,
) -> None:
    project = _resolve_project_path(project)
    result = _handle_command(
        lambda: _runner().sync_judge_evaluators(
            project,
            dry_run=dry_run,
            audit=audit,
        )
    )
    if result is not None:
        present_judge_setup_result(result, console)


@app.command()
def run(
    project: Annotated[Path, typer.Option("--project")],
    mode: Annotated[str, typer.Option("--mode")],
    candidate: Annotated[str | None, typer.Option("--candidate")] = None,
    baseline: Annotated[str | None, typer.Option("--baseline")] = None,
    skip_human_review: Annotated[
        bool,
        typer.Option(
            "--skip-human-review",
            help="Do not automatically select completed run outputs for human review.",
        ),
    ] = False,
    confirm_mixed_variant: Annotated[
        bool,
        typer.Option(
            "--confirm-mixed-variant",
            help=(
                "Bypass confirmation when a candidate changes multiple comparison axes."
            ),
        ),
    ] = False,
    no_report: Annotated[
        bool,
        typer.Option(
            "--no-report",
            help="Do not automatically export a CSV report after the run completes.",
        ),
    ] = False,
    skip_sync: Annotated[
        bool,
        typer.Option(
            "--skip-sync",
            help="Skip dataset and score-config syncs before running.",
        ),
    ] = False,
) -> None:
    project = _resolve_project_path(project)
    runner = _runner()

    def execute_run() -> Any:
        if mode == "candidate" and not baseline:
            raise HarnessError("--baseline is required for candidate runs")
        if mode == "candidate" and candidate and not confirm_mixed_variant:
            axes = runner.mixed_variant_axes(project, candidate)
            if "prompt" in axes and len(axes) > 1:
                console.print(
                    "[yellow]Candidate variant changes multiple comparison axes: "
                    + ", ".join(axes)
                    + ".[/yellow]"
                )
                response = console.input("Type Y to continue: ")
                if response not in {"Y", "y"}:
                    raise HarnessError("Candidate run cancelled.")
        return runner.run(
            project,
            mode,
            candidate=candidate,
            baseline=baseline,
            select_human_review=not skip_human_review,
            skip_sync=skip_sync,
        )

    result = _handle_command(execute_run)
    if result is not None:
        run_result = result
        report = None
        if not no_report:
            report = _handle_command(
                lambda: runner.export(
                    project,
                    run_result.run_id,
                    "csv",
                    expected_count=run_result.completed_count + run_result.failed_count,
                )
            )
        present_run_result(
            RunPresentationResult(
                run_result=run_result,
                skip_sync=skip_sync,
                skip_human_review=skip_human_review,
                report=report,
            ),
            console,
        )


@app.command("select-review")
def select_review(
    project: Annotated[Path, typer.Option("--project")],
    run_id: Annotated[str, typer.Option("--run")],
    sample_strategy: Annotated[
        SampleStrategy | None,
        typer.Option(
            "--sample-strategy",
            help=(
                "Override human_review.sample_strategy for this run: stable or random."
            ),
        ),
    ] = None,
) -> None:
    project = _resolve_project_path(project)
    result = _handle_command(
        lambda: _runner().select_review(
            project,
            run_id,
            sample_strategy=sample_strategy,
        )
    )
    if result is not None:
        present_select_review_result(result, console)


@app.command("calibration-capture")
def calibration_capture(
    project: Annotated[Path, typer.Option("--project")],
    run_id: Annotated[str, typer.Option("--run")],
) -> None:
    project = _resolve_project_path(project)
    result = _handle_command(lambda: _runner().calibration_capture(project, run_id))
    if result is not None:
        present_calibration_capture_result(result, console)


@app.command("calibration-summary")
def calibration_summary(
    project: Annotated[Path, typer.Option("--project")],
    run_id: Annotated[str, typer.Option("--run")],
) -> None:
    project = _resolve_project_path(project)
    result = _handle_command(lambda: _runner().calibration_summary(project, run_id))
    if result is not None:
        present_calibration_summary_result(result, console)


@app.command("campaign-calibration-report")
def campaign_calibration_report(
    project: Annotated[Path, typer.Option("--project")],
    baseline_run_id: Annotated[str, typer.Option("--baseline")],
    reports_dir: Annotated[Path | None, typer.Option("--reports-dir")] = None,
    output: Annotated[Path | None, typer.Option("--output")] = None,
    output_dir: Annotated[Path | None, typer.Option("--output-dir")] = None,
) -> None:
    project = _resolve_project_path(project)
    result = _handle_command(
        lambda: _runner().campaign_calibration_report(
            project,
            baseline_run_id=baseline_run_id,
            reports_dir=reports_dir,
            output_path=output,
            output_dir=output_dir,
        )
    )
    if result is not None:
        present_campaign_calibration_result(result, console)


@app.command()
def export(
    project: Annotated[Path, typer.Option("--project")],
    run_id: Annotated[str, typer.Option("--run")],
    fmt: Annotated[str, typer.Option("--format")] = "csv",
) -> None:
    project = _resolve_project_path(project)
    result = _handle_command(lambda: _runner().export(project, run_id, fmt))
    if result is not None:
        present_export_result(result, console)


@app.command("campaign")
def campaign(
    project: Annotated[Path, typer.Option("--project")],
    skip_sync: Annotated[
        bool,
        typer.Option(
            "--skip-sync",
            help="Skip dataset and score-config syncs before running.",
        ),
    ] = False,
    skip_human_review: Annotated[
        bool,
        typer.Option(
            "--skip-human-review",
            help="Do not automatically select completed run outputs for human review.",
        ),
    ] = False,
    no_report: Annotated[
        bool,
        typer.Option(
            "--no-report",
            help="Do not export CSV reports or create final comparison reports.",
        ),
    ] = False,
    report_format: Annotated[
        str,
        typer.Option(
            "--report-format",
            help="Final comparison report format: excel, html, or both.",
        ),
    ] = "excel",
    overwrite: Annotated[
        bool,
        typer.Option(
            "--overwrite",
            help="Replace existing campaign final comparison reports.",
        ),
    ] = False,
    confirm_mixed_variant: Annotated[
        bool,
        typer.Option(
            "--confirm-mixed-variant",
            help="Bypass confirmation when a campaign candidate changes multiple axes.",
        ),
    ] = False,
) -> None:
    project = _resolve_project_path(project)
    parsed_format = _handle_command(lambda: parse_report_format(report_format))
    if parsed_format is None:
        return

    def print_campaign_progress(run_type: str, name: str) -> None:
        console.print(f"running: {run_type} {name}")

    result = _handle_command(
        lambda: _runner().campaign(
            project,
            skip_sync=skip_sync,
            select_human_review=not skip_human_review,
            no_report=no_report,
            overwrite=overwrite,
            report_format=report_format,
            confirm_mixed_variant=confirm_mixed_variant,
            on_run_start=print_campaign_progress,
        )
    )
    if result is not None:
        has_failures = any(
            candidate.status == "failed" for candidate in result.candidate_runs
        )
        present_campaign_result(result, console)
        if result.baseline_run is None:
            return
        if has_failures:
            raise typer.Exit(code=1)


@app.command("comparison-report")
def comparison_report(
    baseline: Annotated[str, typer.Option("--baseline")],
    fmt: Annotated[
        str,
        typer.Option(
            "--format",
            help="Final comparison report format: excel, html, or both.",
        ),
    ] = "excel",
    project: Annotated[Path | None, typer.Option("--project")] = None,
    reports_dir: Annotated[Path | None, typer.Option("--reports-dir")] = None,
    output: Annotated[Path | None, typer.Option("--output")] = None,
    output_dir: Annotated[Path | None, typer.Option("--output-dir")] = None,
    overwrite: Annotated[
        bool,
        typer.Option(
            "--overwrite",
            help="Replace existing comparison report artifacts.",
        ),
    ] = False,
) -> None:
    result = _handle_command(
        lambda: create_comparison_reports(
            baseline_run_id=baseline,
            reports_dir=_selected_reports_dir(project, reports_dir),
            formats=fmt,
            output_path=output,
            output_dir=output_dir,
            overwrite=overwrite,
        )
    )
    if result is not None:
        present_comparison_report_result(
            ComparisonReportPresentationResult(outputs=result, baseline=baseline),
            console,
        )


@app.command("excel-report")
def excel_report(
    baseline: Annotated[str, typer.Option("--baseline")],
    project: Annotated[Path | None, typer.Option("--project")] = None,
    reports_dir: Annotated[Path | None, typer.Option("--reports-dir")] = None,
    output: Annotated[Path | None, typer.Option("--output")] = None,
    overwrite: Annotated[
        bool,
        typer.Option(
            "--overwrite",
            help="Replace an existing workbook at the selected output path.",
        ),
    ] = False,
) -> None:
    result = _handle_command(
        lambda: create_comparison_reports(
            baseline_run_id=baseline,
            reports_dir=_selected_reports_dir(project, reports_dir),
            formats="excel",
            output_path=output,
            overwrite=overwrite,
        )
    )
    if result is not None:
        present_comparison_report_result(
            ComparisonReportPresentationResult(outputs=result, baseline=baseline),
            console,
        )
