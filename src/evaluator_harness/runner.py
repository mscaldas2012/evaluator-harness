from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from collections.abc import Callable
from uuid import uuid4

from evaluator_harness.baseline_registry import (
    BaselineFingerprint,
    BaselineRegistry,
    build_baseline_fingerprint,
    fingerprint_metadata,
)
from evaluator_harness.certificates import configure_tls_truststore
from evaluator_harness.annotation_queues import (
    AnnotationQueueReferenceStore,
    AnnotationQueueSyncResult,
    queue_review_policy_version,
    resolve_annotation_queue,
    sync_annotation_queue,
)
from evaluator_harness.config import (
    BaselineReference,
    DatasetItem,
    DatasetKind,
    load_env_file,
    load_layered_env_files,
    ModelConfig,
    ProjectConfig,
    project_env_file_path,
    load_project_config,
    scenario_metadata,
    validate_project_config,
)
from evaluator_harness.dataset_loader import dataset_compatibility_version, load_dataset
from evaluator_harness.errors import ConfigError, HarnessError
from evaluator_harness.evaluators import (
    evaluator_score_summary,
    evaluator_target_summary,
    export_evaluator_setup,
    render_judge_prompts,
)
from evaluator_harness.evaluator_bindings import load_evaluator_bindings
from evaluator_harness.exports import ExportResult, export_summary
from evaluator_harness.langfuse_evaluator_setup import (
    EvaluatorSetupResult,
    apply_judge_evaluator_setup,
    audit_judge_evaluator_setup,
    plan_judge_evaluator_setup,
)
from evaluator_harness.langfuse_client import (
    AnnotationRoutingResult,
    DatasetSyncResult,
    LangfuseClient,
    ScoreConfigSyncResult,
)
from evaluator_harness.model_output_targeting import (
    MODEL_OUTPUT_ROLE,
    RUN_ITEM_ROLE,
    diagnose_model_output_targeting,
    final_output_metadata,
    parent_observation_metadata,
    metadata_with_observation_role,
)
from evaluator_harness.providers import create_provider
from evaluator_harness.providers import provider_tracing_metadata
from evaluator_harness.providers.base import (
    ModelProvider,
    ModelRequest,
    validate_provider_roles,
)
from evaluator_harness.progress import NullProgressReporter, ProgressReporter
from evaluator_harness.prompts import (
    RenderedPrompt,
    parse_prompt_file,
    prompt_identity as prompt_file_identity,
    render_prompt,
)
from evaluator_harness.prompt_sync import (
    PromptSyncReport,
    prompt_provenance_metadata,
    sync_project_prompts,
)
from evaluator_harness.review_selection import (
    ReviewCandidate,
    SampleStrategy,
    select_review_items,
)
from evaluator_harness.comparison_reports import (
    ComparisonReportOutput,
    create_comparison_reports,
)
from evaluator_harness.excel_reports import WorkbookOutput
from evaluator_harness.session_identity import (
    SessionIdentityInputs,
    item_comparison_session_id,
)


@dataclass(frozen=True)
class ValidationResult:
    project_name: str
    project_version: str
    dataset_kind: str
    item_count: int
    baseline_name: str
    candidate_names: list[str]
    evaluator_names: list[str]
    evaluator_targets: list[str]
    score_targets: list[str]
    judge_setup_status: str = "ready"
    judge_default: str | None = None
    binding_path: str | None = None


@dataclass(frozen=True)
class RunResult:
    run_id: str
    run_type: str
    completed_count: int
    failed_count: int
    baseline_reference: BaselineReference | None = None
    review_selection: ReviewSelectionResult | None = None
    model_output_targeting_status: str | None = None
    model_output_targeting_message: str | None = None


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


@dataclass(frozen=True)
class ReviewSelectionResult:
    selected_count: int
    queued_count: int
    skipped_duplicate_count: int
    queue_id: str | None
    reasons: dict[str, int]
    queue_ownership: str = "none"


@dataclass(frozen=True)
class SyncAllResult:
    dataset: DatasetSyncResult
    prompts: PromptSyncReport
    score_configs: list[ScoreConfigSyncResult]
    judge_evaluators: EvaluatorSetupResult
    annotation_queue: AnnotationQueueSyncResult


class ExperimentRunner:
    def __init__(
        self,
        *,
        langfuse_client: LangfuseClient | None = None,
        provider_factory: Any | None = None,
        baseline_registry: BaselineRegistry | None = None,
        progress: ProgressReporter | None = None,
    ) -> None:
        configure_tls_truststore()
        load_env_file()
        self._langfuse_client_provided = langfuse_client is not None
        self.langfuse_client = langfuse_client or LangfuseClient()
        self.provider_factory = provider_factory or create_provider
        self.baseline_registry = baseline_registry or BaselineRegistry()
        self.annotation_queue_store = AnnotationQueueReferenceStore()
        self.progress = progress or NullProgressReporter()

    def _load_project_config(self, project_path: Path) -> ProjectConfig:
        config = load_project_config(project_path)
        load_layered_env_files(
            root_env_file=".env",
            project_env_file=project_env_file_path(config.project.name),
        )
        if (
            not self._langfuse_client_provided
            and os.getenv("EVALUATOR_HARNESS_LIVE") in {"1", "true", "TRUE", "yes"}
        ):
            self.langfuse_client = LangfuseClient.from_env()
        return config

    def validate_project(self, project_path: Path) -> ValidationResult:
        config = self._load_project_config(project_path)
        validate_project_config(config)
        items = self._validate_dataset(config)
        return ValidationResult(
            project_name=config.project.name,
            project_version=config.project.version,
            dataset_kind=config.dataset.kind.value,
            item_count=len(items),
            baseline_name=config.baseline.name,
            candidate_names=[candidate.name for candidate in config.candidates],
            evaluator_names=[
                f"{evaluator.name}/{evaluator.version}" for evaluator in config.evaluators
            ],
            evaluator_targets=[
                evaluator_target_summary(evaluator) for evaluator in config.evaluators
            ],
            score_targets=[
                evaluator_score_summary(config, evaluator) for evaluator in config.evaluators
            ],
            judge_setup_status="ready",
            judge_default=(
                config.judge_setup.default_judge_model
                or config.judge_setup.default_llm_connection
            ),
            binding_path=str(
                config.judge_setup.binding_path
                or Path("configs/langfuse/evaluator_bindings")
                / f"{config.project.name}.yaml"
            ),
        )

    def sync_dataset(self, project_path: Path, *, dry_run: bool = False) -> DatasetSyncResult:
        config = self._load_project_config(project_path)
        validate_project_config(config)
        items = self._validate_dataset(config)
        return self.langfuse_client.sync_dataset(
            config.dataset,
            items,
            dry_run=dry_run,
            progress=self.progress,
        )

    def sync_score_configs(
        self,
        project_path: Path,
        *,
        dry_run: bool = False,
    ) -> list[ScoreConfigSyncResult]:
        config = self._load_project_config(project_path)
        validate_project_config(config)
        return self.langfuse_client.sync_score_configs(
            config,
            progress=self.progress,
            dry_run=dry_run,
        )

    def _skip_sync_dataset_result(
        self,
        config: ProjectConfig,
        items: list[DatasetItem],
    ) -> DatasetSyncResult:
        name = config.dataset.langfuse_dataset_name or config.dataset.langfuse_dataset_id
        if not name:
            raise ConfigError("Dataset sync requires a Langfuse dataset name or ID")
        compatibility_version = (
            config.dataset.langfuse_dataset_version
            or dataset_compatibility_version(items)
        )
        return DatasetSyncResult(
            name=name,
            version=config.dataset.langfuse_dataset_version or "latest",
            compatibility_version=compatibility_version,
            item_count=len(items),
            status="skipped",
        )

    def sync_prompts(
        self,
        project_path: Path,
        *,
        dry_run: bool = False,
    ) -> PromptSyncReport:
        config = self._load_project_config(project_path)
        validate_project_config(config)
        return sync_project_prompts(
            config,
            self.langfuse_client,
            dry_run=dry_run,
            progress=self.progress,
        )

    def sync_all(self, project_path: Path, *, dry_run: bool = False) -> SyncAllResult:
        dataset_description = "Checking dataset" if dry_run else "Syncing dataset"
        with self.progress.task(dataset_description, total=None):
            dataset = self.sync_dataset(project_path, dry_run=dry_run)
        prompts = self.sync_prompts(project_path, dry_run=dry_run)
        score_configs = self.sync_score_configs(project_path, dry_run=dry_run)
        judge_evaluators = self.sync_judge_evaluators(
            project_path,
            dry_run=dry_run,
            score_results=score_configs,
        )
        queue_description = "Checking annotation queue" if dry_run else "Syncing annotation queue"
        with self.progress.task(queue_description, total=None):
            annotation_queue = self.sync_annotation_queue(
                project_path,
                dry_run=dry_run,
                score_results=score_configs,
            )
        return SyncAllResult(
            dataset=dataset,
            prompts=prompts,
            score_configs=score_configs,
            judge_evaluators=judge_evaluators,
            annotation_queue=annotation_queue,
        )

    def render_judge_prompts(self, project_path: Path) -> list[Any]:
        config = self._load_project_config(project_path)
        validate_project_config(config)
        return render_judge_prompts(config)

    def export_evaluator_setup(self, project_path: Path) -> Path:
        config = self._load_project_config(project_path)
        validate_project_config(config)
        output_path = (
            _project_reports_dir(config)
            / f"evaluator-setup-{config.project.name}-{config.project.version}.md"
        )
        return export_evaluator_setup(config, output_path)

    def sync_judge_evaluators(
        self,
        project_path: Path,
        *,
        dry_run: bool = False,
        audit: bool = False,
        score_results: list[ScoreConfigSyncResult] | None = None,
    ) -> EvaluatorSetupResult:
        config = self._load_project_config(project_path)
        validate_project_config(config)
        effective_score_results = (
            score_results
            if score_results is not None
            else self.langfuse_client.sync_score_configs(
                config,
                progress=self.progress,
                dry_run=dry_run,
            )
        )
        binding_path = config.judge_setup.binding_path or (
            Path("configs/langfuse/evaluator_bindings") / f"{config.project.name}.yaml"
        )
        bindings = load_evaluator_bindings(binding_path)
        if audit:
            return audit_judge_evaluator_setup(
                config,
                self.langfuse_client,
                effective_score_results,
                bindings=bindings,
                progress=self.progress,
            )
        if dry_run:
            return plan_judge_evaluator_setup(
                config,
                self.langfuse_client,
                effective_score_results,
                bindings=bindings,
                progress=self.progress,
            )
        return apply_judge_evaluator_setup(
            config,
            self.langfuse_client,
            effective_score_results,
            progress=self.progress,
        )

    def sync_annotation_queue(
        self,
        project_path: Path,
        *,
        dry_run: bool = False,
        score_results: list[ScoreConfigSyncResult] | None = None,
    ) -> AnnotationQueueSyncResult:
        config = self._load_project_config(project_path)
        validate_project_config(config)
        effective_score_results = (
            score_results
            if score_results is not None
            else self.langfuse_client.sync_score_configs(
                config,
                progress=self.progress,
                dry_run=dry_run,
            )
            if config.human_review.enabled and config.human_review.queue_ownership == "managed_by_harness"
            else []
        )
        return sync_annotation_queue(
            config,
            self.langfuse_client,
            effective_score_results,
            store=self.annotation_queue_store,
            dry_run=dry_run,
        )

    def run(self, project_path: Path, mode: str, **kwargs: object) -> RunResult:
        if mode not in {"baseline", "candidate"}:
            raise ConfigError(
                f"Unsupported run mode {mode!r}; expected baseline or candidate."
            )

        config = self._load_project_config(project_path)
        validate_project_config(config)
        items = self._validate_dataset(config)
        skip_sync = bool(kwargs.get("skip_sync", False))
        if skip_sync:
            dataset_sync = self._skip_sync_dataset_result(config, items)
        else:
            dataset_sync = self.langfuse_client.sync_dataset(
                config.dataset,
                items,
                progress=self.progress,
            )
            self.langfuse_client.sync_score_configs(config, progress=self.progress)
        if mode == "baseline":
            result = self._run_baseline(config, items, dataset_sync)
        else:
            baseline_selector = _required_str(kwargs.get("baseline"), "--baseline")
            result = self._run_candidate(
                config,
                items,
                dataset_sync,
                candidate_name=_required_str(kwargs.get("candidate"), "--candidate"),
                baseline_selector=baseline_selector,
            )
        if (
            kwargs.get("select_human_review", True)
            and config.human_review.enabled
            and result.completed_count > 0
        ):
            review = self.select_review(
                project_path,
                result.run_id,
                skip_sync=skip_sync,
            )
            return RunResult(
                run_id=result.run_id,
                run_type=result.run_type,
                completed_count=result.completed_count,
                failed_count=result.failed_count,
                baseline_reference=result.baseline_reference,
                review_selection=review,
                model_output_targeting_status=result.model_output_targeting_status,
                model_output_targeting_message=result.model_output_targeting_message,
            )
        return result

    def mixed_variant_axes(
        self,
        project_path: Path,
        candidate_name: str,
    ) -> list[str]:
        config = self._load_project_config(project_path)
        validate_project_config(config)
        candidate = self._candidate_by_name(config, candidate_name)
        axes: list[str] = []
        if model_identity(config.baseline) != model_identity(candidate):
            axes.append("model")
        if prompt_identity_for_model(config, candidate) != prompt_identity_for_model(
            config,
            config.baseline,
        ):
            axes.append("prompt")
        if generation_parameter_hash(config.baseline) != generation_parameter_hash(candidate):
            axes.append("params")
        return axes

    def select_review(
        self,
        project_path: Path,
        run_id: str,
        *,
        sample_strategy: SampleStrategy | None = None,
        skip_sync: bool = False,
    ) -> ReviewSelectionResult:
        if sample_strategy is not None and sample_strategy not in {"stable", "random"}:
            raise ConfigError("sample_strategy must be stable or random")
        config = self._load_project_config(project_path)
        validate_project_config(config)
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
            self.langfuse_client.sync_score_configs(config, progress=self.progress)
            if (
                config.human_review.queue_ownership == "managed_by_harness"
                and not skip_sync
            )
            else []
        )
        with self.progress.task("Resolving annotation queue", total=None):
            queue = (
                self._resolve_annotation_queue_without_sync(config)
                if skip_sync
                else resolve_annotation_queue(
                    config,
                    self.langfuse_client,
                    score_results,
                    store=self.annotation_queue_store,
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
        with self.progress.task("Fetching review traces", total=None):
            traces = self.langfuse_client.traces_for_run(
                run_id,
                dataset_names=dataset_names or None,
            )
        trace_ids = [
            str(trace["trace_id"])
            for trace in traces
            if trace.get("trace_id") is not None
        ]
        scores = self.langfuse_client.fetch_scores(
            run_id,
            trace_ids=trace_ids,
            progress=self.progress,
        )
        candidates = [
            ReviewCandidate.from_trace(trace, scores=scores)
            for trace in traces
        ]
        with self.progress.task("Checking existing review items", total=None):
            existing_review_trace_ids = self.langfuse_client.annotation_queue_object_ids(
                queue.queue_id
            )
        unqueued_candidates = [
            candidate
            for candidate in candidates
            if candidate.trace_id not in existing_review_trace_ids
        ]
        dataset_name = (
            str(traces[0].get("metadata", {}).get("dataset_name"))
            if traces
            else config.dataset.langfuse_dataset_name or "unknown"
        )
        dataset_version = (
            str(
                traces[0].get("metadata", {}).get("dataset_compatibility_version")
                or traces[0].get("metadata", {}).get("dataset_version")
            )
            if traces
            else config.dataset.langfuse_dataset_version or "unknown"
        )
        selections = select_review_items(
            unqueued_candidates,
            config.human_review,
            project_name=config.project.name,
            dataset_name=dataset_name,
            dataset_version=dataset_version,
            sample_strategy=sample_strategy,
        )
        payloads = []
        with self.progress.task("Building review payloads", total=len(selections)) as task:
            for selection in selections:
                payloads.append(
                    self.langfuse_client.build_annotation_queue_payload(config, selection)
                )
                task.advance()
        with self.progress.task("Routing review items", total=None):
            routing: AnnotationRoutingResult = self.langfuse_client.route_annotation_items(
                queue.queue_id,
                payloads,
            )
        reasons: dict[str, int] = {}
        for selection in selections:
            reasons[selection.selection_reason] = (
                reasons.get(selection.selection_reason, 0) + 1
            )
        return ReviewSelectionResult(
            selected_count=len(selections),
            queued_count=routing.queued_count,
            skipped_duplicate_count=routing.skipped_duplicate_count,
            queue_id=routing.queue_id,
            queue_ownership=str(queue.ownership),
            reasons=reasons,
        )

    def _resolve_annotation_queue_without_sync(
        self,
        config: ProjectConfig,
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
        reference = self.annotation_queue_store.load(
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
                self.annotation_queue_store.path_for(
                    config.project.name,
                    config.project.version,
                    reference.review_policy_version,
                )
            ),
            message="using existing annotation queue reference",
        )

    def export(
        self,
        project_path: Path,
        run_id: str,
        fmt: str,
        *,
        expected_count: int | None = None,
    ) -> ExportResult:
        if fmt != "csv":
            raise ConfigError(f"Unsupported export format: {fmt}")
        config = self._load_project_config(project_path)
        dataset_names = [
            name
            for name in [
                config.dataset.langfuse_dataset_name,
                config.dataset.langfuse_dataset_id,
            ]
            if name
        ]
        with self.progress.task("Fetching traces", total=None):
            traces = self.langfuse_client.traces_for_run(
                run_id,
                dataset_names=dataset_names or None,
                expected_count=expected_count,
            )
        trace_ids = [
            str(trace["trace_id"])
            for trace in traces
            if trace.get("trace_id") is not None
        ]
        scores = self.langfuse_client.fetch_scores(
            run_id,
            trace_ids=trace_ids,
            progress=self.progress,
        )
        output_path = _project_reports_dir(config) / f"{run_id}.csv"
        return export_summary(
            traces,
            output_path,
            scores=scores,
            progress=self.progress,
        )

    def campaign(
        self,
        project_path: Path,
        *,
        skip_sync: bool = False,
        select_human_review: bool = True,
        no_report: bool = False,
        overwrite: bool = False,
        report_format: str = "excel",
        confirm_mixed_variant: bool = False,
        on_run_start: Callable[[str, str], None] | None = None,
    ) -> CampaignRunResult:
        config = self._load_project_config(project_path)
        validate_project_config(config)
        selections = campaign_candidate_selections(config)
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
        baseline_run = self.run(
            project_path,
            "baseline",
            select_human_review=select_human_review,
            skip_sync=skip_sync,
        )
        csv_reports: list[ExportResult] = []
        if not no_report:
            csv_reports.append(
                self.export(
                    project_path,
                    baseline_run.run_id,
                    "csv",
                    expected_count=baseline_run.completed_count + baseline_run.failed_count,
                )
            )

        candidate_runs: list[CampaignCandidateRun] = []
        for candidate_name in included_names:
            try:
                if on_run_start is not None:
                    on_run_start("candidate", candidate_name)
                if not confirm_mixed_variant:
                    axes = self.mixed_variant_axes(project_path, candidate_name)
                    if "prompt" in axes and len(axes) > 1:
                        raise ConfigError(
                            "Candidate variant changes multiple comparison axes: "
                            + ", ".join(axes)
                            + ". Pass --confirm-mixed-variant to continue."
                        )
                candidate_result = self.run(
                    project_path,
                    "candidate",
                    candidate=candidate_name,
                    baseline=baseline_run.run_id,
                    select_human_review=select_human_review,
                    skip_sync=skip_sync,
                )
                csv_report = None
                if not no_report:
                    csv_report = self.export(
                        project_path,
                        candidate_result.run_id,
                        "csv",
                        expected_count=(
                            candidate_result.completed_count
                            + candidate_result.failed_count
                        ),
                    )
                    csv_reports.append(csv_report)
                candidate_runs.append(
                    CampaignCandidateRun(
                        candidate_name=candidate_name,
                        run_result=candidate_result,
                        csv_report=csv_report,
                        status="completed",
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

        excel_report = None
        final_reports: list[ComparisonReportOutput] = []
        warnings: list[str] = []
        if not no_report:
            try:
                final_reports = create_comparison_reports(
                    baseline_run_id=baseline_run.run_id,
                    reports_dir=_project_reports_dir(config),
                    formats=report_format,
                    overwrite=overwrite,
                )
                excel_report = next(
                    (report for report in final_reports if report.format == "excel"),
                    None,
                )
                for report in final_reports:
                    warnings.extend(report.warnings)
            except HarnessError as exc:
                warnings.append(str(exc))

        return CampaignRunResult(
            baseline_run=baseline_run,
            candidate_runs=candidate_runs,
            skipped_candidates=skipped,
            csv_reports=csv_reports,
            excel_report=excel_report,
            warnings=warnings,
            final_reports=final_reports,
        )

    def _validate_dataset(self, config: ProjectConfig) -> list[DatasetItem]:
        if config.dataset.kind == DatasetKind.LANGFUSE:
            if not config.dataset.langfuse_dataset_name:
                raise ConfigError("Langfuse datasets require langfuse_dataset_name")
            return []
        if config.dataset.path is None:
            raise ConfigError("Local datasets require path")
        return load_dataset(config.dataset.path)

    def _progress_items(
        self,
        description: str,
        items: list[DatasetItem],
    ) -> Any:
        with self.progress.task(description, total=len(items)) as task:
            for item in items:
                try:
                    yield item
                finally:
                    task.advance()

    def _generate_with_optional_langfuse_generation(
        self,
        provider: ModelProvider,
        request: ModelRequest,
        *,
        model_config: ModelConfig,
        prompt: str,
    ) -> Any:
        if not self._uses_manual_generation_observation(provider):
            return provider.generate(request)
        with self.langfuse_client.generation_span(
            name="OpenAI-generation",
            input=prompt,
            metadata=final_output_metadata(request.metadata),
            model=model_config.model,
            model_parameters=request.params,
            session_id=str(request.metadata.get("item_comparison_session_id") or ""),
        ) as generation_observation:
            response = provider.generate(request)
            self.langfuse_client.update_generation_span(
                generation_observation,
                response,
            )
            return response

    def _uses_manual_generation_observation(self, provider: ModelProvider) -> bool:
        return bool(
            getattr(provider, "uses_manual_langfuse_generation", False)
            and self.langfuse_client.supports_observation_spans()
        )

    def _run_baseline(
        self,
        config: ProjectConfig,
        items: list[DatasetItem],
        dataset_sync: DatasetSyncResult,
    ) -> RunResult:
        provider: ModelProvider = self.provider_factory(config.baseline)
        run_id = f"baseline-{uuid4().hex[:12]}"
        run_name = f"{config.project.name}-{config.project.version}-{run_id}"
        now = _utc_now()
        fingerprint = build_baseline_fingerprint(
            config,
            dataset_name=dataset_sync.name,
            dataset_version=dataset_sync.compatibility_version,
        )
        reference = BaselineReference(
            baseline_run_id=run_id,
            langfuse_run_name=run_name,
            created_at=now,
            **fingerprint_metadata(fingerprint),
        )

        self.langfuse_client.create_run(
            run_id=run_id,
            run_name=run_name,
            run_type="baseline",
            project=config.project.name,
            metadata={
                **fingerprint_metadata(fingerprint),
                **scenario_metadata(config),
                "baseline_run_id": run_id,
                "created_at": now,
            },
        )

        completed = 0
        failed = 0
        baseline_prompt_ref = config.task_prompt
        for item in self._progress_items("Running baseline items", items):
            trace_id = self.langfuse_client.create_trace_id(f"{run_id}:{item.item_id}")
            trace_name = self._trace_name(config, run_type="baseline", item=item)
            rendered_prompt = self._render_prompt_payload(baseline_prompt_ref, item)
            prompt = rendered_prompt.display_text
            session_inputs = self._session_identity_inputs(
                config=config,
                item=item,
                dataset_sync=dataset_sync,
                baseline_anchor=run_id,
            )
            session_id = item_comparison_session_id(session_inputs)
            request = ModelRequest(
                prompt=prompt,
                params=config.baseline.parameters.model_dump(mode="json", exclude_none=True),
                metadata=self._request_metadata(
                    config=config,
                    model_config=config.baseline,
                    item=item,
                    run_id=run_id,
                    run_type="baseline",
                    trace_id=trace_id,
                    trace_name=trace_name,
                    dataset_sync=dataset_sync,
                    fingerprint=fingerprint,
                    rendered_prompt=rendered_prompt,
                    session_id=session_id,
                    session_inputs=session_inputs,
                ),
                rendered_prompt=rendered_prompt,
            )
            parent_metadata = parent_observation_metadata(request.metadata)
            with self.langfuse_client.trace_span(
                trace_id=trace_id,
                name=trace_name,
                input=item.input,
                metadata=parent_metadata,
                session_id=session_id,
            ) as parent_observation:
                parent_observation_id = self.langfuse_client.observation_id(
                    parent_observation
                )
                if parent_observation_id:
                    request.metadata["parent_observation_id"] = parent_observation_id
                    parent_metadata["parent_observation_id"] = parent_observation_id
                uses_manual_generation = self._uses_manual_generation_observation(provider)
                try:
                    self._validate_provider_prompt_roles(config.baseline, rendered_prompt)
                    response = self._generate_with_optional_langfuse_generation(
                        provider,
                        request,
                        model_config=config.baseline,
                        prompt=prompt,
                    )
                    completed += 1
                    retry_count = int(response.raw.get("retry_count", 0))
                    trace = self._trace_payload(
                        config=config,
                        item=item,
                        run_id=run_id,
                        trace_id=trace_id,
                        trace_name=trace_name,
                        response=response,
                        prompt=prompt,
                        retry_count=retry_count,
                        error=None,
                        dataset_sync=dataset_sync,
                        fingerprint=fingerprint,
                        rendered_prompt=rendered_prompt,
                        observation_role=(
                            RUN_ITEM_ROLE if uses_manual_generation else MODEL_OUTPUT_ROLE
                        ),
                        session_id=session_id,
                        session_inputs=session_inputs,
                    )
                    if self.langfuse_client.update_trace_span(parent_observation, trace):
                        trace["_live_observation_logged"] = True
                    self.langfuse_client.log_trace(trace)
                    self.langfuse_client.record_dataset_run_item(
                        dataset_sync=dataset_sync,
                        item_id=item.item_id,
                        run_name=run_id,
                        trace_id=trace_id,
                        observation_id=parent_observation_id,
                        metadata=trace["metadata"],
                    )
                    self.langfuse_client.enqueue_baseline_evaluator_payload(
                        {
                            "run_id": run_id,
                            "trace_id": trace_id,
                            "item_id": item.item_id,
                            "input": item.input,
                            "output": response.output,
                            "ground_truth": item.ground_truth,
                            "evaluators": [
                                {
                                    "name": evaluator.name,
                                    "version": evaluator.version,
                                    "score_config": (
                                        f"{config.project.score_config_prefix}{evaluator.score.name}"
                                        if evaluator.score.managed_by_harness
                                        else evaluator.score.langfuse_score_config_id
                                    ),
                                }
                                for evaluator in config.evaluators
                            ],
                        }
                    )
                except Exception as exc:
                    failed += 1
                    trace = self._trace_payload(
                        config=config,
                        item=item,
                        run_id=run_id,
                        trace_id=trace_id,
                        trace_name=trace_name,
                        response=None,
                        prompt=prompt,
                        retry_count=0,
                        error=str(exc),
                        dataset_sync=dataset_sync,
                        fingerprint=fingerprint,
                        rendered_prompt=rendered_prompt,
                        observation_role=RUN_ITEM_ROLE,
                        session_id=session_id,
                        session_inputs=session_inputs,
                    )
                    if self.langfuse_client.update_trace_span(parent_observation, trace):
                        trace["_live_observation_logged"] = True
                    self.langfuse_client.log_trace(trace)
                    self.langfuse_client.record_dataset_run_item(
                        dataset_sync=dataset_sync,
                        item_id=item.item_id,
                        run_name=run_id,
                        trace_id=trace_id,
                        observation_id=parent_observation_id,
                        metadata=trace["metadata"],
                    )

        self.baseline_registry.record(run_id, fingerprint, reference)
        self.langfuse_client.record_baseline_reference(run_id, reference)
        targeting = self._diagnose_run_model_output_targeting(
            run_id=run_id,
            completed_count=completed,
        )
        return RunResult(
            run_id=run_id,
            run_type="baseline",
            completed_count=completed,
            failed_count=failed,
            baseline_reference=reference,
            model_output_targeting_status=targeting.status,
            model_output_targeting_message=targeting.message,
        )

    def _run_candidate(
        self,
        config: ProjectConfig,
        items: list[DatasetItem],
        dataset_sync: DatasetSyncResult,
        *,
        candidate_name: str,
        baseline_selector: str,
    ) -> RunResult:
        candidate = self._candidate_by_name(config, candidate_name)
        fingerprint = build_baseline_fingerprint(
            config,
            dataset_name=dataset_sync.name,
            dataset_version=dataset_sync.compatibility_version,
        )
        baseline_reference = self.langfuse_client.lookup_baseline(
            selector=baseline_selector,
            fingerprint=fingerprint,
        )
        if baseline_reference is None:
            try:
                baseline_run_id = self.baseline_registry.resolve(
                    baseline_selector,
                    fingerprint,
                )
            except ConfigError:
                baseline_run_id = ""
            else:
                baseline_reference = (
                    self.baseline_registry.reference_for(baseline_run_id)
                    or self.langfuse_client.baseline_references.get(baseline_run_id)
                )
        baseline_run_id = (
            baseline_reference.baseline_run_id
            if baseline_reference is not None
            else baseline_selector
        )
        if baseline_reference is None:
            raise ConfigError(f"No baseline reference found for {baseline_run_id}")

        provider: ModelProvider = self.provider_factory(candidate)
        run_id = f"candidate-{uuid4().hex[:12]}"
        run_name = f"{config.project.name}-{config.project.version}-{candidate.name}-{run_id}"
        parameter_hash = _parameter_hash(candidate)
        baseline_prompt_identity = prompt_identity_for_model(config, config.baseline)
        candidate_prompt_identity = prompt_identity_for_model(config, candidate)
        candidate_parameter_identity = parameter_identity(candidate)
        candidate_generation_parameter_hash = generation_parameter_hash(candidate)
        candidate_variant_identity = variant_identity(config, candidate)
        self.langfuse_client.create_run(
            run_id=run_id,
            run_name=run_name,
            run_type="candidate",
            project=config.project.name,
            candidate=candidate.name,
            baseline_run_id=baseline_run_id,
            metadata={
                **fingerprint_metadata(fingerprint),
                **scenario_metadata(config),
                "candidate": candidate.name,
                "parameter_hash": parameter_hash,
                "parameter_identity": candidate_parameter_identity,
                "generation_parameter_hash": candidate_generation_parameter_hash,
                "variant_identity": candidate_variant_identity,
                "prompt_identity": candidate_prompt_identity,
                "baseline_prompt_identity": baseline_prompt_identity,
                "candidate_prompt_identity": candidate_prompt_identity,
            },
        )

        completed = 0
        failed = 0
        candidate_prompt_ref = candidate.task_prompt or config.task_prompt
        for item in self._progress_items("Running candidate items", items):
            trace_id = self.langfuse_client.create_trace_id(f"{run_id}:{item.item_id}")
            trace_name = self._trace_name(
                config,
                run_type="candidate",
                item=item,
                model_config=candidate,
            )
            rendered_prompt = self._render_prompt_payload(candidate_prompt_ref, item)
            prompt = rendered_prompt.display_text
            session_inputs = self._session_identity_inputs(
                config=config,
                item=item,
                dataset_sync=dataset_sync,
                baseline_anchor=baseline_reference.baseline_run_id,
            )
            session_id = item_comparison_session_id(session_inputs)
            request = ModelRequest(
                prompt=prompt,
                params=candidate.parameters.model_dump(mode="json", exclude_none=True),
                metadata={
                    **self._request_metadata(
                        config=config,
                        model_config=candidate,
                        item=item,
                        run_id=run_id,
                        run_type="candidate",
                        trace_id=trace_id,
                        trace_name=trace_name,
                        dataset_sync=dataset_sync,
                        fingerprint=fingerprint,
                        rendered_prompt=rendered_prompt,
                        session_id=session_id,
                        session_inputs=session_inputs,
                    ),
                    "baseline_run_id": baseline_run_id,
                },
                rendered_prompt=rendered_prompt,
            )
            parent_metadata = parent_observation_metadata(request.metadata)
            with self.langfuse_client.trace_span(
                trace_id=trace_id,
                name=trace_name,
                input=item.input,
                metadata=parent_metadata,
                session_id=session_id,
            ) as parent_observation:
                parent_observation_id = self.langfuse_client.observation_id(
                    parent_observation
                )
                if parent_observation_id:
                    request.metadata["parent_observation_id"] = parent_observation_id
                    parent_metadata["parent_observation_id"] = parent_observation_id
                uses_manual_generation = self._uses_manual_generation_observation(provider)
                try:
                    self._validate_provider_prompt_roles(candidate, rendered_prompt)
                    response = self._generate_with_optional_langfuse_generation(
                        provider,
                        request,
                        model_config=candidate,
                        prompt=prompt,
                    )
                    completed += 1
                    retry_count = int(response.raw.get("retry_count", 0))
                    trace = self._trace_payload(
                        config=config,
                        item=item,
                        run_id=run_id,
                        trace_id=trace_id,
                        trace_name=trace_name,
                        response=response,
                        prompt=prompt,
                        retry_count=retry_count,
                        error=None,
                        model_config=candidate,
                        dataset_sync=dataset_sync,
                        fingerprint=fingerprint,
                        baseline_reference=baseline_reference,
                        parameter_hash=parameter_hash,
                        rendered_prompt=rendered_prompt,
                        observation_role=(
                            RUN_ITEM_ROLE if uses_manual_generation else MODEL_OUTPUT_ROLE
                        ),
                        session_id=session_id,
                        session_inputs=session_inputs,
                    )
                    if self.langfuse_client.update_trace_span(parent_observation, trace):
                        trace["_live_observation_logged"] = True
                    self.langfuse_client.log_trace(trace)
                    self.langfuse_client.record_dataset_run_item(
                        dataset_sync=dataset_sync,
                        item_id=item.item_id,
                        run_name=run_id,
                        trace_id=trace_id,
                        observation_id=parent_observation_id,
                        metadata=trace["metadata"],
                    )
                    self.langfuse_client.enqueue_candidate_evaluator_payload(
                        {
                            "run_id": run_id,
                            "trace_id": trace_id,
                            "item_id": item.item_id,
                            "input": item.input,
                            "output": response.output,
                            "baseline_output": self.langfuse_client.output_for(
                                run_id=baseline_run_id,
                                item_id=item.item_id,
                            ),
                            "ground_truth": item.ground_truth,
                            "baseline_reference": baseline_reference.model_dump(mode="json"),
                            "prompt_identity": candidate_prompt_identity,
                            "baseline_prompt_identity": baseline_prompt_identity,
                            "candidate_prompt_identity": candidate_prompt_identity,
                            "parameter_identity": candidate_parameter_identity,
                            "generation_parameter_hash": candidate_generation_parameter_hash,
                            "variant_identity": candidate_variant_identity,
                            "evaluators": [
                                {"name": evaluator.name, "version": evaluator.version}
                                for evaluator in config.evaluators
                            ],
                        }
                    )
                except Exception as exc:
                    failed += 1
                    trace = self._trace_payload(
                        config=config,
                        item=item,
                        run_id=run_id,
                        trace_id=trace_id,
                        trace_name=trace_name,
                        response=None,
                        prompt=prompt,
                        retry_count=0,
                        error=str(exc),
                        model_config=candidate,
                        dataset_sync=dataset_sync,
                        fingerprint=fingerprint,
                        baseline_reference=baseline_reference,
                        parameter_hash=parameter_hash,
                        rendered_prompt=rendered_prompt,
                        observation_role=RUN_ITEM_ROLE,
                        session_id=session_id,
                        session_inputs=session_inputs,
                    )
                    if self.langfuse_client.update_trace_span(parent_observation, trace):
                        trace["_live_observation_logged"] = True
                    self.langfuse_client.log_trace(trace)
                    self.langfuse_client.record_dataset_run_item(
                        dataset_sync=dataset_sync,
                        item_id=item.item_id,
                        run_name=run_id,
                        trace_id=trace_id,
                        observation_id=parent_observation_id,
                        metadata=trace["metadata"],
                    )

        targeting = self._diagnose_run_model_output_targeting(
            run_id=run_id,
            completed_count=completed,
        )
        return RunResult(
            run_id=run_id,
            run_type="candidate",
            completed_count=completed,
            failed_count=failed,
            baseline_reference=baseline_reference,
            model_output_targeting_status=targeting.status,
            model_output_targeting_message=targeting.message,
        )

    def _trace_payload(
        self,
        *,
        config: ProjectConfig,
        item: DatasetItem,
        run_id: str,
        trace_id: str,
        trace_name: str,
        response: Any | None,
        prompt: str,
        retry_count: int,
        error: str | None,
        model_config: ModelConfig | None = None,
        dataset_sync: DatasetSyncResult | None = None,
        fingerprint: BaselineFingerprint | None = None,
        baseline_reference: BaselineReference | None = None,
        parameter_hash: str | None = None,
        rendered_prompt: RenderedPrompt | None = None,
        observation_role: str = MODEL_OUTPUT_ROLE,
        session_id: str | None = None,
        session_inputs: SessionIdentityInputs | None = None,
    ) -> dict[str, Any]:
        active_model = model_config or config.baseline
        active_prompt_identity = prompt_identity_for_model(config, active_model)
        prompt_ref = active_model.task_prompt or config.task_prompt
        baseline_prompt_identity = prompt_identity_for_model(config, config.baseline)
        candidate_prompt_identity = (
            active_prompt_identity if baseline_reference is not None else None
        )
        active_parameter_identity = parameter_identity(active_model)
        active_generation_parameter_hash = generation_parameter_hash(active_model)
        active_variant_identity = variant_identity(config, active_model)
        return {
            "trace_id": trace_id,
            "run_id": run_id,
            "session_id": session_id,
            "name": trace_name,
            "input": item.input,
            "output": response.output if response is not None else None,
            "error": error,
            "metadata": {
                **(fingerprint_metadata(fingerprint) if fingerprint else {}),
                "project": config.project.name,
                "project_version": config.project.version,
                **scenario_metadata(config),
                "run_type": "candidate" if baseline_reference is not None else "baseline",
                "test_trace": _is_test_run(),
                "environment": config.project.metadata.get("environment"),
                "project_tags": config.project.metadata.get("tags", []),
                "run_tags": [
                    config.project.name,
                    run_id,
                    active_model.name,
                ],
                "dataset_name": dataset_sync.name if dataset_sync else None,
                "dataset_version": dataset_sync.version if dataset_sync else None,
                "dataset_compatibility_version": (
                    dataset_sync.compatibility_version if dataset_sync else None
                ),
                "dataset_item_id": item.item_id,
                "trace_id": trace_id,
                "trace_name": trace_name,
                "item_comparison_session_id": session_id,
                "item_comparison_session_inputs": (
                    session_inputs.metadata() if session_inputs is not None else None
                ),
                "observation_role": observation_role,
                "langfuse_dataset_item_id": (
                    f"{dataset_sync.name}:{item.item_id}" if dataset_sync else None
                ),
                "dataset_run_item_id": (
                    f"{run_id}:{item.item_id}" if dataset_sync else None
                ),
                "prompt_version": active_prompt_identity["version"],
                "prompt_shape": active_prompt_identity.get("shape"),
                "prompt_roles": active_prompt_identity.get("roles", []),
                **prompt_provenance_metadata(
                    config,
                    artifact_type="task",
                    artifact_name="task_prompt",
                    prompt_ref=prompt_ref,
                ),
                "prompt_identity": active_prompt_identity,
                "baseline_prompt_version": baseline_prompt_identity["version"],
                "baseline_prompt_identity": baseline_prompt_identity,
                "candidate_prompt_version": (
                    candidate_prompt_identity["version"]
                    if candidate_prompt_identity is not None
                    else None
                ),
                "candidate_prompt_identity": candidate_prompt_identity,
                "evaluator_set_id": fingerprint.evaluator_set_id if fingerprint else None,
                "ground_truth": item.ground_truth,
                "provider": active_model.provider.value,
                "model": active_model.model,
                "model_name": active_model.name,
                "temperature": active_model.parameters.temperature,
                "parameter_hash": parameter_hash or _parameter_hash(active_model),
                "parameter_identity": active_parameter_identity,
                "generation_parameter_hash": active_generation_parameter_hash,
                "variant_identity": active_variant_identity,
                "baseline_reference": (
                    baseline_reference.model_dump(mode="json")
                    if baseline_reference is not None
                    else None
                ),
                "retry_count": retry_count,
                "latency_ms": response.latency_ms if response is not None else None,
                "input_tokens": response.input_tokens if response is not None else None,
                "output_tokens": response.output_tokens if response is not None else None,
                "cost_usd": response.cost_usd if response is not None else None,
                "tracing_strategy": (
                    response.raw.get("tracing_strategy") if response is not None else None
                ),
                "manual_fallback_reason": (
                    response.raw.get("manual_fallback_reason") if response is not None else None
                ),
                "provider_tracing_strategy": provider_tracing_metadata(active_model),
            },
            "prompt": prompt,
            "rendered_prompt": (
                rendered_prompt.model_dump(mode="json") if rendered_prompt else None
            ),
            "timestamp": _utc_now(),
        }

    def _request_metadata(
        self,
        *,
        config: ProjectConfig,
        model_config: ModelConfig,
        item: DatasetItem,
        run_id: str,
        run_type: str,
        trace_id: str,
        trace_name: str,
        dataset_sync: DatasetSyncResult,
        fingerprint: BaselineFingerprint,
        rendered_prompt: RenderedPrompt | None = None,
        session_id: str | None = None,
        session_inputs: SessionIdentityInputs | None = None,
    ) -> dict[str, Any]:
        active_prompt_identity = prompt_identity_for_model(config, model_config)
        prompt_ref = model_config.task_prompt or config.task_prompt
        baseline_prompt_identity = prompt_identity_for_model(config, config.baseline)
        candidate_prompt_identity = (
            active_prompt_identity if run_type == "candidate" else None
        )
        active_parameter_identity = parameter_identity(model_config)
        active_generation_parameter_hash = generation_parameter_hash(model_config)
        return {
            "project": config.project.name,
            "project_version": config.project.version,
            **scenario_metadata(config),
            "run_id": run_id,
            "run_type": run_type,
            "item_id": item.item_id,
            "dataset_item_id": item.item_id,
            "dataset_name": dataset_sync.name,
            "dataset_version": dataset_sync.version,
            "dataset_compatibility_version": dataset_sync.compatibility_version,
            "evaluator_set_id": fingerprint.evaluator_set_id,
            "trace_id": trace_id,
            "trace_name": trace_name,
            "item_comparison_session_id": session_id,
            "item_comparison_session_inputs": (
                session_inputs.metadata() if session_inputs is not None else None
            ),
            "prompt_version": active_prompt_identity["version"],
            "prompt_shape": active_prompt_identity.get("shape"),
            "prompt_roles": active_prompt_identity.get("roles", []),
            **prompt_provenance_metadata(
                config,
                artifact_type="task",
                artifact_name="task_prompt",
                prompt_ref=prompt_ref,
            ),
            "prompt_identity": active_prompt_identity,
            "baseline_prompt_version": baseline_prompt_identity["version"],
            "baseline_prompt_identity": baseline_prompt_identity,
            "candidate_prompt_version": (
                candidate_prompt_identity["version"]
                if candidate_prompt_identity is not None
                else None
            ),
            "candidate_prompt_identity": candidate_prompt_identity,
            "parameter_identity": active_parameter_identity,
            "generation_parameter_hash": active_generation_parameter_hash,
            "variant_identity": variant_identity(config, model_config),
            "observation_role": MODEL_OUTPUT_ROLE,
            "rendered_prompt": (
                rendered_prompt.model_dump(mode="json") if rendered_prompt else None
            ),
        }

    def _session_identity_inputs(
        self,
        *,
        config: ProjectConfig,
        item: DatasetItem,
        dataset_sync: DatasetSyncResult,
        baseline_anchor: str,
    ) -> SessionIdentityInputs:
        return SessionIdentityInputs(
            project=config.project.name,
            project_version=config.project.version,
            dataset_name=dataset_sync.name,
            dataset_version=dataset_sync.compatibility_version or dataset_sync.version,
            baseline_anchor=baseline_anchor,
            dataset_item_id=item.item_id,
            source_row=item.source_row,
        )

    def _diagnose_run_model_output_targeting(
        self,
        *,
        run_id: str,
        completed_count: int,
    ):
        if self.langfuse_client.supports_observation_spans():
            from evaluator_harness.model_output_targeting import (
                ModelOutputTargetingDiagnostic,
            )

            return ModelOutputTargetingDiagnostic(
                status="unknown",
                model_output_count=0,
                expected_completed_count=completed_count,
                message=(
                    "Live Langfuse observation spans were emitted. Verify evaluator "
                    "counts in Langfuse; local trace payloads do not include nested "
                    "generation observations."
                ),
            )
        observations = [
            {
                "trace_id": trace.get("trace_id"),
                "name": trace.get("name"),
                "metadata": metadata_with_observation_role(
                    trace.get("metadata") or {},
                    str((trace.get("metadata") or {}).get("observation_role") or RUN_ITEM_ROLE),
                ),
            }
            for trace in self.langfuse_client.traces_for_run(run_id)
        ]
        return diagnose_model_output_targeting(
            observations,
            expected_completed_count=completed_count,
        )

    def _render_prompt(self, path: Path, variables: dict[str, str]) -> str:
        prompt_path = path if path.is_absolute() else Path.cwd() / path
        text = prompt_path.read_text(encoding="utf-8")
        for key, value in variables.items():
            text = text.replace("{{" + key + "}}", value)
        return text

    def _render_prompt_payload(self, prompt_ref: Any, item: DatasetItem) -> RenderedPrompt:
        prompt = parse_prompt_file(prompt_ref.path, version=prompt_ref.version)
        return render_prompt(prompt, self._dataset_row_context(item))

    def _dataset_row_context(self, item: DatasetItem) -> dict[str, Any]:
        return {
            **item.metadata,
            "input": item.input,
            "ground_truth": item.ground_truth,
            "reference_output": item.reference_output,
        }

    def _validate_provider_prompt_roles(
        self,
        model_config: ModelConfig,
        rendered_prompt: RenderedPrompt,
    ) -> None:
        if rendered_prompt.shape != "messages":
            return
        validate_provider_roles(
            model_config.provider,
            [message.role for message in rendered_prompt.messages],
        )

    def _trace_name(
        self,
        config: ProjectConfig,
        *,
        run_type: str,
        item: DatasetItem,
        model_config: ModelConfig | None = None,
    ) -> str:
        prefix = "test/" if _is_test_run() else ""
        if run_type == "candidate" and model_config is not None:
            variant_name = model_config.name
        else:
            variant_name = f"baseline-{config.baseline.name}"
        return f"{prefix}{config.project.name}/{variant_name}"

    def _candidate_by_name(self, config: ProjectConfig, candidate_name: str) -> ModelConfig:
        for candidate in config.candidates:
            if candidate.name == candidate_name:
                return candidate
        raise ConfigError(f"Candidate model config not found: {candidate_name}")


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _required_str(value: object, option_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ConfigError(f"{option_name} is required for candidate runs")
    return value


def _project_reports_dir(config: ProjectConfig) -> Path:
    return Path("reports") / config.project.name


def campaign_candidate_selections(config: ProjectConfig) -> list[CampaignCandidateSelection]:
    selections: list[CampaignCandidateSelection] = []
    for candidate in config.candidates:
        included = candidate.exclude_from_campaign is False
        reason = (
            "exclude-from-campaign=false"
            if included
            else "exclude-from-campaign=true"
        )
        selections.append(
            CampaignCandidateSelection(
                candidate_name=candidate.name,
                included=included,
                reason=reason,
            )
        )
    return selections


def _parameter_hash(config: ModelConfig) -> str:
    payload = {
        "provider": config.provider.value,
        "model": config.model,
        "parameters": config.parameters.model_dump(mode="json", exclude_none=True),
    }
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def model_identity(config: ModelConfig) -> dict[str, str]:
    return {
        "provider": config.provider.value,
        "auth_mode": config.auth_mode.value,
        "model": config.model,
    }


def prompt_identity(prompt_ref: Any) -> dict[str, Any]:
    return prompt_file_identity(Path(prompt_ref.path), prompt_ref.version)


def prompt_identity_for_model(
    config: ProjectConfig,
    model_config: ModelConfig,
) -> dict[str, str]:
    prompt_ref = model_config.task_prompt or config.task_prompt
    return prompt_identity(prompt_ref)


def generation_parameter_hash(config: ModelConfig) -> str:
    payload = config.parameters.model_dump(mode="json", exclude_none=True)
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode("utf-8")).hexdigest()


def parameter_identity(config: ModelConfig) -> dict[str, Any]:
    return config.parameters.model_dump(mode="json", exclude_none=True)


def variant_identity(config: ProjectConfig, model_config: ModelConfig) -> dict[str, Any]:
    return {
        "candidate": model_config.name,
        "model": model_identity(model_config),
        "prompt": prompt_identity_for_model(config, model_config),
        "parameters": model_config.parameters.model_dump(mode="json", exclude_none=True),
        "generation_parameter_hash": generation_parameter_hash(model_config),
    }


def _is_test_run() -> bool:
    return bool(os.getenv("PYTEST_CURRENT_TEST"))
