from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from evaluator_harness.config import ProjectConfig
from evaluator_harness.errors import ConfigError
from evaluator_harness.exports import ExportResult, export_summary
from evaluator_harness.langfuse_gateways import LangfuseGateway
from evaluator_harness.langfuse_records import format_langfuse_warning
from evaluator_harness.progress import ProgressReporter


def export_run_summary(
    *,
    config: ProjectConfig,
    run_id: str,
    fmt: str,
    langfuse_gateway: LangfuseGateway,
    progress: ProgressReporter,
    warning_provider: Callable[[], tuple[Any, ...]],
    expected_count: int | None = None,
    strict_linkage: bool = True,
) -> ExportResult:
    if fmt != "csv":
        raise ConfigError(f"Unsupported export format: {fmt}")
    dataset_names = [
        name
        for name in [
            config.dataset.langfuse_dataset_name,
            config.dataset.langfuse_dataset_id,
        ]
        if name
    ]
    with progress.task("Fetching traces", total=None):
        traces = langfuse_gateway.traces_for_run(
            run_id,
            dataset_names=dataset_names or None,
            expected_count=expected_count,
        )
    trace_ids = [
        str(trace["trace_id"])
        for trace in traces
        if trace.get("trace_id") is not None
    ]
    scores = langfuse_gateway.fetch_scores(
        run_id,
        trace_ids=trace_ids,
        progress=progress,
    )
    warnings = warning_provider()
    linkage_warnings = export_linkage_warnings(
        expected_count=expected_count,
        trace_count=len(traces),
        warnings=warnings,
    )
    if strict_linkage and linkage_warnings:
        raise ConfigError(linkage_warnings[0])
    warning_messages = tuple(format_langfuse_warning(warning) for warning in warnings)
    return export_summary(
        traces,
        project_reports_dir(config) / f"{run_id}.csv",
        scores=scores,
        progress=progress,
        warnings=(*warning_messages, *linkage_warnings),
    )


def export_linkage_warnings(
    *,
    expected_count: int | None,
    trace_count: int,
    warnings: tuple[Any, ...],
) -> tuple[str, ...]:
    messages: list[str] = []
    operations = {getattr(warning, "operation", "") for warning in warnings}
    if (
        expected_count is not None
        and trace_count < expected_count
        and "trace_lookup" in operations
    ):
        messages.append(
            "Langfuse trace confirmation failed; export would be misleading "
            f"({trace_count}/{expected_count} expected traces confirmed)."
        )
    if "score_retrieval" in operations:
        messages.append(
            "Langfuse score confirmation failed; export would be misleading."
        )
    return tuple(messages)


def project_reports_dir(config: ProjectConfig) -> Path:
    return Path("reports") / config.project.name
