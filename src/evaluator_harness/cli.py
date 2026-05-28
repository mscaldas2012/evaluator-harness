from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console

from evaluator_harness.errors import HarnessError
from evaluator_harness.runner import ExperimentRunner

app = typer.Typer(no_args_is_help=True)
console = Console()


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
def sync_dataset(project: Annotated[Path, typer.Option("--project")]) -> None:
    result = _handle_command(lambda: ExperimentRunner().sync_dataset(project))
    if result is not None:
        console.print(f"dataset: {result.name}")
        console.print(f"version: {result.version}")
        console.print(f"compatibility-version: {result.compatibility_version}")
        console.print(f"items: {result.item_count}")
        console.print(f"rejected: {result.rejected_count}")
        console.print(f"status: {result.status}")


@app.command("sync-score-configs")
def sync_score_configs(project: Annotated[Path, typer.Option("--project")]) -> None:
    results = _handle_command(lambda: ExperimentRunner().sync_score_configs(project))
    if results is not None:
        for result in results:
            console.print(f"score-config: {result.name}")
            console.print(f"status: {result.status}")
            console.print(f"ownership: {result.ownership}")
            console.print(f"id: {result.score_config_id}")


@app.command("sync-annotation-queue")
def sync_annotation_queue(project: Annotated[Path, typer.Option("--project")]) -> None:
    result = _handle_command(lambda: ExperimentRunner().sync_annotation_queue(project))
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
        lambda: ExperimentRunner().sync_judge_evaluators(
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
) -> None:
    result = _handle_command(
        lambda: ExperimentRunner().run(
            project,
            mode,
            candidate=candidate,
            baseline=baseline,
        )
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


@app.command("select-review")
def select_review(
    project: Annotated[Path, typer.Option("--project")],
    run_id: Annotated[str, typer.Option("--run")],
) -> None:
    result = _handle_command(lambda: ExperimentRunner().select_review(project, run_id))
    if result is not None:
        console.print(f"selected: {result.selected_count}")
        console.print(f"queued: {result.queued_count}")
        console.print(f"queue: {result.queue_id or 'none'}")
        console.print(f"queue-ownership: {getattr(result, 'queue_ownership', 'unknown')}")
        console.print(f"duplicates-skipped: {result.skipped_duplicate_count}")
        if result.reasons:
            reason_text = ", ".join(
                f"{reason}={count}" for reason, count in sorted(result.reasons.items())
            )
            console.print(f"reasons: {reason_text}")


@app.command()
def export(
    project: Annotated[Path, typer.Option("--project")],
    run_id: Annotated[str, typer.Option("--run")],
    fmt: Annotated[str, typer.Option("--format")] = "csv",
) -> None:
    result = _handle_command(lambda: ExperimentRunner().export(project, run_id, fmt))
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
