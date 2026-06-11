from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from evaluator_harness.errors import HarnessError
from evaluator_harness.progress import RichProgressReporter
from evaluator_harness.runner import ExperimentRunner

app = typer.Typer(no_args_is_help=True)
console = Console()
_DEFAULT_RUNNER_CLASS = ExperimentRunner


def _runner() -> ExperimentRunner:
    try:
        return ExperimentRunner(progress=RichProgressReporter(console))
    except TypeError:
        if ExperimentRunner is _DEFAULT_RUNNER_CLASS:
            raise
        return ExperimentRunner()


def _handle_command(callback: object) -> None:
    try:
        if callable(callback):
            result = callback()
            return result
    except HarnessError as exc:
        console.print(f"[red]{exc}[/red]")
        raise typer.Exit(code=1) from exc
    except NotImplementedError as exc:
        console.print(f"[yellow]{exc}[/yellow]")
        raise typer.Exit(code=2) from exc


@app.command()
def validate(project: Annotated[Path, typer.Option("--project")]) -> None:
    result = _handle_command(lambda: ExperimentRunner().validate_project(project))
    if result is not None:
        console.print(f"project: {result.project_name}/{result.project_version}")
        console.print(f"dataset: {result.dataset_kind} ({result.item_count} items)")
        console.print(f"baseline: {result.baseline_name}")
        console.print(f"candidates: {', '.join(result.candidate_names)}")
        console.print(f"evaluators: {', '.join(result.evaluator_names)}")
        console.print(f"evaluator-targets: {', '.join(result.evaluator_targets)}")
        console.print(f"score-targets: {', '.join(result.score_targets)}")
        console.print(f"judge-setup: {result.judge_setup_status}")
        if result.judge_default:
            console.print(f"judge-default: {result.judge_default}")
        if result.binding_path:
            console.print(f"binding-file: {result.binding_path}")


@app.command("sync-dataset")
def sync_dataset(
    project: Annotated[Path, typer.Option("--project")],
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    result = _handle_command(lambda: _runner().sync_dataset(project, dry_run=dry_run))
    if result is not None:
        console.print(f"dataset: {result.name}")
        console.print(f"version: {result.version}")
        console.print(f"compatibility-version: {result.compatibility_version}")
        console.print(f"items: {result.item_count}")
        console.print(f"rejected: {result.rejected_count}")
        console.print(f"status: {result.status}")


@app.command("sync-score-configs")
def sync_score_configs(
    project: Annotated[Path, typer.Option("--project")],
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    results = _handle_command(
        lambda: _runner().sync_score_configs(project, dry_run=dry_run)
    )
    if results is not None:
        for result in results:
            console.print(f"score-config: {result.name}")
            console.print(f"status: {result.status}")
            console.print(f"ownership: {result.ownership}")
            console.print(f"id: {result.score_config_id}")


@app.command("sync-prompts")
def sync_prompts(
    project: Annotated[Path, typer.Option("--project")],
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            "--audit",
            help="Preview prompt sync actions without creating Langfuse prompts or writing bindings.",
        ),
    ] = False,
) -> None:
    result = _handle_command(lambda: _runner().sync_prompts(project, dry_run=dry_run))
    if result is not None:
        console.print(f"project: {result.project}/{result.project_version}")
        console.print(f"mode: {result.mode}")
        console.print(f"binding-file: {result.binding_path}")
        console.print(f"prompts: {result.total_count}")
        console.print(f"created: {result.created_count}")
        console.print(f"reused: {result.reused_count}")
        console.print(f"conflicts: {result.conflict_count}")
        console.print(f"failed: {result.failed_count}")
        for item in result.items:
            console.print("")
            console.print(
                "prompt: "
                f"{item.artifact.artifact_type}/"
                f"{item.artifact.artifact_name}/"
                f"{item.artifact.artifact_version}"
            )
            console.print(f"managed-name: {item.managed_name}")
            console.print(f"shape: {item.artifact.prompt_shape}")
            console.print(f"status: {item.status}")
            console.print(f"langfuse-version: {item.langfuse_prompt_version or 'none'}")
            if item.message:
                console.print(f"message: {item.message}")
            if item.remediation:
                console.print(f"remediation: {item.remediation}")
        if result.conflict_count or result.failed_count:
            raise typer.Exit(code=1)


@app.command("sync-all")
def sync_all(
    project: Annotated[Path, typer.Option("--project")],
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    result = _handle_command(lambda: _runner().sync_all(project, dry_run=dry_run))
    if result is not None:
        console.print("Report")
        console.print(
            f"  dataset: {result.dataset.name} ({result.dataset.status}, "
            f"{result.dataset.item_count} items)"
        )
        console.print(
            f"  prompts: {result.prompts.mode}, "
            f"created={result.prompts.created_count}, "
            f"reused={result.prompts.reused_count}, "
            f"conflicts={result.prompts.conflict_count}, "
            f"failed={result.prompts.failed_count}"
        )
        score_summary = ", ".join(
            f"{score.name}={score.status}" for score in result.score_configs
        )
        console.print(f"  score-configs: {score_summary or 'none'}")
        console.print(
            f"  judge-evaluators: {result.judge_evaluators.mode}, "
            f"{result.judge_evaluators.overall_status}"
        )
        console.print(
            f"  annotation-queue: {result.annotation_queue.status} "
            f"({result.annotation_queue.queue_id or 'none'})"
        )
        if result.annotation_queue.message:
            console.print(f"  annotation-message: {result.annotation_queue.message}")
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
    result = _handle_command(
        lambda: _runner().sync_annotation_queue(project, dry_run=dry_run)
    )
    if result is not None:
        console.print(f"queue: {result.queue_id or 'none'}")
        if result.queue_name:
            console.print(f"name: {result.queue_name}")
        console.print(f"status: {result.status}")
        console.print(f"ownership: {result.ownership}")
        if result.score_config_ids:
            console.print(f"score-configs: {', '.join(result.score_config_ids)}")
        if result.reference_path:
            console.print(f"reference: {result.reference_path}")
        if result.manual_fallback_reason:
            console.print(f"manual-fallback: {result.manual_fallback_reason}")
        if result.message:
            console.print(f"message: {result.message}")
        if result.status == "conflict":
            raise typer.Exit(code=1)


@app.command("render-judge-prompts")
def render_judge_prompts(project: Annotated[Path, typer.Option("--project")]) -> None:
    results = _handle_command(lambda: ExperimentRunner().render_judge_prompts(project))
    if results is not None:
        for result in results:
            console.print(f"evaluator: {result.evaluator_name}/{result.evaluator_version}")
            console.print(f"target: {result.target}")
            console.print(f"score: {result.score}")
            console.print(
                "shared_with_human_annotation_queue: "
                f"{str(result.shared_with_human_annotation_queue).lower()}"
            )
            console.print("score_sources:")
            for source, langfuse_source in result.score_sources.items():
                console.print(f"  {source}: {langfuse_source}")
            console.print("filters:")
            console.print(f"  project: {result.filters.project}")
            console.print(f"  project_version: {result.filters.project_version}")
            console.print(f"  evaluator_set_id: {result.filters.evaluator_set_id}")
            console.print(
                "  run_type: "
                + ",".join(run_type.value for run_type in result.filters.run_types)
            )
            console.print(f"  observation_role: {result.filters.observation_role}")
            if result.filters.observation_name:
                console.print("optional_narrowing:")
                console.print(f"  observation_name: {result.filters.observation_name}")
            console.print(f"prompt: {result.prompt_path}")


@app.command("export-evaluator-setup")
def export_evaluator_setup(project: Annotated[Path, typer.Option("--project")]) -> None:
    result = _handle_command(lambda: ExperimentRunner().export_evaluator_setup(project))
    if result is not None:
        console.print(f"export: {result}")


@app.command("sync-judge-evaluators")
def sync_judge_evaluators(
    project: Annotated[Path, typer.Option("--project")],
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
    audit: Annotated[bool, typer.Option("--audit")] = False,
) -> None:
    result = _handle_command(
        lambda: _runner().sync_judge_evaluators(
            project,
            dry_run=dry_run,
            audit=audit,
        )
    )
    if result is not None:
        _print_judge_setup_result(result)


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
            help="Bypass confirmation when a candidate changes multiple comparison axes.",
        ),
    ] = False,
    no_report: Annotated[
        bool,
        typer.Option(
            "--no-report",
            help="Do not automatically export a CSV report after the run completes.",
        ),
    ] = False,
) -> None:
    runner = _runner()

    def execute_run() -> object:
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
        )

    result = _handle_command(
        execute_run
    )
    if result is not None:
        console.print(f"run: {result.run_id}")
        console.print(f"{result.run_type}: {result.completed_count} completed, {result.failed_count} failed")
        if result.baseline_reference is not None:
            reference_id = getattr(
                result.baseline_reference,
                "baseline_run_id",
                str(result.baseline_reference),
            )
            console.print(f"baseline-reference: {reference_id}")
        targeting_status = getattr(result, "model_output_targeting_status", None)
        targeting_message = getattr(result, "model_output_targeting_message", None)
        if targeting_status and targeting_message:
            console.print(f"model-output-targeting: {targeting_status}")
            console.print(f"model-output-targeting-detail: {targeting_message}")
        review = getattr(result, "review_selection", None)
        if review is not None:
            console.print(f"review-selected: {review.selected_count}")
            console.print(f"review-queued: {review.queued_count}")
            console.print(f"review-duplicates-skipped: {review.skipped_duplicate_count}")
        elif skip_human_review:
            console.print("review: skipped")
        if not no_report:
            report = _handle_command(lambda: runner.export(project, result.run_id, "csv"))
            if report is not None:
                console.print(f"report: {report.output_path}")
                console.print(f"report-rows: {report.row_count}")


@app.command("select-review")
def select_review(
    project: Annotated[Path, typer.Option("--project")],
    run_id: Annotated[str, typer.Option("--run")],
    sample_strategy: Annotated[
        str | None,
        typer.Option(
            "--sample-strategy",
            help="Override human_review.sample_strategy for this run: stable or random.",
        ),
    ] = None,
) -> None:
    result = _handle_command(
        lambda: _runner().select_review(
            project,
            run_id,
            sample_strategy=sample_strategy,
        )
    )
    if result is not None:
        console.print("Report")
        console.print(f"  selected: {result.selected_count}")
        console.print(f"  queued: {result.queued_count}")
        console.print(f"  queue: {result.queue_id or 'none'}")
        console.print(f"  queue-ownership: {getattr(result, 'queue_ownership', 'unknown')}")
        console.print(f"  duplicates-skipped: {result.skipped_duplicate_count}")
        if result.reasons:
            reason_text = ", ".join(
                f"{reason}={count}" for reason, count in sorted(result.reasons.items())
            )
            console.print(f"  reasons: {reason_text}")


@app.command()
def export(
    project: Annotated[Path, typer.Option("--project")],
    run_id: Annotated[str, typer.Option("--run")],
    fmt: Annotated[str, typer.Option("--format")] = "csv",
) -> None:
    result = _handle_command(lambda: _runner().export(project, run_id, fmt))
    if result is not None:
        console.print(f"export: {result.output_path}")
        console.print(f"rows: {result.row_count}")


def _print_judge_setup_result(result: object) -> None:
    console.print(f"project: {result.project}/{result.project_version}")
    console.print(f"mode: {result.mode}")
    console.print(f"status: {result.overall_status}")
    console.print(f"binding-file: {result.binding_path}")
    for evaluator in result.evaluators:
        console.print("")
        console.print(f"evaluator: {evaluator.evaluator_name}/{evaluator.evaluator_version}")
        console.print(f"source: {evaluator.source_type}")
        console.print(f"target: {evaluator.target}")
        console.print(f"operation: {evaluator.operation.value}")
        console.print(f"display-name: {evaluator.managed_display_name}")
        console.print(
            "score-config: "
            f"{evaluator.score_target.name} ({evaluator.score_target.score_config_id})"
        )
        if evaluator.judge_model:
            console.print(f"judge-model: {evaluator.judge_model}")
        if evaluator.llm_connection:
            console.print(f"llm-connection: {evaluator.llm_connection}")
        console.print(f"activation: {evaluator.activation_state}")
        console.print(f"sampling: {evaluator.sampling_percent}")
        console.print(f"historical-backfill: {evaluator.backfill_status.value}")
        console.print(f"binding: {evaluator.binding_status}")
        if evaluator.filters:
            console.print("filters:")
            for key, value in evaluator.filters.items():
                console.print(f"  {key}: {value}")
        if evaluator.variables:
            console.print("variables:")
            for key, value in evaluator.variables.items():
                console.print(f"  {key}: {value}")
        if evaluator.remediation:
            console.print(f"remediation: {evaluator.remediation}")
