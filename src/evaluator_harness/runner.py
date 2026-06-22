from __future__ import annotations

import os
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path
from typing import Any

from evaluator_harness.annotation_queues import (
    AnnotationQueueReferenceStore,
    AnnotationQueueSyncResult,
    sync_annotation_queue,
)
from evaluator_harness.baseline_registry import (
    BaselineFingerprint,
    BaselineRegistry,
)
from evaluator_harness.baseline_runs import build_baseline_run_context
from evaluator_harness.campaigns import (
    CampaignCandidateRun as CampaignCandidateRun,
)
from evaluator_harness.campaigns import (
    CampaignCandidateSelection as CampaignCandidateSelection,
)
from evaluator_harness.campaigns import (
    CampaignRunResult as CampaignRunResult,
)
from evaluator_harness.campaigns import (
    campaign_candidate_selections,
    run_campaign,
)
from evaluator_harness.candidate_runs import build_candidate_run_context
from evaluator_harness.certificates import configure_tls_truststore
from evaluator_harness.comparison_reports import (
    create_comparison_reports,
)
from evaluator_harness.config import (
    BaselineReference,
    DatasetItem,
    DatasetKind,
    ModelConfig,
    ProjectConfig,
    load_env_file,
    load_layered_env_files,
    load_project_config,
    project_env_file_path,
    validate_project_config,
)
from evaluator_harness.dataset_loader import dataset_compatibility_version, load_dataset
from evaluator_harness.errors import ConfigError
from evaluator_harness.evaluator_bindings import load_evaluator_bindings
from evaluator_harness.evaluators import (
    evaluator_score_summary,
    evaluator_target_summary,
    export_evaluator_setup,
    render_judge_prompts,
)
from evaluator_harness.exports import ExportResult
from evaluator_harness.langfuse_evaluator_setup import (
    EvaluatorSetupResult,
    apply_judge_evaluator_setup,
    audit_judge_evaluator_setup,
    plan_judge_evaluator_setup,
)
from evaluator_harness.langfuse_gateways import (
    LangfuseGateway,
    build_default_langfuse_gateway,
    build_langfuse_gateway_from_env,
)
from evaluator_harness.langfuse_records import (
    DatasetSyncResult,
    ScoreConfigSyncResult,
    format_langfuse_warning,
)
from evaluator_harness.model_output_targeting import (
    MODEL_OUTPUT_ROLE,
    RUN_ITEM_ROLE,
    diagnose_model_output_targeting,
    final_output_metadata,
    metadata_with_observation_role,
    parent_observation_metadata,
)
from evaluator_harness.progress import NullProgressReporter, ProgressReporter
from evaluator_harness.prompt_sync import (
    PromptSyncReport,
    sync_project_prompts,
)
from evaluator_harness.prompts import (
    RenderedPrompt,
    parse_prompt_file,
    render_prompt,
)
from evaluator_harness.providers import create_provider
from evaluator_harness.providers.base import (
    ModelProvider,
    ModelRequest,
    validate_provider_roles,
)
from evaluator_harness.review_routing import (
    ReviewSelectionResult,
    select_and_route_review_items,
)
from evaluator_harness.review_selection import SampleStrategy
from evaluator_harness.run_exports import (
    export_run_summary,
)
from evaluator_harness.run_exports import (
    project_reports_dir as _project_reports_dir,
)
from evaluator_harness.run_metadata import (
    _is_test_run,
    build_request_metadata,
    build_trace_payload,
    generation_parameter_hash,
    model_identity,
    prompt_identity_for_model,
)
from evaluator_harness.run_metadata import (
    prompt_identity as prompt_identity,
)
from evaluator_harness.run_metadata import (
    variant_identity as variant_identity,
)
from evaluator_harness.runner_records import (
    RunItemExecutionPlan,
    RunItemExecutionResult,
    RunResult,
    SyncAllResult,
    ValidationResult,
)
from evaluator_harness.session_identity import (
    SessionIdentityInputs,
    item_comparison_session_id,
)


class ExperimentRunner:
    def __init__(
        self,
        *,
        langfuse_gateway: LangfuseGateway | None = None,
        provider_factory: Any | None = None,
        baseline_registry: BaselineRegistry | None = None,
        progress: ProgressReporter | None = None,
    ) -> None:
        configure_tls_truststore()
        load_env_file()
        self._langfuse_gateway_provided = langfuse_gateway is not None
        self.langfuse_gateway = langfuse_gateway or build_default_langfuse_gateway()
        self.provider_factory = provider_factory or create_provider
        self.baseline_registry = baseline_registry or BaselineRegistry()
        self.annotation_queue_store = AnnotationQueueReferenceStore()
        self.progress = progress or NullProgressReporter()

    def _current_langfuse_warning_messages(self) -> tuple[str, ...]:
        warnings = self._current_langfuse_warnings()
        return tuple(format_langfuse_warning(warning) for warning in warnings)

    def _current_langfuse_warnings(self) -> tuple[Any, ...]:
        current = getattr(self.langfuse_gateway, "current_langfuse_warnings", None)
        if not callable(current):
            return ()
        warnings = current()
        if isinstance(warnings, tuple):
            return warnings
        if isinstance(warnings, list):
            return tuple(warnings)
        return ()

    def _langfuse_status(self, warnings: tuple[str, ...]) -> str:
        return "complete-with-warnings" if warnings else "complete"

    def _require_dataset_identity(self, dataset_sync: DatasetSyncResult) -> None:
        if not dataset_sync.name:
            raise ConfigError(
                "Dataset identity is required before running Langfuse-backed "
                "baseline or candidate workflows."
            )

    def _load_project_config(self, project_path: Path) -> ProjectConfig:
        config = load_project_config(project_path)
        load_layered_env_files(
            root_env_file=".env",
            project_env_file=project_env_file_path(config.project.name),
        )
        if not self._langfuse_gateway_provided and os.getenv(
            "EVALUATOR_HARNESS_LIVE"
        ) in {"1", "true", "TRUE", "yes"}:
            self.langfuse_gateway = build_langfuse_gateway_from_env()
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
                f"{evaluator.name}/{evaluator.version}"
                for evaluator in config.evaluators
            ],
            evaluator_targets=[
                evaluator_target_summary(evaluator) for evaluator in config.evaluators
            ],
            score_targets=[
                evaluator_score_summary(config, evaluator)
                for evaluator in config.evaluators
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

    def sync_dataset(
        self, project_path: Path, *, dry_run: bool = False
    ) -> DatasetSyncResult:
        config = self._load_project_config(project_path)
        validate_project_config(config)
        items = self._validate_dataset(config)
        return self.langfuse_gateway.sync_dataset(
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
        return self.langfuse_gateway.sync_score_configs(
            config,
            progress=self.progress,
            dry_run=dry_run,
        )

    def _skip_sync_dataset_result(
        self,
        config: ProjectConfig,
        items: list[DatasetItem],
    ) -> DatasetSyncResult:
        name = (
            config.dataset.langfuse_dataset_name or config.dataset.langfuse_dataset_id
        )
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
            self.langfuse_gateway,
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
        queue_description = (
            "Checking annotation queue" if dry_run else "Syncing annotation queue"
        )
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
            else self.langfuse_gateway.sync_score_configs(
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
                self.langfuse_gateway,
                effective_score_results,
                bindings=bindings,
                progress=self.progress,
            )
        if dry_run:
            return plan_judge_evaluator_setup(
                config,
                self.langfuse_gateway,
                effective_score_results,
                bindings=bindings,
                progress=self.progress,
            )
        return apply_judge_evaluator_setup(
            config,
            self.langfuse_gateway,
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
            else self.langfuse_gateway.sync_score_configs(
                config,
                progress=self.progress,
                dry_run=dry_run,
            )
            if config.human_review.enabled
            and config.human_review.queue_ownership == "managed_by_harness"
            else []
        )
        return sync_annotation_queue(
            config,
            self.langfuse_gateway,
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
        drain_warnings = getattr(self.langfuse_gateway, "drain_langfuse_warnings", None)
        if callable(drain_warnings):
            drain_warnings()
        items = self._validate_dataset(config)
        skip_sync = bool(kwargs.get("skip_sync", False))
        if skip_sync:
            dataset_sync = self._skip_sync_dataset_result(config, items)
        else:
            dataset_sync = self.langfuse_gateway.sync_dataset(
                config.dataset,
                items,
                progress=self.progress,
            )
            self.langfuse_gateway.sync_score_configs(config, progress=self.progress)
        self._require_dataset_identity(dataset_sync)
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
            return replace(result, review_selection=review)
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
        if generation_parameter_hash(config.baseline) != generation_parameter_hash(
            candidate
        ):
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
        config = self._load_project_config(project_path)
        validate_project_config(config)
        return select_and_route_review_items(
            config=config,
            run_id=run_id,
            langfuse_gateway=self.langfuse_gateway,
            annotation_queue_store=self.annotation_queue_store,
            progress=self.progress,
            sample_strategy=sample_strategy,
            skip_sync=skip_sync,
        )

    def export(
        self,
        project_path: Path,
        run_id: str,
        fmt: str,
        *,
        expected_count: int | None = None,
        strict_linkage: bool = True,
    ) -> ExportResult:
        config = self._load_project_config(project_path)
        return export_run_summary(
            config=config,
            run_id=run_id,
            fmt=fmt,
            langfuse_gateway=self.langfuse_gateway,
            progress=self.progress,
            warning_provider=self._current_langfuse_warnings,
            expected_count=expected_count,
            strict_linkage=strict_linkage,
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
        return run_campaign(
            config=config,
            project_path=project_path,
            run=self.run,
            export=self.export,
            mixed_variant_axes=self.mixed_variant_axes,
            create_reports=create_comparison_reports,
            select_candidates=campaign_candidate_selections,
            skip_sync=skip_sync,
            select_human_review=select_human_review,
            no_report=no_report,
            overwrite=overwrite,
            report_format=report_format,
            confirm_mixed_variant=confirm_mixed_variant,
            on_run_start=on_run_start,
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
        with self.langfuse_gateway.generation_span(
            name="OpenAI-generation",
            input=prompt,
            metadata=final_output_metadata(request.metadata),
            model=model_config.model,
            model_parameters=request.params,
            session_id=str(request.metadata.get("item_comparison_session_id") or ""),
        ) as generation_observation:
            response = provider.generate(request)
            self.langfuse_gateway.update_generation_span(
                generation_observation,
                response,
            )
            return response

    def _uses_manual_generation_observation(self, provider: ModelProvider) -> bool:
        return bool(
            getattr(provider, "uses_manual_langfuse_generation", False)
            and self.langfuse_gateway.supports_observation_spans()
        )

    def _run_baseline(
        self,
        config: ProjectConfig,
        items: list[DatasetItem],
        dataset_sync: DatasetSyncResult,
    ) -> RunResult:
        context = build_baseline_run_context(config=config, dataset_sync=dataset_sync)
        provider: ModelProvider = self.provider_factory(config.baseline)

        self.langfuse_gateway.create_run(
            run_id=context.run_id,
            run_name=context.run_name,
            run_type="baseline",
            project=config.project.name,
            metadata=context.run_metadata,
        )

        completed = 0
        failed = 0
        baseline_plan = RunItemExecutionPlan(
            run_id=context.run_id,
            run_type="baseline",
            model_config=config.baseline,
            provider=provider,
            prompt_ref=config.task_prompt,
            dataset_sync=dataset_sync,
            fingerprint=context.fingerprint,
            baseline_anchor=context.run_id,
        )
        for item in self._progress_items("Running baseline items", items):
            result = self._execute_run_item(config, item, baseline_plan)
            if result.completed:
                completed += 1
                if result.response is None:
                    continue
                self.langfuse_gateway.enqueue_baseline_evaluator_payload(
                    self._baseline_evaluator_payload(config, result)
                )
            elif result.failed:
                failed += 1

        self.baseline_registry.record(
            context.run_id,
            context.fingerprint,
            context.reference,
        )
        self.langfuse_gateway.record_baseline_reference(
            context.run_id,
            context.reference,
        )
        targeting = self._diagnose_run_model_output_targeting(
            run_id=context.run_id,
            completed_count=completed,
        )
        langfuse_warnings = self._current_langfuse_warning_messages()
        return RunResult(
            run_id=context.run_id,
            run_type="baseline",
            completed_count=completed,
            failed_count=failed,
            baseline_reference=context.reference,
            model_output_targeting_status=targeting.status,
            model_output_targeting_message=targeting.message,
            langfuse_status=self._langfuse_status(langfuse_warnings),
            langfuse_warnings=langfuse_warnings,
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
        context = build_candidate_run_context(
            config=config,
            dataset_sync=dataset_sync,
            candidate_name=candidate_name,
            baseline_selector=baseline_selector,
            langfuse_gateway=self.langfuse_gateway,
            baseline_registry=self.baseline_registry,
            warning_messages=self._current_langfuse_warning_messages(),
        )
        provider: ModelProvider = self.provider_factory(context.candidate)
        self.langfuse_gateway.create_run(
            run_id=context.run_id,
            run_name=context.run_name,
            run_type="candidate",
            project=config.project.name,
            candidate=context.candidate.name,
            baseline_run_id=context.baseline_run_id,
            metadata=context.run_metadata,
        )

        completed = 0
        failed = 0
        candidate_plan = RunItemExecutionPlan(
            run_id=context.run_id,
            run_type="candidate",
            model_config=context.candidate,
            provider=provider,
            prompt_ref=context.candidate.task_prompt or config.task_prompt,
            dataset_sync=dataset_sync,
            fingerprint=context.fingerprint,
            baseline_anchor=context.baseline_reference.baseline_run_id,
            baseline_reference=context.baseline_reference,
            parameter_hash=context.parameter_hash,
            request_metadata={"baseline_run_id": context.baseline_run_id},
        )
        for item in self._progress_items("Running candidate items", items):
            result = self._execute_run_item(config, item, candidate_plan)
            if result.completed:
                completed += 1
                if result.response is None:
                    continue
                self.langfuse_gateway.enqueue_candidate_evaluator_payload(
                    self._candidate_evaluator_payload(
                        config,
                        result,
                        baseline_run_id=context.baseline_run_id,
                        baseline_reference=context.baseline_reference,
                        baseline_prompt_identity=context.baseline_prompt_identity,
                        candidate_prompt_identity=context.candidate_prompt_identity,
                        candidate_parameter_identity=context.candidate_parameter_identity,
                        candidate_generation_parameter_hash=(
                            context.candidate_generation_parameter_hash
                        ),
                        candidate_variant_identity=context.candidate_variant_identity,
                    )
                )
            elif result.failed:
                failed += 1

        targeting = self._diagnose_run_model_output_targeting(
            run_id=context.run_id,
            completed_count=completed,
        )
        langfuse_warnings = self._current_langfuse_warning_messages()
        return RunResult(
            run_id=context.run_id,
            run_type="candidate",
            completed_count=completed,
            failed_count=failed,
            baseline_reference=context.baseline_reference,
            model_output_targeting_status=targeting.status,
            model_output_targeting_message=targeting.message,
            langfuse_status=self._langfuse_status(langfuse_warnings),
            langfuse_warnings=langfuse_warnings,
        )

    def _execute_run_item(
        self,
        config: ProjectConfig,
        item: DatasetItem,
        plan: RunItemExecutionPlan,
    ) -> RunItemExecutionResult:
        # This method owns only shared item mechanics; run setup, finalization,
        # and evaluator payload semantics stay in the baseline/candidate paths.
        trace_id = self.langfuse_gateway.create_trace_id(
            f"{plan.run_id}:{item.item_id}"
        )
        trace_name = self._trace_name(
            config,
            run_type=plan.run_type,
            item=item,
            model_config=plan.model_config if plan.run_type == "candidate" else None,
        )
        rendered_prompt = self._render_prompt_payload(plan.prompt_ref, item)
        prompt = rendered_prompt.display_text
        session_inputs = self._session_identity_inputs(
            config=config,
            item=item,
            dataset_sync=plan.dataset_sync,
            baseline_anchor=plan.baseline_anchor,
        )
        session_id = item_comparison_session_id(session_inputs)
        metadata = {
            **self._request_metadata(
                config=config,
                model_config=plan.model_config,
                item=item,
                run_id=plan.run_id,
                run_type=plan.run_type,
                trace_id=trace_id,
                trace_name=trace_name,
                dataset_sync=plan.dataset_sync,
                fingerprint=plan.fingerprint,
                rendered_prompt=rendered_prompt,
                session_id=session_id,
                session_inputs=session_inputs,
            ),
            **plan.request_metadata,
        }
        request = ModelRequest(
            prompt=prompt,
            params=plan.model_config.parameters.model_dump(
                mode="json", exclude_none=True
            ),
            metadata=metadata,
            rendered_prompt=rendered_prompt,
        )
        parent_metadata = parent_observation_metadata(request.metadata)
        with self.langfuse_gateway.trace_span(
            trace_id=trace_id,
            name=trace_name,
            input=item.input,
            metadata=parent_metadata,
            session_id=session_id,
        ) as parent_observation:
            parent_observation_id = self.langfuse_gateway.observation_id(
                parent_observation
            )
            if parent_observation_id:
                request.metadata["parent_observation_id"] = parent_observation_id
                parent_metadata["parent_observation_id"] = parent_observation_id
            uses_manual_generation = self._uses_manual_generation_observation(
                plan.provider
            )
            try:
                self._validate_provider_prompt_roles(plan.model_config, rendered_prompt)
                response = self._generate_with_optional_langfuse_generation(
                    plan.provider,
                    request,
                    model_config=plan.model_config,
                    prompt=prompt,
                )
            except Exception as exc:
                trace = self._trace_payload(
                    config=config,
                    item=item,
                    run_id=plan.run_id,
                    trace_id=trace_id,
                    trace_name=trace_name,
                    response=None,
                    prompt=prompt,
                    retry_count=0,
                    error=str(exc),
                    model_config=plan.model_config,
                    dataset_sync=plan.dataset_sync,
                    fingerprint=plan.fingerprint,
                    baseline_reference=plan.baseline_reference,
                    parameter_hash=plan.parameter_hash,
                    rendered_prompt=rendered_prompt,
                    observation_role=RUN_ITEM_ROLE,
                    session_id=session_id,
                    session_inputs=session_inputs,
                )
                self._record_run_item_trace(
                    item,
                    plan,
                    trace=trace,
                    parent_observation=parent_observation,
                    parent_observation_id=parent_observation_id,
                )
                return RunItemExecutionResult(
                    item=item,
                    trace_id=trace_id,
                    trace_name=trace_name,
                    session_id=session_id,
                    rendered_prompt=rendered_prompt,
                    response=None,
                    error=str(exc),
                    retry_count=0,
                    trace=trace,
                    completed=False,
                    failed=True,
                    dataset_run_item_recorded=True,
                )

            retry_count = int(response.raw.get("retry_count", 0))
            trace = self._trace_payload(
                config=config,
                item=item,
                run_id=plan.run_id,
                trace_id=trace_id,
                trace_name=trace_name,
                response=response,
                prompt=prompt,
                retry_count=retry_count,
                error=None,
                model_config=plan.model_config,
                dataset_sync=plan.dataset_sync,
                fingerprint=plan.fingerprint,
                baseline_reference=plan.baseline_reference,
                parameter_hash=plan.parameter_hash,
                rendered_prompt=rendered_prompt,
                observation_role=(
                    RUN_ITEM_ROLE if uses_manual_generation else MODEL_OUTPUT_ROLE
                ),
                session_id=session_id,
                session_inputs=session_inputs,
            )
            self._record_run_item_trace(
                item,
                plan,
                trace=trace,
                parent_observation=parent_observation,
                parent_observation_id=parent_observation_id,
            )
            return RunItemExecutionResult(
                item=item,
                trace_id=trace_id,
                trace_name=trace_name,
                session_id=session_id,
                rendered_prompt=rendered_prompt,
                response=response,
                error=None,
                retry_count=retry_count,
                trace=trace,
                completed=True,
                failed=False,
                dataset_run_item_recorded=True,
            )

    def _record_run_item_trace(
        self,
        item: DatasetItem,
        plan: RunItemExecutionPlan,
        *,
        trace: dict[str, Any],
        parent_observation: Any,
        parent_observation_id: str | None,
    ) -> None:
        if self.langfuse_gateway.update_trace_span(parent_observation, trace):
            trace["_live_observation_logged"] = True
        self.langfuse_gateway.log_trace(trace)
        self.langfuse_gateway.record_dataset_run_item(
            dataset_sync=plan.dataset_sync,
            item_id=item.item_id,
            run_name=plan.run_id,
            trace_id=trace["trace_id"],
            observation_id=parent_observation_id,
            metadata=trace["metadata"],
        )

    def _baseline_evaluator_payload(
        self,
        config: ProjectConfig,
        result: RunItemExecutionResult,
    ) -> dict[str, Any]:
        if result.response is None:
            raise ConfigError("Baseline evaluator payload requires a provider response")
        return {
            "run_id": result.trace["run_id"],
            "trace_id": result.trace_id,
            "item_id": result.item.item_id,
            "input": result.item.input,
            "output": result.response.output,
            "ground_truth": result.item.ground_truth,
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

    def _candidate_evaluator_payload(
        self,
        config: ProjectConfig,
        result: RunItemExecutionResult,
        *,
        baseline_run_id: str,
        baseline_reference: BaselineReference,
        baseline_prompt_identity: dict[str, Any],
        candidate_prompt_identity: dict[str, Any],
        candidate_parameter_identity: dict[str, Any],
        candidate_generation_parameter_hash: str,
        candidate_variant_identity: dict[str, Any],
    ) -> dict[str, Any]:
        if result.response is None:
            raise ConfigError(
                "Candidate evaluator payload requires a provider response"
            )
        return {
            "run_id": result.trace["run_id"],
            "trace_id": result.trace_id,
            "item_id": result.item.item_id,
            "input": result.item.input,
            "output": result.response.output,
            "baseline_output": self.langfuse_gateway.output_for(
                run_id=baseline_run_id,
                item_id=result.item.item_id,
            ),
            "ground_truth": result.item.ground_truth,
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
        return build_trace_payload(
            config=config,
            item=item,
            run_id=run_id,
            trace_id=trace_id,
            trace_name=trace_name,
            response=response,
            prompt=prompt,
            retry_count=retry_count,
            error=error,
            model_config=model_config,
            dataset_sync=dataset_sync,
            fingerprint=fingerprint,
            baseline_reference=baseline_reference,
            parameter_hash=parameter_hash,
            rendered_prompt=rendered_prompt,
            observation_role=observation_role,
            session_id=session_id,
            session_inputs=session_inputs,
        )

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
        return build_request_metadata(
            config=config,
            model_config=model_config,
            item=item,
            run_id=run_id,
            run_type=run_type,
            trace_id=trace_id,
            trace_name=trace_name,
            dataset_sync=dataset_sync,
            fingerprint=fingerprint,
            rendered_prompt=rendered_prompt,
            session_id=session_id,
            session_inputs=session_inputs,
        )

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
        if self.langfuse_gateway.supports_observation_spans():
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
                    str(
                        (trace.get("metadata") or {}).get("observation_role")
                        or RUN_ITEM_ROLE
                    ),
                ),
            }
            for trace in self.langfuse_gateway.traces_for_run(run_id)
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

    def _render_prompt_payload(
        self, prompt_ref: Any, item: DatasetItem
    ) -> RenderedPrompt:
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

    def _candidate_by_name(
        self, config: ProjectConfig, candidate_name: str
    ) -> ModelConfig:
        for candidate in config.candidates:
            if candidate.name == candidate_name:
                return candidate
        raise ConfigError(f"Candidate model config not found: {candidate_name}")


def _required_str(value: object, option_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise ConfigError(f"{option_name} is required for candidate runs")
    return value