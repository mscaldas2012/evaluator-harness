from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Any

from evaluator_harness.langfuse_mappers import (
    object_to_score_config_dict,
    object_to_score_dict,
)
from evaluator_harness.langfuse_scores import annotation_scores_for_traces
from evaluator_harness.langfuse_records import (
    AnnotationQueueRecord,
    DatasetItemRecord,
    DatasetRecord,
    EvaluatorRecord,
    PromptRecord,
    RunRecord,
    ScoreConfigRecord,
    ScoreRecord,
    TraceRecord,
)


@dataclass(frozen=True)
class InMemoryAnnotationRoutingResult:
    queue_id: str
    queued_count: int
    skipped_duplicate_count: int


@dataclass
class InMemoryLangfuseGateway:
    owner: Any | None = None
    datasets: dict[str, DatasetRecord] = field(default_factory=dict)
    dataset_items: dict[str, list[DatasetItemRecord]] = field(default_factory=dict)
    runs: dict[str, RunRecord] = field(default_factory=dict)
    traces: list[TraceRecord] = field(default_factory=list)
    scores: list[ScoreRecord] = field(default_factory=list)
    score_configs: list[ScoreConfigRecord] = field(default_factory=list)
    prompts: dict[str, list[PromptRecord]] = field(default_factory=dict)
    evaluators: list[EvaluatorRecord] = field(default_factory=list)
    annotation_queues: list[AnnotationQueueRecord] = field(default_factory=list)
    annotation_queue_items: dict[str, set[str]] = field(default_factory=dict)

    def check_reachable(self, *, operation: str) -> None:
        if self.owner is not None:
            self.owner.check_reachable(operation=operation)
            return
        _ = operation

    def sync_dataset(self, *args: Any, **kwargs: Any) -> Any:
        if self.owner is not None:
            return self.owner._sync_dataset_impl(*args, **kwargs)
        name = str(args[0] if args else kwargs["name"])
        items = list(args[1] if len(args) > 1 else kwargs.get("items", []))
        record = DatasetRecord(id=name, name=name)
        self.datasets[name] = record
        self.dataset_items[name] = items
        return record

    def record_dataset_run_item(self, *args: Any, **kwargs: Any) -> None:
        if self.owner is not None:
            self.owner._record_dataset_run_item_impl(*args, **kwargs)
            return
        run = args[0] if args else kwargs.get("run")
        item = args[1] if len(args) > 1 else kwargs.get("item")
        if isinstance(run, RunRecord):
            self.runs[run.id] = run
        if isinstance(item, DatasetItemRecord):
            items = self.dataset_items.setdefault(item.dataset_name, [])
            if item not in items:
                items.append(item)

    def sync_score_configs(self, *args: Any, **kwargs: Any) -> Any:
        if self.owner is not None:
            return self.owner._sync_score_configs_impl(*args, **kwargs)
        raise NotImplementedError("sync_score_configs requires a facade owner")

    def load_live_score_configs_by_name(self, *args: Any, **kwargs: Any) -> Any:
        if self.owner is not None:
            return self.owner._load_live_score_configs_by_name(*args, **kwargs)
        return None

    def create_live_score_config(self, *args: Any, **kwargs: Any) -> Any:
        if self.owner is not None:
            return self.owner._create_live_score_config(*args, **kwargs)
        return None

    def list_score_configs(self) -> list[ScoreConfigRecord]:
        return list(self.score_configs)

    def list_prompt_versions(self, name: str | None = None) -> list[PromptRecord]:
        if self.owner is not None:
            return self.owner._list_prompt_versions_impl(name)
        if name is None:
            return [prompt for versions in self.prompts.values() for prompt in versions]
        return list(self.prompts.get(name, []))

    def create_prompt_version(self, *args: Any, **kwargs: Any) -> Any:
        if self.owner is not None:
            return self.owner._create_prompt_version_impl(*args, **kwargs)
        payload = dict(args[0] if args else kwargs)
        versions = self.prompts.setdefault(str(payload["name"]), [])
        record = PromptRecord(
            name=str(payload["name"]),
            version=payload.get("version") or len(versions) + 1,
            prompt=payload.get("prompt"),
            type=payload.get("type"),
            config=dict(payload.get("config") or {}),
            labels=list(payload.get("labels") or []),
            tags=list(payload.get("tags") or []),
            commit_message=payload.get("commit_message"),
        )
        versions.append(record)
        return record

    def traces_for_run(
        self,
        run_id: str,
        *args: Any,
        **kwargs: Any,
    ) -> list[TraceRecord]:
        if self.owner is not None:
            return self.owner._traces_for_run_impl(run_id, *args, **kwargs)
        return [trace for trace in self.traces if trace.run_id == run_id]

    def scores_for_traces(self, trace_ids: list[str]) -> list[ScoreRecord]:
        trace_id_set = {str(trace_id) for trace_id in trace_ids}
        return [
            score
            for score in self.scores
            if score.trace_id is not None and str(score.trace_id) in trace_id_set
        ]

    def fetch_scores(self, *args: Any, **kwargs: Any) -> Any:
        if self.owner is not None:
            return self.owner._fetch_scores_impl(*args, **kwargs)
        trace_ids = kwargs.get("trace_ids")
        return self.scores_for_traces(trace_ids or [])

    def fetch_calibration_scores(self, *args: Any, **kwargs: Any) -> Any:
        if self.owner is not None:
            return self.owner.fetch_calibration_scores(*args, **kwargs)
        trace_ids = kwargs.get("trace_ids") or []
        scores = [object_to_score_dict(score) for score in self.scores_for_traces(trace_ids)]
        return [*scores, *annotation_scores_for_traces(self, trace_ids)]

    def list_evaluators(self) -> list[EvaluatorRecord]:
        if self.owner is not None:
            return self.owner._list_evaluators_impl()
        return list(self.evaluators)

    def get_evaluator(self, evaluator_id: str) -> Any:
        if self.owner is not None:
            return self.owner._get_evaluator_impl(evaluator_id)
        return next(
            (
                evaluator
                for evaluator in self.evaluators
                if str(evaluator.id) == str(evaluator_id)
            ),
            None,
        )

    def create_evaluator(self, payload: dict[str, Any]) -> Any:
        if self.owner is not None:
            return self.owner._create_evaluator_impl(payload)
        record = EvaluatorRecord(
            id=str(payload.get("id") or f"eval-{len(self.evaluators) + 1}"),
            name=str(payload.get("name") or payload.get("display_name")),
            display_name=payload.get("display_name"),
            active=payload.get("active"),
            filters=dict(payload.get("filters") or {}),
            variables=dict(payload.get("variables") or {}),
            score_config_id=payload.get("score_config_id"),
            sampling_percent=payload.get("sampling_percent"),
            target=payload.get("target"),
            metadata=dict(payload.get("metadata") or {}),
        )
        self.evaluators.append(record)
        return record

    def update_evaluator(self, evaluator_id: str, changes: dict[str, Any]) -> Any:
        if self.owner is not None:
            return self.owner._update_evaluator_impl(evaluator_id, changes)
        existing = self.get_evaluator(evaluator_id)
        if existing is None:
            return None
        updated = replace(existing, **changes)
        self.evaluators = [
            updated if str(evaluator.id) == str(evaluator_id) else evaluator
            for evaluator in self.evaluators
        ]
        return updated

    def lookup_baseline(self, *args: Any, **kwargs: Any) -> Any:
        if self.owner is not None:
            return self.owner._lookup_baseline_impl(*args, **kwargs)
        return None

    def lookup_live_baseline(self, **kwargs: Any) -> Any:
        _ = kwargs
        return None

    def dataset_run_metadata(self, **kwargs: Any) -> dict[str, Any]:
        if self.owner is not None:
            return self.owner._dataset_run_metadata_impl(**kwargs)
        return {}

    def list_annotation_queues(self) -> list[AnnotationQueueRecord]:
        if self.owner is not None:
            return self.owner._list_annotation_queues_impl()
        return list(self.annotation_queues)

    def route_annotation_items(self, *args: Any, **kwargs: Any) -> Any:
        if self.owner is not None:
            return self.owner._route_annotation_items_impl(*args, **kwargs)
        queue_id = str(args[0] if args else kwargs["queue_id"])
        items = list(args[1] if len(args) > 1 else kwargs.get("items", []))
        object_ids = self.annotation_queue_items.setdefault(queue_id, set())
        queued_count = 0
        skipped_count = 0
        for item in items:
            object_id = str(item.get("object_id") or item.get("trace_id") or "")
            if not object_id:
                continue
            if object_id in object_ids:
                skipped_count += 1
                continue
            object_ids.add(object_id)
            queued_count += 1
        return InMemoryAnnotationRoutingResult(
            queue_id=queue_id,
            queued_count=queued_count,
            skipped_duplicate_count=skipped_count,
        )

    def annotation_queue_object_ids(self, *args: Any, **kwargs: Any) -> set[str]:
        if self.owner is not None:
            return self.owner._annotation_queue_object_ids_impl(*args, **kwargs)
        queue_id = str(args[0] if args else kwargs["queue_id"])
        return set(self.annotation_queue_items.get(queue_id, set()))

    def completed_annotation_queue_items(self, *args: Any, **kwargs: Any) -> list[Any]:
        if self.owner is not None:
            return self.owner._completed_annotation_queue_items_impl(*args, **kwargs)
        queue_ids = {str(queue_id) for queue_id in (args[0] if args else kwargs["queue_ids"])}
        return [
            {
                "queue_id": queue_id,
                "object_id": object_id,
                "trace_id": object_id,
                "status": "COMPLETED",
            }
            for queue_id, object_ids in self.annotation_queue_items.items()
            if queue_id in queue_ids
            for object_id in object_ids
        ]

    def create_annotation_queue(self, *args: Any, **kwargs: Any) -> Any:
        if self.owner is not None:
            return self.owner._create_annotation_queue_impl(*args, **kwargs)
        record = AnnotationQueueRecord(
            id=str(kwargs.get("id") or f"queue-{len(self.annotation_queues) + 1}"),
            name=kwargs.get("name"),
            description=kwargs.get("description"),
            score_config_ids=list(kwargs.get("score_config_ids") or []),
            metadata=dict(kwargs.get("metadata") or {}),
        )
        self.annotation_queues.append(record)
        self.annotation_queue_items.setdefault(record.id, set())
        return record

    def get_annotation_queue(self, queue_id: str) -> Any:
        if self.owner is not None:
            return self.owner._get_annotation_queue_impl(queue_id)
        return next(
            (
                queue
                for queue in self.annotation_queues
                if str(queue.id) == str(queue_id)
            ),
            None,
        )

    def log_trace(self, trace: TraceRecord) -> TraceRecord:
        self.traces.append(trace)
        return trace

    def record_score(self, score: ScoreRecord | dict[str, Any]) -> ScoreRecord:
        if isinstance(score, dict):
            normalized = object_to_score_dict(score)
            score = ScoreRecord(
                id=normalized.get("id"),
                name=normalized.get("name"),
                value=normalized.get("value"),
                trace_id=normalized.get("trace_id"),
                observation_id=normalized.get("observation_id"),
                dataset_run_id=normalized.get("dataset_run_id"),
                comment=normalized.get("comment"),
                source=normalized.get("source"),
                metadata=dict(normalized.get("metadata") or {}),
            )
        self.scores.append(score)
        return score

    def record_score_config(
        self,
        score_config: ScoreConfigRecord | dict[str, Any],
    ) -> ScoreConfigRecord:
        if isinstance(score_config, dict):
            normalized = object_to_score_config_dict(score_config)
            score_config = ScoreConfigRecord(
                id=normalized.get("id"),
                name=str(normalized["name"]),
                data_type=normalized.get("data_type"),
                min_value=normalized.get("min_value"),
                max_value=normalized.get("max_value"),
                categories=normalized.get("categories"),
                description=normalized.get("description"),
                archived=bool(normalized.get("archived", False)),
                metadata=dict(normalized.get("metadata") or {}),
            )
        self.score_configs.append(score_config)
        return score_config
