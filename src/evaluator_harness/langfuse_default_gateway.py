from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from collections.abc import Mapping
from typing import Any

import httpx

from evaluator_harness.config import (
    DatasetItem,
    DatasetSource,
    LiveSettings,
    ProjectConfig,
    ScoreConfigRef,
)
from evaluator_harness.errors import LangfuseError
from evaluator_harness.langfuse_annotation_ops import (
    annotation_queue_object_ids_workflow,
    build_annotation_queue_payload_workflow,
    create_annotation_queue_workflow,
    create_live_annotation_queue,
    create_live_annotation_queue_item,
    get_annotation_queue_workflow,
    get_live_annotation_queue,
    list_annotation_queues_workflow,
    list_live_annotation_queues,
    live_annotation_queue_object_ids,
    route_annotation_items_workflow,
)
from evaluator_harness.langfuse_baselines import (
    dataset_run_metadata_workflow,
    lookup_baseline_workflow,
    lookup_live_baseline_workflow,
)
from evaluator_harness.langfuse_dataset import (
    find_dataset_item_id,
    record_dataset_run_item_workflow,
    sync_dataset_workflow,
)
from evaluator_harness.langfuse_evaluator_ops import (
    create_evaluator_workflow,
    create_live_evaluator,
    create_rest_evaluator,
    get_evaluator_workflow,
    get_live_evaluator,
    get_rest_evaluator,
    inactivate_evaluator_workflow,
    list_evaluators_workflow,
    list_live_evaluators,
    list_rest_evaluators,
    resolve_rest_evaluator_reference,
    rest_evaluator_request,
    supports_evaluator_backfill,
    update_evaluator_workflow,
    update_live_evaluator,
    update_rest_evaluator,
)
from evaluator_harness.langfuse_gateways import (
    build_langfuse_gateway,
    gateway_config_from_connection,
)
from evaluator_harness.langfuse_health import check_reachable_workflow
from evaluator_harness.langfuse_observations import (
    create_run_workflow,
    create_trace_id_workflow,
    generation_span_workflow,
    log_trace_workflow,
    observation_id_workflow,
    supports_observation_spans,
    trace_span_workflow,
    update_generation_span_workflow,
    update_trace_span_workflow,
)
from evaluator_harness.langfuse_prompts import (
    create_prompt_version_workflow,
    find_prompt_version_workflow,
    list_prompt_versions_workflow,
    live_create_prompt_version,
    live_list_prompt_versions,
)
from evaluator_harness.langfuse_records import (
    AnnotationRoutingResult,
    DatasetSyncResult,
    LangfuseOperationOutcome,
    LangfuseWarning,
    ScoreConfigRecord,
    ScoreConfigSyncResult,
    aggregate_langfuse_warnings,
    warning_from_outcome,
)
from evaluator_harness.langfuse_retry import (
    with_logged_langfuse_retries,
)
from evaluator_harness.langfuse_score_configs import (
    align_score_config_to_existing_id as align_live_score_config_to_existing_id,
)
from evaluator_harness.langfuse_score_configs import (
    assert_score_config_compatible,
    create_live_score_config,
    load_live_score_configs_by_name,
    score_payload,
    sync_one_score_config,
    sync_score_configs_workflow,
)
from evaluator_harness.langfuse_scores import (
    fetch_scores_workflow,
    live_scores_for_traces,
)
from evaluator_harness.langfuse_traces import (
    candidate_dataset_names,
    live_dataset_run_item_traces,
    live_dataset_run_traces_for_run,
    live_trace_by_id,
    live_traces_for_run,
    output_for_workflow,
    trace_by_id_workflow,
    traces_for_run_workflow,
)
from evaluator_harness.progress import ProgressReporter


@dataclass
class DefaultLangfuseGateway:
    client: Any | None = None
    reachable: bool = True
    settings: LiveSettings | None = None
    http_transport: httpx.BaseTransport | None = None
    calls: list[tuple[str, dict[str, Any]]] = field(default_factory=list)
    datasets: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    score_configs: dict[str, dict[str, Any]] = field(default_factory=dict)
    runs: dict[str, dict[str, Any]] = field(default_factory=dict)
    traces: list[dict[str, Any]] = field(default_factory=list)
    baseline_evaluator_payloads: list[dict[str, Any]] = field(default_factory=list)
    candidate_evaluator_payloads: list[dict[str, Any]] = field(default_factory=list)
    baseline_references: dict[str, Any] = field(default_factory=dict)
    scores: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    prompt_versions: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    annotation_queues: dict[str, dict[str, Any]] = field(default_factory=dict)
    annotation_queue_items: list[dict[str, Any]] = field(default_factory=list)
    evaluators: dict[str, dict[str, Any]] = field(default_factory=dict)
    evaluator_backfill_targets: set[str] = field(default_factory=set)
    langfuse_warnings: list[LangfuseWarning] = field(default_factory=list)
    retry_sleep: Any = field(default=time.sleep, repr=False)
    _annotation_queue_keys: set[tuple[str, str]] = field(default_factory=set)
    _gateway: Any = field(default=None, init=False, repr=False)

    def __post_init__(self) -> None:
        self._gateway = build_langfuse_gateway(
            owner=self,
            config=gateway_config_from_connection(
                client=self.client,
                settings=self.settings,
                http_transport=self.http_transport,
                reachable=self.reachable,
            ),
        )

    def record_langfuse_outcome(self, outcome: LangfuseOperationOutcome) -> None:
        warning = warning_from_outcome(outcome)
        if warning is not None:
            self.add_langfuse_warning(warning)

    def add_langfuse_warning(self, warning: LangfuseWarning) -> None:
        self.langfuse_warnings = list(
            aggregate_langfuse_warnings((*self.langfuse_warnings, warning))
        )

    def current_langfuse_warnings(self) -> tuple[LangfuseWarning, ...]:
        return aggregate_langfuse_warnings(self.langfuse_warnings)

    def drain_langfuse_warnings(self) -> tuple[LangfuseWarning, ...]:
        warnings = self.current_langfuse_warnings()
        self.langfuse_warnings.clear()
        return warnings

    @classmethod
    def from_env(
        cls,
        *,
        env_mapping: Mapping[str, str] | None = None,
    ) -> DefaultLangfuseGateway:
        settings = LiveSettings.from_env(load_file=env_mapping is None, env_mapping=env_mapping)
        settings.require_langfuse()
        try:
            from langfuse import Langfuse
        except Exception as exc:  # pragma: no cover - dependency present in normal env
            raise LangfuseError("langfuse SDK is required for live execution") from exc
        return cls(
            client=Langfuse(
                public_key=settings.langfuse_public_key,
                secret_key=settings.langfuse_secret_key,
                host=settings.langfuse_host,
            ),
            settings=settings,
        )

    def check_reachable(
        self,
        *,
        operation: str = "langfuse",
        dataset_item_id: str | None = None,
    ) -> None:
        check_reachable_workflow(
            self,
            operation=operation,
            dataset_item_id=dataset_item_id,
        )

    def sync_dataset(
        self,
        source: DatasetSource,
        items: list[DatasetItem],
        *,
        progress: ProgressReporter | None = None,
        dry_run: bool = False,
    ) -> DatasetSyncResult:
        return self._gateway.sync_dataset(
            source,
            items,
            progress=progress,
            dry_run=dry_run,
        )

    def _sync_dataset_impl(
        self,
        source: DatasetSource,
        items: list[DatasetItem],
        *,
        progress: ProgressReporter | None = None,
        dry_run: bool = False,
    ) -> DatasetSyncResult:
        return sync_dataset_workflow(
            self,
            source,
            items,
            result_factory=DatasetSyncResult,
            progress=progress,
            dry_run=dry_run,
        )

    def record_dataset_run_item(
        self,
        *,
        dataset_sync: DatasetSyncResult,
        item_id: str,
        run_name: str,
        trace_id: str,
        observation_id: str | None,
        metadata: dict[str, Any],
    ) -> None:
        self._gateway.record_dataset_run_item(
            dataset_sync=dataset_sync,
            item_id=item_id,
            run_name=run_name,
            trace_id=trace_id,
            observation_id=observation_id,
            metadata=metadata,
        )

    def _record_dataset_run_item_impl(
        self,
        *,
        dataset_sync: DatasetSyncResult,
        item_id: str,
        run_name: str,
        trace_id: str,
        observation_id: str | None,
        metadata: dict[str, Any],
    ) -> None:
        record_dataset_run_item_workflow(
            self,
            dataset_sync=dataset_sync,
            item_id=item_id,
            run_name=run_name,
            trace_id=trace_id,
            observation_id=observation_id,
            metadata=metadata,
        )

    def _find_dataset_item_id(self, *, dataset_name: str, item_id: str) -> str | None:
        return find_dataset_item_id(self, dataset_name=dataset_name, item_id=item_id)

    def sync_score_configs(
        self,
        config: ProjectConfig,
        *,
        progress: ProgressReporter | None = None,
        dry_run: bool = False,
    ) -> list[ScoreConfigSyncResult]:
        return self._gateway.sync_score_configs(
            config,
            progress=progress,
            dry_run=dry_run,
        )

    def _sync_score_configs_impl(
        self,
        config: ProjectConfig,
        *,
        progress: ProgressReporter | None = None,
        dry_run: bool = False,
    ) -> list[ScoreConfigSyncResult]:
        return sync_score_configs_workflow(
            self,
            config,
            result_factory=ScoreConfigSyncResult,
            progress=progress,
            dry_run=dry_run,
        )

    def _sync_one_score_config(
        self,
        config: ProjectConfig,
        evaluator: Any,
        *,
        dry_run: bool = False,
    ) -> ScoreConfigSyncResult:
        return sync_one_score_config(
            self,
            config,
            evaluator,
            result_factory=ScoreConfigSyncResult,
            dry_run=dry_run,
        )

    def list_score_configs(self) -> list[ScoreConfigRecord]:
        records: list[ScoreConfigRecord] = []
        for value in self.score_configs.values():
            records.append(
                ScoreConfigRecord(
                    id=str(value.get("id")) if value.get("id") is not None else None,
                    name=str(value.get("name") or ""),
                    data_type=value.get("data_type") or value.get("dataType"),
                    min_value=value.get("min_value")
                    if value.get("min_value") is not None
                    else value.get("minValue"),
                    max_value=value.get("max_value")
                    if value.get("max_value") is not None
                    else value.get("maxValue"),
                    categories=value.get("categories"),
                    description=value.get("description"),
                    archived=bool(value.get("archived", False)),
                    metadata=value.get("metadata") or {},
                )
            )
        return records

    def list_evaluators(self) -> list[dict[str, Any]]:
        return self._gateway.list_evaluators()

    def _list_evaluators_impl(self) -> list[dict[str, Any]]:
        return list_evaluators_workflow(self)

    def get_evaluator(self, evaluator_id: str) -> dict[str, Any] | None:
        return self._gateway.get_evaluator(evaluator_id)

    def _get_evaluator_impl(self, evaluator_id: str) -> dict[str, Any] | None:
        return get_evaluator_workflow(self, evaluator_id)

    def create_evaluator(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._gateway.create_evaluator(payload)

    def _create_evaluator_impl(self, payload: dict[str, Any]) -> dict[str, Any]:
        return create_evaluator_workflow(self, payload)

    def update_evaluator(
        self,
        evaluator_id: str,
        changes: dict[str, Any],
    ) -> dict[str, Any]:
        return self._gateway.update_evaluator(evaluator_id, changes)

    def _update_evaluator_impl(
        self,
        evaluator_id: str,
        changes: dict[str, Any],
    ) -> dict[str, Any]:
        return update_evaluator_workflow(self, evaluator_id, changes)

    def inactivate_evaluator(
        self,
        evaluator_id: str,
        *,
        comment: str | None = None,
    ) -> dict[str, Any]:
        return inactivate_evaluator_workflow(self, evaluator_id, comment=comment)

    def supports_evaluator_backfill(self, target: str) -> bool:
        return supports_evaluator_backfill(self, target)

    def _list_live_evaluators(self) -> list[dict[str, Any]]:
        return list_live_evaluators(self)

    def _get_live_evaluator(self, evaluator_id: str) -> dict[str, Any]:
        return get_live_evaluator(self, evaluator_id)

    def _create_live_evaluator(self, payload: dict[str, Any]) -> dict[str, Any]:
        return create_live_evaluator(self, payload)

    def _update_live_evaluator(
        self,
        evaluator_id: str,
        changes: dict[str, Any],
    ) -> dict[str, Any]:
        return update_live_evaluator(self, evaluator_id, changes)

    def _list_rest_evaluators(self) -> list[dict[str, Any]]:
        return list_rest_evaluators(self)

    def _get_rest_evaluator(self, evaluator_id: str) -> dict[str, Any] | None:
        return get_rest_evaluator(self, evaluator_id)

    def _create_rest_evaluator(self, payload: dict[str, Any]) -> dict[str, Any]:
        return create_rest_evaluator(self, payload)

    def _update_rest_evaluator(
        self,
        evaluator_id: str,
        changes: dict[str, Any],
    ) -> dict[str, Any]:
        return update_rest_evaluator(self, evaluator_id, changes)

    def _resolve_rest_evaluator_reference(
        self,
        payload: dict[str, Any],
    ) -> dict[str, str]:
        return resolve_rest_evaluator_reference(self, payload)

    def _rest_evaluator_request(
        self,
        method: str,
        path: str,
        *,
        operation: str,
        json_payload: dict[str, Any] | None = None,
    ) -> Any:
        return rest_evaluator_request(
            self,
            method,
            path,
            operation=operation,
            json_payload=json_payload,
        )

    def _with_langfuse_retries(self, *, operation: str, callback: Any) -> Any:
        return with_logged_langfuse_retries(
            self,
            operation=operation,
            callback=callback,
        )

    def _load_live_score_configs_by_name(
        self,
        name: str,
        expected: dict[str, Any],
    ) -> None:
        load_live_score_configs_by_name(self, name, expected)

    def _create_live_score_config(self, payload: dict[str, Any]) -> str | None:
        return create_live_score_config(self, payload)

    def align_score_config_to_existing_id(
        self,
        *,
        target_score_config_id: str,
        managed_name: str,
    ) -> None:
        align_live_score_config_to_existing_id(
            self,
            target_score_config_id=target_score_config_id,
            managed_name=managed_name,
        )

    def create_run(self, *args: Any, **kwargs: Any) -> Any:
        return create_run_workflow(self, *args, **kwargs)

    def log_trace(self, trace: dict[str, Any]) -> dict[str, Any]:
        return log_trace_workflow(self, trace)

    @contextmanager
    def trace_span(
        self,
        *,
        trace_id: str,
        name: str,
        input: Any,
        metadata: dict[str, Any],
        session_id: str | None = None,
    ):
        with trace_span_workflow(
            self,
            trace_id=trace_id,
            name=name,
            input=input,
            metadata=metadata,
            session_id=session_id,
        ) as observation:
            yield observation

    def supports_observation_spans(self) -> bool:
        return supports_observation_spans(self)

    @contextmanager
    def generation_span(
        self,
        *,
        name: str,
        input: Any,
        metadata: dict[str, Any],
        model: str,
        model_parameters: dict[str, Any],
        session_id: str | None = None,
    ):
        with generation_span_workflow(
            self,
            name=name,
            input=input,
            metadata=metadata,
            model=model,
            model_parameters=model_parameters,
            session_id=session_id,
        ) as observation:
            yield observation

    def observation_id(self, observation: Any | None) -> str | None:
        return observation_id_workflow(observation)

    def update_trace_span(self, observation: Any | None, trace: dict[str, Any]) -> bool:
        return update_trace_span_workflow(self, observation, trace)

    def update_generation_span(self, observation: Any | None, response: Any) -> bool:
        return update_generation_span_workflow(self, observation, response)

    def create_trace_id(self, seed: str) -> str:
        return create_trace_id_workflow(self, seed)

    def lookup_baseline(self, *args: Any, **kwargs: Any) -> Any:
        return self._gateway.lookup_baseline(*args, **kwargs)

    def _lookup_baseline_impl(self, *args: Any, **kwargs: Any) -> Any:
        return lookup_baseline_workflow(self, *args, **kwargs)

    def _lookup_live_baseline(self, *, selector: str, fingerprint: Any) -> Any | None:
        return self._gateway.lookup_live_baseline(
            selector=selector,
            fingerprint=fingerprint,
        )

    def _lookup_live_baseline_impl(
        self,
        *,
        selector: str,
        fingerprint: Any,
    ) -> Any | None:
        return lookup_live_baseline_workflow(
            self,
            selector=selector,
            fingerprint=fingerprint,
        )

    def _dataset_run_metadata(
        self,
        *,
        dataset_name: str,
        fingerprint: Any,
        run: Any,
    ) -> dict[str, Any]:
        return self._gateway.dataset_run_metadata(
            dataset_name=dataset_name,
            fingerprint=fingerprint,
            run=run,
        )

    def _dataset_run_metadata_impl(
        self,
        *,
        dataset_name: str,
        fingerprint: Any,
        run: Any,
    ) -> dict[str, Any]:
        return dataset_run_metadata_workflow(
            self,
            dataset_name=dataset_name,
            fingerprint=fingerprint,
            run=run,
        )

    def record_baseline_reference(self, run_id: str, reference: Any) -> None:
        self.baseline_references[run_id] = reference

    def enqueue_baseline_evaluator_payload(self, payload: dict[str, Any]) -> None:
        self.baseline_evaluator_payloads.append(payload)

    def enqueue_candidate_evaluator_payload(self, payload: dict[str, Any]) -> None:
        self.candidate_evaluator_payloads.append(payload)

    def output_for(self, *, run_id: str, item_id: str) -> str | None:
        return output_for_workflow(self, run_id=run_id, item_id=item_id)

    def fetch_scores(
        self,
        run_id: str,
        *,
        trace_ids: list[str] | None = None,
        progress: ProgressReporter | None = None,
    ) -> list[dict[str, Any]]:
        return self._gateway.fetch_scores(
            run_id,
            trace_ids=trace_ids,
            progress=progress,
        )

    def _fetch_scores_impl(
        self,
        run_id: str,
        *,
        trace_ids: list[str] | None = None,
        progress: ProgressReporter | None = None,
    ) -> list[dict[str, Any]]:
        return fetch_scores_workflow(
            self,
            run_id,
            trace_ids=trace_ids,
            progress=progress,
        )

    def scores_for_traces(self, trace_ids: list[str]) -> list[Any]:
        if self.client is not None:
            return self._live_scores_for_traces(trace_ids)
        return [
            score
            for trace_id in trace_ids
            for score in self.scores.get(trace_id, [])
        ]

    def list_prompt_versions(self, name: str | None = None) -> list[dict[str, Any]]:
        return self._gateway.list_prompt_versions(name)

    def _list_prompt_versions_impl(
        self,
        name: str | None = None,
    ) -> list[dict[str, Any]]:
        return list_prompt_versions_workflow(self, name)

    def find_prompt_version(
        self,
        name: str,
        *,
        label: str,
    ) -> dict[str, Any] | None:
        return find_prompt_version_workflow(self, name, label=label)

    def create_prompt_version(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._gateway.create_prompt_version(payload)

    def _create_prompt_version_impl(self, payload: dict[str, Any]) -> dict[str, Any]:
        return create_prompt_version_workflow(self, payload)

    def traces_for_run(
        self,
        run_id: str,
        *,
        dataset_names: list[str] | None = None,
        expected_count: int | None = None,
        wait_timeout_seconds: float | None = None,
        poll_interval_seconds: float | None = None,
    ) -> list[dict[str, Any]]:
        return self._gateway.traces_for_run(
            run_id,
            dataset_names=dataset_names,
            expected_count=expected_count,
            wait_timeout_seconds=wait_timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )

    def _traces_for_run_impl(
        self,
        run_id: str,
        *,
        dataset_names: list[str] | None = None,
        expected_count: int | None = None,
        wait_timeout_seconds: float | None = None,
        poll_interval_seconds: float | None = None,
    ) -> list[dict[str, Any]]:
        return traces_for_run_workflow(
            self,
            run_id,
            dataset_names=dataset_names,
            expected_count=expected_count,
            wait_timeout_seconds=wait_timeout_seconds,
            poll_interval_seconds=poll_interval_seconds,
        )

    def _live_list_prompt_versions(
        self,
        *,
        name: str | None = None,
    ) -> list[dict[str, Any]]:
        return live_list_prompt_versions(self, name=name)

    def _live_create_prompt_version(self, payload: dict[str, Any]) -> dict[str, Any]:
        return live_create_prompt_version(self, payload)

    def _live_scores_for_traces(
        self,
        trace_ids: list[str],
        *,
        progress: ProgressReporter | None = None,
    ) -> list[dict[str, Any]]:
        return live_scores_for_traces(self, trace_ids, progress=progress)

    def _live_traces_for_run(
        self,
        run_id: str,
        *,
        dataset_names: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        return live_traces_for_run(
            self,
            run_id,
            dataset_names=dataset_names,
        )

    def _live_dataset_run_traces_for_run(
        self,
        run_id: str,
        *,
        dataset_names: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        return live_dataset_run_traces_for_run(
            self,
            run_id,
            dataset_names=dataset_names,
        )

    def _candidate_dataset_names(self) -> list[str]:
        return candidate_dataset_names(self)

    def _live_dataset_run_item_traces(
        self,
        *,
        dataset_name: str,
        run_id: str,
    ) -> list[dict[str, Any]]:
        return live_dataset_run_item_traces(
            self,
            dataset_name=dataset_name,
            run_id=run_id,
        )

    def _live_trace_by_id(self, trace_id: str) -> dict[str, Any] | None:
        return live_trace_by_id(self, trace_id)

    def trace_by_id(self, trace_id: str) -> dict[str, Any]:
        return trace_by_id_workflow(self, trace_id)

    def build_annotation_queue_payload(
        self,
        config: ProjectConfig,
        selection: Any,
    ) -> dict[str, Any]:
        return build_annotation_queue_payload_workflow(self, config, selection)

    def route_annotation_items(
        self,
        queue_id: str,
        items: list[dict[str, Any]],
    ) -> AnnotationRoutingResult:
        return self._gateway.route_annotation_items(queue_id, items)

    def _route_annotation_items_impl(
        self,
        queue_id: str,
        items: list[dict[str, Any]],
    ) -> AnnotationRoutingResult:
        return route_annotation_items_workflow(
            self,
            queue_id,
            items,
            result_factory=AnnotationRoutingResult,
        )

    def annotation_queue_object_ids(self, queue_id: str) -> set[str]:
        return self._gateway.annotation_queue_object_ids(queue_id)

    def _annotation_queue_object_ids_impl(self, queue_id: str) -> set[str]:
        return annotation_queue_object_ids_workflow(self, queue_id)

    def create_annotation_queue(
        self,
        *,
        name: str,
        score_config_ids: list[str],
        description: str | None = None,
    ) -> dict[str, Any]:
        return self._gateway.create_annotation_queue(
            name=name,
            score_config_ids=score_config_ids,
            description=description,
        )

    def _create_annotation_queue_impl(
        self,
        *,
        name: str,
        score_config_ids: list[str],
        description: str | None = None,
    ) -> dict[str, Any]:
        return create_annotation_queue_workflow(
            self,
            name=name,
            score_config_ids=score_config_ids,
            description=description,
        )

    def list_annotation_queues(self) -> list[dict[str, Any]]:
        return self._gateway.list_annotation_queues()

    def _list_annotation_queues_impl(self) -> list[dict[str, Any]]:
        return list_annotation_queues_workflow(self)

    def get_annotation_queue(self, queue_id: str) -> dict[str, Any]:
        return self._gateway.get_annotation_queue(queue_id)

    def _get_annotation_queue_impl(self, queue_id: str) -> dict[str, Any]:
        return get_annotation_queue_workflow(self, queue_id)

    def _create_live_annotation_queue(
        self,
        *,
        name: str,
        score_config_ids: list[str],
        description: str | None,
    ) -> dict[str, Any] | None:
        return create_live_annotation_queue(
            self,
            name=name,
            score_config_ids=score_config_ids,
            description=description,
        )

    def _list_live_annotation_queues(self) -> list[dict[str, Any]] | None:
        return list_live_annotation_queues(self)

    def _get_live_annotation_queue(self, queue_id: str) -> dict[str, Any] | None:
        return get_live_annotation_queue(self, queue_id)

    def _create_live_annotation_queue_item(
        self,
        queue_id: str,
        *,
        object_id: str,
    ) -> dict[str, Any] | None:
        return create_live_annotation_queue_item(
            self,
            queue_id,
            object_id=object_id,
        )

    def _live_annotation_queue_object_ids(self, queue_id: str) -> set[str]:
        return live_annotation_queue_object_ids(self, queue_id)

    def _score_payload(
        self,
        managed_name: str,
        score: ScoreConfigRef,
    ) -> dict[str, Any]:
        return score_payload(managed_name, score)

    def _assert_score_config_compatible(
        self,
        managed_name: str,
        existing: dict[str, Any],
        expected: dict[str, Any],
    ) -> None:
        assert_score_config_compatible(managed_name, existing, expected)
