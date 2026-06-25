from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, cast

from rich.console import Console


@dataclass(frozen=True)
class RunPresentationResult:
    run_result: Any
    skip_sync: bool
    skip_human_review: bool
    report: Any | None


@dataclass(frozen=True)
class ComparisonReportPresentationResult:
    outputs: list[Any]
    baseline: str


def present_validate_result(result: Any, console: Console) -> None:
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


def present_sync_dataset_result(result: Any, console: Console) -> None:
    console.print(f"dataset: {result.name}")
    console.print(f"version: {result.version}")
    console.print(f"compatibility-version: {result.compatibility_version}")
    console.print(f"items: {result.item_count}")
    console.print(f"rejected: {result.rejected_count}")
    console.print(f"status: {result.status}")


def present_sync_score_configs_result(result: Iterable[Any], console: Console) -> None:
    for item in result:
        console.print(f"score-config: {item.name}")
        console.print(f"status: {item.status}")
        console.print(f"ownership: {item.ownership}")
        console.print(f"id: {item.score_config_id}")


def present_sync_prompts_result(result: Any, console: Console) -> None:
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


def present_sync_all_result(result: Any, console: Console) -> None:
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


def present_sync_annotation_queue_result(result: Any, console: Console) -> None:
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


def present_render_judge_prompts_result(
    result: Iterable[Any], console: Console
) -> None:
    for item in result:
        console.print(f"evaluator: {item.evaluator_name}/{item.evaluator_version}")
        console.print(f"target: {item.target}")
        console.print(f"score: {item.score}")
        console.print(
            "shared_with_human_annotation_queue: "
            f"{str(item.shared_with_human_annotation_queue).lower()}"
        )
        console.print("score_sources:")
        for source, langfuse_source in item.score_sources.items():
            console.print(f"  {source}: {langfuse_source}")
        console.print("filters:")
        console.print(f"  project: {item.filters.project}")
        console.print(f"  project_version: {item.filters.project_version}")
        console.print(f"  evaluator_set_id: {item.filters.evaluator_set_id}")
        console.print(
            "  run_type: "
            + ",".join(run_type.value for run_type in item.filters.run_types)
        )
        console.print(f"  observation_role: {item.filters.observation_role}")
        if item.filters.observation_name:
            console.print("optional_narrowing:")
            console.print(f"  observation_name: {item.filters.observation_name}")
        console.print(f"prompt: {item.prompt_path}")


def present_export_evaluator_setup_result(result: Any, console: Console) -> None:
    console.print(f"export: {result}")


def present_judge_setup_result(result: Any, console: Console) -> None:
    console.print(f"project: {result.project}/{result.project_version}")
    console.print(f"mode: {result.mode}")
    console.print(f"status: {result.overall_status}")
    console.print(f"binding-file: {result.binding_path}")
    for evaluator in result.evaluators:
        console.print("")
        console.print(
            f"evaluator: {evaluator.evaluator_name}/{evaluator.evaluator_version}"
        )
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


def present_run_result(result: RunPresentationResult, console: Console) -> None:
    run_result = cast(Any, result.run_result)
    console.print(f"run: {run_result.run_id}")
    if result.skip_sync:
        console.print("sync: skipped")
    console.print(
        f"{run_result.run_type}: {run_result.completed_count} completed, "
        f"{run_result.failed_count} failed"
    )
    if run_result.baseline_reference is not None:
        reference_id = getattr(
            run_result.baseline_reference,
            "baseline_run_id",
            str(run_result.baseline_reference),
        )
        console.print(f"baseline-reference: {reference_id}")

    targeting_status = getattr(run_result, "model_output_targeting_status", None)
    targeting_message = getattr(run_result, "model_output_targeting_message", None)
    if targeting_status and targeting_message:
        console.print(f"model-output-targeting: {targeting_status}")
        console.print(f"model-output-targeting-detail: {targeting_message}")

    langfuse_status = getattr(run_result, "langfuse_status", None)
    if langfuse_status and langfuse_status != "complete":
        console.print(f"langfuse: {langfuse_status}")

    printed_warnings = tuple(getattr(run_result, "langfuse_warnings", ()))
    if printed_warnings:
        console.print(f"warning-count: {len(printed_warnings)}")
    for warning in printed_warnings:
        console.print(f"warning: {warning}")

    review = getattr(run_result, "review_selection", None)
    if review is not None:
        console.print(f"review-selected: {review.selected_count}")
        console.print(f"review-queued: {review.queued_count}")
        console.print(f"review-duplicates-skipped: {review.skipped_duplicate_count}")
    elif result.skip_human_review:
        console.print("review: skipped")

    if result.report is not None:
        report = cast(Any, result.report)
        console.print(f"report: {report.output_path}")
        console.print(f"report-rows: {report.row_count}")
        for warning in getattr(report, "warnings", ()):
            if warning not in printed_warnings:
                console.print(f"warning: {warning}")


def present_select_review_result(result: Any, console: Console) -> None:
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


def present_export_result(result: Any, console: Console) -> None:
    console.print(f"export: {result.output_path}")
    console.print(f"rows: {result.row_count}")
    warnings = tuple(getattr(result, "warnings", ()))
    if warnings:
        console.print(f"warning-count: {len(warnings)}")
    for warning in warnings:
        console.print(f"warning: {warning}")


def present_calibration_capture_result(result: Any, console: Console) -> None:
    console.print(f"calibration: {result.output_path}")
    console.print(f"rows: {result.row_count}")
    console.print(f"paired: {result.paired_count}")
    console.print(f"pending: {result.pending_count}")
    warnings = tuple(getattr(result, "warnings", ()))
    if warnings:
        console.print(f"warning-count: {len(warnings)}")
    for warning in warnings:
        console.print(f"warning: {warning}")


def present_calibration_summary_result(result: Any, console: Console) -> None:
    console.print(f"calibration-summary: {result.output_path}")
    console.print(f"summaries: {result.summary_count}")
    console.print(f"paired: {result.paired_count}")
    console.print(f"pending: {result.pending_count}")
    warnings = tuple(getattr(result, "warnings", ()))
    if warnings:
        console.print(f"warning-count: {len(warnings)}")
    for warning in warnings:
        console.print(f"warning: {warning}")


def present_campaign_calibration_result(result: Any, console: Console) -> None:
    console.print("campaign-calibration: completed")
    console.print(f"baseline: {result.baseline_run_id}")
    console.print(f"runs: {result.run_count}")
    console.print(f"captured: {result.captured_count}")
    console.print(f"summarized: {result.summarized_count}")
    report_path = getattr(result, "html_report_path", None)
    if report_path is not None:
        console.print(f"report: {report_path}")
    console.print(f"source: {result.source}")
    warnings = tuple(getattr(result, "warnings", ()))
    if warnings:
        console.print(f"warning-count: {len(warnings)}")
    for warning in warnings:
        console.print(f"warning: {warning}")


def present_campaign_result(result: Any, console: Console) -> None:
    if result.baseline_run is None:
        console.print("campaign: skipped")
        for warning in result.warnings:
            console.print(f"reason: {warning}")
        return

    has_failures = any(
        candidate.status == "failed" for candidate in result.candidate_runs
    )
    console.print(
        "campaign: completed-with-failures" if has_failures else "campaign: completed"
    )
    console.print(f"baseline: {result.baseline_run.run_id}")
    for candidate in result.candidate_runs:
        if candidate.run_result is not None:
            console.print(
                f"candidate: {candidate.candidate_name} {candidate.run_result.run_id}"
            )
        if candidate.status == "failed":
            console.print(f"failed: {candidate.candidate_name} {candidate.message}")
    for skipped in result.skipped_candidates:
        console.print(f"skipped: {skipped.candidate_name} {skipped.reason}")
    for report in result.csv_reports:
        console.print(f"report: {report.output_path}")
    final_reports = result.final_reports or []
    if final_reports:
        for final_report in final_reports:
            console.print(f"{final_report.format}-report: {final_report.output_path}")
    elif result.excel_report is not None:
        console.print(f"excel-report: {result.excel_report.output_path}")
    for warning in result.warnings:
        console.print(f"warning: {warning}")


def present_comparison_report_result(
    result: ComparisonReportPresentationResult, console: Console
) -> None:
    first = result.outputs[0] if result.outputs else None
    for output in result.outputs:
        console.print(f"{output.format}-report: {output.output_path}")
    if first is not None:
        console.print(f"baseline: {result.baseline}")
        console.print(f"reports: {first.report_count}")
        console.print(f"rows: {first.row_count}")
        console.print(f"score-observations: {first.score_observation_count}")
    for output in result.outputs:
        for warning in output.warnings:
            console.print(f"warning: {warning}")
