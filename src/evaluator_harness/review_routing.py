from __future__ import annotations

import os
from collections.abc import Sequence
from dataclasses import dataclass

from evaluator_harness.annotation_queues import (
    AnnotationQueueReferenceStore,
    AnnotationQueueSyncResult,
    queue_review_policy_version,
    resolve_annotation_queue,
)
from evaluator_harness.config import ProjectConfig
from evaluator_harness.errors import ConfigError
from evaluator_harness.langfuse_gateways import LangfuseGateway
from evaluator_harness.langfuse_records import AnnotationRoutingResult
from evaluator_harness.progress import ProgressReporter
from evaluator_harness.review_selection import (
    ReviewCandidate,
    SampleStrategy,
    select_review_items,
)


@dataclass(frozen=True)
class ReviewSelectionResult:
    selected_count: int
    queued_count: int
    skipped_duplicate_count: int
    queue_id: str | None
    reasons: dict[str, int]
    queue_ownership: str = "none"


def select_and_route_review_items(
    *,
    config: ProjectConfig,
    run_id: str,
    langfuse_gateway: LangfuseGateway,
    annotation_queue_store: AnnotationQueueReferenceStore,
    progress: ProgressReporter,
    sample_strategy: SampleStrategy | None = None,
    skip_sync: bool = False,
) -> ReviewSelectionResult:
    if sample_strategy is not None and sample_strategy not in {"stable", "random"}:
        raise ConfigError("sample_strategy must be stable or random")
    if not config.human_review.enabled:
        return ReviewSelectionResult(
            selected_count=0,
            queued_count=0,
            skipped_duplicate_count=0,
            queue_id=config.human_review.annotation_queue_id,
            queue_ownership="skipped",
            reasons={},
        )

    score_results = (
        langfuse_gateway.sync_score_configs(config, progress=progress)
        if config.human_review.queue_ownership == "managed_by_harness"
        and not skip_sync
        else []
    )
    with progress.task("Resolving annotation queue", total=None):
        queue = (
            resolve_annotation_queue_without_sync(config, annotation_queue_store)
            if skip_sync
            else resolve_annotation_queue(
                config,
                langfuse_gateway,
                score_results,
                store=annotation_queue_store,
            )
        )
    if not queue.queue_id:
        raise ConfigError("annotation queue could not be resolved")

    dataset_names = [
        name
        for name in [
            config.dataset.langfuse_dataset_name,
            config.dataset.langfuse_dataset_id,
        ]
        if name
    ]
    with progress.task("Fetching review traces", total=None):
        traces = langfuse_gateway.traces_for_run(
            run_id,
            dataset_names=dataset_names or None,
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
    candidates = [ReviewCandidate.from_trace(trace, scores=scores) for trace in traces]
    with progress.task("Checking existing review items", total=None):
        existing_review_trace_ids = langfuse_gateway.annotation_queue_object_ids(
            queue.queue_id
        )
    unqueued_candidates = [
        candidate
        for candidate in candidates
        if candidate.trace_id not in existing_review_trace_ids
    ]
    dataset_name, dataset_version = review_dataset_identity(config, traces)
    selections = select_review_items(
        unqueued_candidates,
        config.human_review,
        project_name=config.project.name,
        dataset_name=dataset_name,
        dataset_version=dataset_version,
        sample_strategy=sample_strategy,
    )
    payloads = []
    with progress.task("Building review payloads", total=len(selections)) as task:
        for selection in selections:
            payloads.append(
                langfuse_gateway.build_annotation_queue_payload(config, selection)
            )
            task.advance()
    with progress.task("Routing review items", total=None):
        routing: AnnotationRoutingResult = langfuse_gateway.route_annotation_items(
            queue.queue_id,
            payloads,
        )
    return ReviewSelectionResult(
        selected_count=len(selections),
        queued_count=routing.queued_count,
        skipped_duplicate_count=routing.skipped_duplicate_count,
        queue_id=routing.queue_id,
        queue_ownership=str(queue.ownership),
        reasons=selection_reasons(selections),
    )


def resolve_annotation_queue_without_sync(
    config: ProjectConfig,
    annotation_queue_store: AnnotationQueueReferenceStore,
) -> AnnotationQueueSyncResult:
    if config.human_review.queue_ownership == "user_owned":
        queue_id = str(config.human_review.annotation_queue_id or "")
        if not queue_id:
            raise ConfigError("user_owned human review requires annotation_queue_id")
        return AnnotationQueueSyncResult(
            queue_id=queue_id,
            queue_name=queue_id,
            ownership="user_owned",
            status="user_owned",
            message="using user-owned annotation queue",
        )
    if config.human_review.fallback_to_env:
        queue_id = os.getenv("LANGFUSE_ANNOTATION_QUEUE_ID")
        if queue_id:
            return AnnotationQueueSyncResult(
                queue_id=queue_id,
                queue_name=queue_id,
                ownership="environment_override",
                status="environment_override",
                message="using LANGFUSE_ANNOTATION_QUEUE_ID override",
            )
    reference = annotation_queue_store.load(
        config.project.name,
        config.project.version,
        queue_review_policy_version(config),
    )
    if reference is None:
        raise ConfigError(
            "--skip-sync requires an existing managed annotation queue reference; "
            "run sync-annotation-queue or run without --skip-sync first."
        )
    return AnnotationQueueSyncResult(
        queue_id=reference.queue_id,
        queue_name=reference.queue_name,
        ownership=reference.ownership,
        status="resolved",
        score_config_ids=reference.score_config_ids,
        reference_path=str(
            annotation_queue_store.path_for(
                config.project.name,
                config.project.version,
                reference.review_policy_version,
            )
        ),
        message="using existing annotation queue reference",
    )


def review_dataset_identity(
    config: ProjectConfig,
    traces: list[dict[str, object]],
) -> tuple[str, str]:
    if not traces:
        return (
            config.dataset.langfuse_dataset_name or "unknown",
            config.dataset.langfuse_dataset_version or "unknown",
        )
    metadata = traces[0].get("metadata", {})
    if not isinstance(metadata, dict):
        metadata = {}
    dataset_name = str(metadata.get("dataset_name"))
    dataset_version = str(
        metadata.get("dataset_compatibility_version")
        or metadata.get("dataset_version")
    )
    return dataset_name, dataset_version


def selection_reasons(selections: Sequence[object]) -> dict[str, int]:
    reasons: dict[str, int] = {}
    for selection in selections:
        reason = str(getattr(selection, "selection_reason"))
        reasons[reason] = reasons.get(reason, 0) + 1
    return reasons
