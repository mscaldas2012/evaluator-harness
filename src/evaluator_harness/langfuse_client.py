from __future__ import annotations

import hashlib
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Any

import httpx

from evaluator_harness.config import (
    DatasetItem,
    DatasetKind,
    DatasetSource,
    LiveSettings,
    ProjectConfig,
    ScoreConfigRef,
)
from evaluator_harness.dataset_loader import dataset_compatibility_version
from evaluator_harness.errors import FailureContext, LangfuseError, ConfigError
from evaluator_harness.progress import NullProgressReporter, ProgressReporter


_FINGERPRINT_FIELDS = [
    "project_name",
    "project_version",
    "dataset_name",
    "dataset_version",
    "prompt_version",
    "evaluator_set_id",
    "baseline_model",
    "baseline_parameters_hash",
]

UNSTABLE_EVALUATION_RULES_PATH = "/api/public/unstable/evaluation-rules"
UNSTABLE_EVALUATORS_PATH = "/api/public/unstable/evaluators"


@dataclass(frozen=True)
class DatasetSyncResult:
    name: str
    version: str
    compatibility_version: str
    item_count: int
    status: str
    rejected_count: int = 0


@dataclass(frozen=True)
class ScoreConfigSyncResult:
    evaluator_name: str
    name: str
    score_config_id: str
    status: str
    ownership: str


@dataclass(frozen=True)
class AnnotationRoutingResult:
    queue_id: str
    queued_count: int
    skipped_duplicate_count: int


@dataclass
class LangfuseClient:
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
    annotation_queues: dict[str, dict[str, Any]] = field(default_factory=dict)
    annotation_queue_items: list[dict[str, Any]] = field(default_factory=list)
    evaluators: dict[str, dict[str, Any]] = field(default_factory=dict)
    evaluator_backfill_targets: set[str] = field(default_factory=set)
    _annotation_queue_keys: set[tuple[str, str]] = field(default_factory=set)

    @classmethod
    def from_env(cls) -> LangfuseClient:
        settings = LiveSettings.from_env()
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
        self.calls.append(("check_reachable", {"operation": operation}))
        if not self.reachable:
            raise LangfuseError(
                f"Langfuse is unreachable during {operation}",
                context=FailureContext(
                    operation=operation,
                    dataset_item_id=dataset_item_id,
                ),
            )
        if self.client is not None:
            try:
                auth_check = getattr(self.client, "auth_check", None)
                if callable(auth_check):
                    auth_check()
            except Exception as exc:
                raise LangfuseError(
                    f"Langfuse workspace access could not be verified during {operation}: {exc}",
                    context=FailureContext(
                        operation=operation,
                        dataset_item_id=dataset_item_id,
                    ),
                ) from exc

    def sync_dataset(
        self,
        source: DatasetSource,
        items: list[DatasetItem],
        *,
        progress: ProgressReporter | None = None,
    ) -> DatasetSyncResult:
        self.check_reachable(operation="sync-dataset")
        name = source.langfuse_dataset_name or source.langfuse_dataset_id
        if not name:
            raise ConfigError("Dataset sync requires a Langfuse dataset name or ID")
        compatibility_version = source.langfuse_dataset_version or dataset_compatibility_version(items)
        self.calls.append(("sync_dataset", {"name": name, "item_count": len(items)}))
        if source.kind != DatasetKind.LANGFUSE:
            create_dataset_item = None
            if self.client is not None:
                create_dataset = getattr(self.client, "create_dataset", None)
                if callable(create_dataset):
                    try:
                        create_dataset(
                            name=name,
                            metadata={
                                "source_kind": source.kind.value,
                                "compatibility_version": compatibility_version,
                            },
                        )
                    except Exception:
                        # Dataset may already exist; item sync below is idempotent by source ID.
                        pass
                create_dataset_item = getattr(self.client, "create_dataset_item", None)
            synced_items: list[dict[str, Any]] = []
            reporter = progress or NullProgressReporter()
            with reporter.task("Syncing dataset items", total=len(items)) as task:
                for item in items:
                    if callable(create_dataset_item):
                        create_dataset_item(
                            dataset_name=name,
                            id=f"{name}:{item.item_id}",
                            input={"input": item.input},
                            expected_output=item.ground_truth or item.reference_output,
                            metadata={
                                **item.metadata,
                                "item_id": item.item_id,
                                "input_hash": item.input_hash,
                                "compatibility_version": compatibility_version,
                            },
                        )
                    synced_items.append(
                        {
                            "id": item.item_id,
                            "langfuse_item_id": f"{name}:{item.item_id}",
                            "input": item.input,
                            "expected_output": item.ground_truth or item.reference_output,
                            "metadata": {
                                **item.metadata,
                                "item_id": item.item_id,
                                "input_hash": item.input_hash,
                            },
                        }
                    )
                    task.advance()
            self.datasets[name] = synced_items
            status = "synced"
        else:
            self.datasets.setdefault(name, [])
            status = "resolved"
        version = source.langfuse_dataset_version or "latest"
        return DatasetSyncResult(
            name=name,
            version=version,
            compatibility_version=compatibility_version,
            item_count=len(items),
            status=status,
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
        if self.client is None:
            return
        api = getattr(self.client, "api", None)
        dataset_run_items = getattr(api, "dataset_run_items", None)
        create = getattr(dataset_run_items, "create", None)
        if not callable(create):
            return
        payload = {
            "run_name": run_name,
            "metadata": metadata,
            "trace_id": trace_id,
            "observation_id": observation_id,
        }
        try:
            create(
                dataset_item_id=f"{dataset_sync.name}:{item_id}",
                **payload,
            )
            return
        except Exception:
            fallback_item_id = self._find_dataset_item_id(
                dataset_name=dataset_sync.name,
                item_id=item_id,
            )
            if not fallback_item_id:
                return
        try:
            create(dataset_item_id=fallback_item_id, **payload)
        except Exception:
            return

    def _find_dataset_item_id(self, *, dataset_name: str, item_id: str) -> str | None:
        if self.client is None:
            return None
        api = getattr(self.client, "api", None)
        dataset_items = getattr(api, "dataset_items", None)
        list_items = getattr(dataset_items, "list", None)
        if not callable(list_items):
            return None
        try:
            page = list_items(dataset_name=dataset_name, limit=100)
        except Exception:
            return None
        items = getattr(page, "data", None) or getattr(page, "items", None) or []
        for item in items:
            metadata = getattr(item, "metadata", None) or {}
            if str(metadata.get("item_id")) == str(item_id):
                value = getattr(item, "id", None)
                return str(value) if value else None
        return None

    def sync_score_configs(
        self,
        config: ProjectConfig,
        *,
        progress: ProgressReporter | None = None,
    ) -> list[ScoreConfigSyncResult]:
        self.check_reachable(operation="sync-score-configs")
        results: list[ScoreConfigSyncResult] = []
        reporter = progress or NullProgressReporter()
        with reporter.task("Syncing score configs", total=len(config.evaluators)) as task:
            for evaluator in config.evaluators:
                results.append(self._sync_one_score_config(config, evaluator))
                task.advance()
        self.calls.append(("sync_score_configs", {"count": len(results)}))
        return results

    def _sync_one_score_config(
        self,
        config: ProjectConfig,
        evaluator: Any,
    ) -> ScoreConfigSyncResult:
        score = evaluator.score
        if not score.managed_by_harness:
            score_config_id = score.langfuse_score_config_id
            if not score_config_id:
                raise ConfigError(
                    f"Evaluator {evaluator.name} requires langfuse_score_config_id"
                )
            return ScoreConfigSyncResult(
                evaluator_name=evaluator.name,
                name=score_config_id,
                score_config_id=score_config_id,
                status="user_owned",
                ownership="user_owned",
            )

        managed_name = f"{config.project.score_config_prefix}{score.name}"
        payload = self._score_payload(managed_name, score)
        self._load_live_score_configs_by_name(managed_name, payload)
        existing = self.score_configs.get(managed_name)
        if existing is None:
            score_config_id = f"score-config-{len(self.score_configs) + 1}"
            if self.client is not None:
                score_config_id = self._create_live_score_config(payload) or score_config_id
            self.score_configs[managed_name] = {
                "id": score_config_id,
                **payload,
                "archived": False,
            }
            status = "created"
        else:
            self._assert_score_config_compatible(managed_name, existing, payload)
            score_config_id = str(existing["id"])
            status = "reused"
        return ScoreConfigSyncResult(
            evaluator_name=evaluator.name,
            name=managed_name,
            score_config_id=score_config_id,
            status=status,
            ownership="managed_by_harness",
        )

    def list_evaluators(self) -> list[dict[str, Any]]:
        self.check_reachable(operation="list-evaluators")
        self.calls.append(("list_evaluators", {}))
        if self.client is not None:
            return self._list_live_evaluators()
        return list(self.evaluators.values())

    def get_evaluator(self, evaluator_id: str) -> dict[str, Any] | None:
        self.check_reachable(operation="get-evaluator")
        self.calls.append(("get_evaluator", {"evaluator_id": evaluator_id}))
        if self.client is not None:
            try:
                return self._get_live_evaluator(evaluator_id)
            except NotImplementedError:
                return None
        return self.evaluators.get(evaluator_id)

    def create_evaluator(self, payload: dict[str, Any]) -> dict[str, Any]:
        self.check_reachable(operation="create-evaluator")
        self.calls.append(("create_evaluator", payload))
        if self.client is not None:
            return self._create_live_evaluator(payload)
        evaluator_id = f"eval-{len(self.evaluators) + 1}"
        evaluator = {"id": evaluator_id, **payload, "active": True}
        self.evaluators[evaluator_id] = evaluator
        return evaluator

    def update_evaluator(
        self,
        evaluator_id: str,
        changes: dict[str, Any],
    ) -> dict[str, Any]:
        self.check_reachable(operation="update-evaluator")
        self.calls.append(
            ("update_evaluator", {"evaluator_id": evaluator_id, "changes": changes})
        )
        if self.client is not None:
            return self._update_live_evaluator(evaluator_id, changes)
        if evaluator_id not in self.evaluators:
            raise ConfigError(f"Evaluator not found: {evaluator_id}")
        self.evaluators[evaluator_id].update(changes)
        return self.evaluators[evaluator_id]

    def inactivate_evaluator(
        self,
        evaluator_id: str,
        *,
        comment: str | None = None,
    ) -> dict[str, Any]:
        self.check_reachable(operation="inactivate-evaluator")
        self.calls.append(
            (
                "inactivate_evaluator",
                {"evaluator_id": evaluator_id, "comment": comment},
            )
        )
        changes = {"active": False}
        if comment:
            changes["comment"] = comment
        return self.update_evaluator(evaluator_id, changes)

    def supports_evaluator_backfill(self, target: str) -> bool:
        return target in self.evaluator_backfill_targets

    def _list_live_evaluators(self) -> list[dict[str, Any]]:
        api = getattr(self.client, "api", None)
        evaluators = getattr(api, "evaluators", None)
        list_evaluators = getattr(evaluators, "list", None) or getattr(evaluators, "get", None)
        if not callable(list_evaluators):
            return self._list_rest_evaluators()
        try:
            page = list_evaluators(limit=100)
        except Exception as exc:
            raise LangfuseError(f"Unable to list Langfuse evaluators: {exc}") from exc
        return [_object_to_evaluator_dict(item) for item in getattr(page, "data", [])]

    def _get_live_evaluator(self, evaluator_id: str) -> dict[str, Any]:
        api = getattr(self.client, "api", None)
        evaluators = getattr(api, "evaluators", None)
        get_by_id = getattr(evaluators, "get_by_id", None) or getattr(evaluators, "get", None)
        if not callable(get_by_id):
            return self._get_rest_evaluator(evaluator_id)
        try:
            return _object_to_evaluator_dict(get_by_id(evaluator_id))
        except Exception as exc:
            raise LangfuseError(f"Unable to get Langfuse evaluator {evaluator_id}: {exc}") from exc

    def _create_live_evaluator(self, payload: dict[str, Any]) -> dict[str, Any]:
        api = getattr(self.client, "api", None)
        evaluators = getattr(api, "evaluators", None)
        create = getattr(evaluators, "create", None)
        if not callable(create):
            return self._create_rest_evaluator(payload)
        try:
            return _object_to_evaluator_dict(create(**payload))
        except Exception as exc:
            raise LangfuseError(
                f"Unable to create Langfuse evaluator {payload.get('display_name')}: {exc}"
            ) from exc

    def _update_live_evaluator(
        self,
        evaluator_id: str,
        changes: dict[str, Any],
    ) -> dict[str, Any]:
        api = getattr(self.client, "api", None)
        evaluators = getattr(api, "evaluators", None)
        update = getattr(evaluators, "update", None)
        if not callable(update):
            return self._update_rest_evaluator(evaluator_id, changes)
        try:
            return _object_to_evaluator_dict(update(evaluator_id, **changes))
        except Exception as exc:
            raise LangfuseError(f"Unable to update Langfuse evaluator {evaluator_id}: {exc}") from exc

    def _list_rest_evaluators(self) -> list[dict[str, Any]]:
        payload = self._rest_evaluator_request(
            "GET",
            UNSTABLE_EVALUATION_RULES_PATH,
            operation="list Langfuse evaluators",
        )
        return [_object_to_evaluator_dict(item) for item in _extract_rest_collection(payload)]

    def _get_rest_evaluator(self, evaluator_id: str) -> dict[str, Any] | None:
        try:
            payload = self._rest_evaluator_request(
                "GET",
                f"{UNSTABLE_EVALUATION_RULES_PATH}/{evaluator_id}",
                operation=f"get Langfuse evaluator {evaluator_id}",
            )
        except LangfuseError as exc:
            if "404" in str(exc):
                return None
            raise
        return _object_to_evaluator_dict(payload)

    def _create_rest_evaluator(self, payload: dict[str, Any]) -> dict[str, Any]:
        evaluator_ref = self._resolve_rest_evaluator_reference(payload)
        response = self._rest_evaluator_request(
            "POST",
            UNSTABLE_EVALUATION_RULES_PATH,
            json_payload=_rest_evaluation_rule_payload(payload, evaluator_ref=evaluator_ref),
            operation=f"create Langfuse evaluator {payload.get('display_name')}",
        )
        return _object_to_evaluator_dict(response)

    def _update_rest_evaluator(
        self,
        evaluator_id: str,
        changes: dict[str, Any],
    ) -> dict[str, Any]:
        response = self._rest_evaluator_request(
            "PATCH",
            f"{UNSTABLE_EVALUATION_RULES_PATH}/{evaluator_id}",
            json_payload=_rest_evaluation_rule_update_payload(changes),
            operation=f"update Langfuse evaluator {evaluator_id}",
        )
        return _object_to_evaluator_dict(response)

    def _resolve_rest_evaluator_reference(self, payload: dict[str, Any]) -> dict[str, str]:
        source_type = payload.get("source_type")
        if source_type == "catalog":
            name = str(payload.get("catalog_ref") or payload.get("name") or payload.get("display_name"))
            return {"name": name, "scope": "managed"}
        evaluator_name = str(payload.get("name") or payload.get("display_name"))
        if source_type == "custom" or payload.get("prompt"):
            evaluator_payload = _rest_custom_evaluator_payload(payload)
            created = self._rest_evaluator_request(
                "POST",
                UNSTABLE_EVALUATORS_PATH,
                json_payload=evaluator_payload,
                operation=f"create Langfuse evaluator template {evaluator_name}",
            )
            return {
                "name": str(created.get("name") or evaluator_name),
                "scope": str(created.get("scope") or "project"),
            }
        return {"name": evaluator_name, "scope": str(payload.get("evaluator_scope") or "project")}

    def _rest_evaluator_request(
        self,
        method: str,
        path: str,
        *,
        operation: str,
        json_payload: dict[str, Any] | None = None,
    ) -> Any:
        if self.settings is None:
            raise NotImplementedError(
                "Installed Langfuse SDK/API does not expose evaluator operations "
                "and REST credentials are unavailable"
            )
        self.settings.require_langfuse()
        try:
            with httpx.Client(
                base_url=str(self.settings.langfuse_host).rstrip("/"),
                auth=(
                    str(self.settings.langfuse_public_key),
                    str(self.settings.langfuse_secret_key),
                ),
                timeout=30.0,
                transport=self.http_transport,
            ) as http_client:
                response = http_client.request(method, path, json=json_payload)
                response.raise_for_status()
                if not response.content:
                    return {}
                return response.json()
        except httpx.HTTPStatusError as exc:
            body = exc.response.text[:500]
            raise LangfuseError(
                f"Unable to {operation} via unstable evaluation-rules REST API: "
                f"HTTP {exc.response.status_code} {body}"
            ) from exc
        except httpx.HTTPError as exc:
            raise LangfuseError(
                f"Unable to {operation} via unstable evaluation-rules REST API: {exc}"
            ) from exc

    def _load_live_score_configs_by_name(self, name: str, expected: dict[str, Any]) -> None:
        if self.client is None:
            return
        api = getattr(self.client, "api", None)
        score_configs = getattr(api, "score_configs", None)
        get = getattr(score_configs, "get", None)
        if not callable(get):
            return
        try:
            page = get(limit=100)
        except Exception as exc:
            raise LangfuseError(f"Unable to list score configs: {exc}") from exc

        page_configs = [_object_to_score_config_dict(config) for config in getattr(page, "data", [])]
        matches = [config for config in page_configs if config.get("name") == name]
        active_matches = [config for config in matches if not config.get("archived")]
        compatible_active = [
            config for config in active_matches if _score_config_is_compatible(config, expected)
        ]
        if compatible_active:
            self.score_configs[name] = compatible_active[0]
            return
        if not active_matches:
            archived_matches = [config for config in matches if config.get("archived")]
            if archived_matches:
                self.score_configs[name] = archived_matches[0]
            return
        self.score_configs[name] = active_matches[0]

    def _create_live_score_config(self, payload: dict[str, Any]) -> str | None:
        api = getattr(self.client, "api", None)
        score_configs = getattr(api, "score_configs", None)
        create = getattr(score_configs, "create", None)
        if not callable(create):
            return None
        try:
            from langfuse.api.commons.types.config_category import ConfigCategory
            from langfuse.api.commons.types.score_config_data_type import ScoreConfigDataType

            categories = (
                [
                    ConfigCategory(value=float(index), label=str(category))
                    for index, category in enumerate(payload["categories"] or [])
                ]
                if payload.get("categories")
                else None
            )
            created = create(
                name=payload["name"],
                data_type=ScoreConfigDataType(payload["data_type"]),
                categories=categories,
                min_value=payload.get("min_value"),
                max_value=payload.get("max_value"),
                description=payload.get("description"),
            )
        except Exception:
            return None
        return str(getattr(created, "id", None) or getattr(created, "score_config_id", "") or "") or None

    def align_score_config_to_existing_id(
        self,
        *,
        target_score_config_id: str,
        managed_name: str,
    ) -> None:
        if self.client is None:
            return
        api = getattr(self.client, "api", None)
        score_configs = getattr(api, "score_configs", None)
        get_by_id = getattr(score_configs, "get_by_id", None)
        get = getattr(score_configs, "get", None)
        update = getattr(score_configs, "update", None)
        if not callable(get_by_id) or not callable(get) or not callable(update):
            return
        try:
            target = _object_to_score_config_dict(get_by_id(target_score_config_id))
            if target.get("name") == managed_name and not target.get("archived"):
                self.score_configs[managed_name] = target
                return
            page = get(limit=100)
            for config in getattr(page, "data", []):
                candidate = _object_to_score_config_dict(config)
                if (
                    candidate.get("name") == managed_name
                    and not candidate.get("archived")
                    and candidate.get("id") != target_score_config_id
                ):
                    update(
                        str(candidate["id"]),
                        name=_archived_score_config_name(managed_name, str(candidate["id"])),
                        is_archived=True,
                    )
            updated = update(
                target_score_config_id,
                name=managed_name,
                is_archived=False,
            )
        except Exception as exc:
            raise LangfuseError(
                f"Unable to align queue score config {target_score_config_id} "
                f"to managed name {managed_name}: {exc}"
            ) from exc
        self.score_configs[managed_name] = _object_to_score_config_dict(updated)

    def create_run(self, *args: Any, **kwargs: Any) -> Any:
        self.calls.append(("create_run", {"args": args, "kwargs": kwargs}))
        run_id = str(kwargs.get("run_id") or (args[0] if args else f"run-{len(self.runs) + 1}"))
        run = {"run_id": run_id, "args": args, "kwargs": kwargs}
        self.runs[run_id] = run
        return run

    def log_trace(self, trace: dict[str, Any]) -> dict[str, Any]:
        stored_trace = {
            key: value
            for key, value in trace.items()
            if key != "_live_observation_logged"
        }
        self.calls.append(("log_trace", stored_trace))
        self.traces.append(stored_trace)
        if self.client is not None and not trace.get("_live_observation_logged"):
            create_event = getattr(self.client, "create_event", None)
            if callable(create_event):
                try:
                    create_event(
                        trace_context={"trace_id": str(trace["trace_id"])},
                        name=trace.get("name"),
                        input=trace.get("input"),
                        output=trace.get("output"),
                        metadata=trace.get("metadata") or {},
                    )
                    flush = getattr(self.client, "flush", None)
                    if callable(flush):
                        flush()
                except Exception as exc:
                    raise LangfuseError(
                        f"Unable to create Langfuse trace {trace.get('trace_id')}: {exc}"
                    ) from exc
        return stored_trace

    @contextmanager
    def trace_span(
        self,
        *,
        trace_id: str,
        name: str,
        input: Any,
        metadata: dict[str, Any],
    ):
        start = (
            getattr(self.client, "start_as_current_observation", None)
            if self.client is not None
            else None
        )
        if not callable(start):
            yield None
            return
        with start(
            trace_context={"trace_id": trace_id},
            as_type="span",
            name=name,
            input=input,
            metadata=metadata,
        ) as observation:
            yield observation
        flush = getattr(self.client, "flush", None)
        if callable(flush):
            flush()

    @contextmanager
    def generation_span(
        self,
        *,
        name: str,
        input: Any,
        metadata: dict[str, Any],
        model: str,
        model_parameters: dict[str, Any],
    ):
        start = (
            getattr(self.client, "start_as_current_observation", None)
            if self.client is not None
            else None
        )
        if not callable(start):
            yield None
            return
        with start(
            as_type="generation",
            name=name,
            input=input,
            metadata=metadata,
            model=model,
            model_parameters=model_parameters,
        ) as observation:
            yield observation
        flush = getattr(self.client, "flush", None)
        if callable(flush):
            flush()

    def observation_id(self, observation: Any | None) -> str | None:
        if observation is None:
            return None
        value = getattr(observation, "id", None) or getattr(
            observation, "observation_id", None
        )
        return str(value) if value else None

    def update_trace_span(self, observation: Any | None, trace: dict[str, Any]) -> bool:
        if observation is None:
            return False
        update = getattr(observation, "update", None)
        if not callable(update):
            return False
        update(
            output=trace.get("output"),
            metadata=trace.get("metadata") or {},
            level="ERROR" if trace.get("error") else "DEFAULT",
            status_message=trace.get("error"),
        )
        flush = getattr(self.client, "flush", None) if self.client is not None else None
        if callable(flush):
            flush()
        return True

    def update_generation_span(self, observation: Any | None, response: Any) -> bool:
        if observation is None:
            return False
        update = getattr(observation, "update", None)
        if not callable(update):
            return False
        usage_details = None
        if response.input_tokens is not None or response.output_tokens is not None:
            usage_details = {
                key: value
                for key, value in {
                    "input": response.input_tokens,
                    "output": response.output_tokens,
                }.items()
                if value is not None
            }
        cost_details = (
            {"total": response.cost_usd}
            if response.cost_usd is not None
            else None
        )
        update(
            output=response.output,
            usage_details=usage_details,
            cost_details=cost_details,
        )
        return True

    def create_trace_id(self, seed: str) -> str:
        if self.client is not None:
            create_trace_id = getattr(self.client, "create_trace_id", None)
            if callable(create_trace_id):
                return str(create_trace_id(seed=seed))
        return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:32]

    def lookup_baseline(self, *args: Any, **kwargs: Any) -> Any:
        self.calls.append(("lookup_baseline", {"args": args, "kwargs": kwargs}))
        selector = str(kwargs.get("selector") or (args[0] if args else "latest-compatible"))
        fingerprint = kwargs.get("fingerprint") or (args[1] if len(args) > 1 else None)
        live_reference = self._lookup_live_baseline(selector=selector, fingerprint=fingerprint)
        if live_reference is not None:
            return live_reference
        if selector != "latest-compatible":
            reference = self.baseline_references.get(selector)
            if reference is not None and _reference_matches(reference, fingerprint):
                return reference
            return None
        for reference in reversed(list(self.baseline_references.values())):
            if _reference_matches(reference, fingerprint):
                return reference
        return None

    def _lookup_live_baseline(self, *, selector: str, fingerprint: Any) -> Any | None:
        if self.client is None or fingerprint is None:
            return None
        get_dataset_runs = getattr(self.client, "get_dataset_runs", None)
        if not callable(get_dataset_runs):
            return None
        dataset_name = getattr(fingerprint, "dataset_name", None)
        if not dataset_name:
            return None
        try:
            page = get_dataset_runs(dataset_name=dataset_name, limit=100)
        except Exception:
            return None
        runs = getattr(page, "data", None) or getattr(page, "runs", None) or []
        matches: list[Any] = []
        for run in runs:
            metadata = self._dataset_run_metadata(
                dataset_name=str(dataset_name),
                fingerprint=fingerprint,
                run=run,
            )
            if metadata.get("run_type") not in {None, "baseline"}:
                continue
            if selector != "latest-compatible":
                run_name = getattr(run, "name", None) or getattr(run, "run_name", None)
                if selector not in {str(run_name), str(metadata.get("baseline_run_id"))}:
                    continue
            if _metadata_matches(metadata, fingerprint):
                matches.append(run)
        if not matches:
            return None
        run = matches[-1]
        metadata = getattr(run, "metadata", None) or {}
        from evaluator_harness.config import BaselineReference

        return BaselineReference(
            baseline_run_id=str(
                metadata.get("baseline_run_id")
                or getattr(run, "name", None)
                or getattr(run, "run_name", None)
            ),
            langfuse_run_name=str(getattr(run, "name", None) or getattr(run, "run_name", None)),
            created_at=str(metadata.get("created_at") or ""),
            **{field: _metadata_fingerprint_value(metadata, field) for field in _FINGERPRINT_FIELDS},
        )

    def _dataset_run_metadata(
        self,
        *,
        dataset_name: str,
        fingerprint: Any,
        run: Any,
    ) -> dict[str, Any]:
        metadata = getattr(run, "metadata", None) or {}
        if metadata and _metadata_matches(dict(metadata), fingerprint):
            return dict(metadata)
        get_dataset_run = getattr(self.client, "get_dataset_run", None)
        run_name = getattr(run, "name", None) or getattr(run, "run_name", None)
        if not callable(get_dataset_run) or not run_name:
            return {}
        try:
            run_with_items = get_dataset_run(
                dataset_name=dataset_name,
                run_name=str(run_name),
            )
        except Exception:
            return {}
        items = getattr(run_with_items, "items", None) or []
        for item in items:
            item_metadata = getattr(item, "metadata", None) or {}
            if item_metadata and _metadata_matches(dict(item_metadata), fingerprint):
                return dict(item_metadata)
        return dict(metadata)

    def record_baseline_reference(self, run_id: str, reference: Any) -> None:
        self.baseline_references[run_id] = reference

    def enqueue_baseline_evaluator_payload(self, payload: dict[str, Any]) -> None:
        self.baseline_evaluator_payloads.append(payload)

    def enqueue_candidate_evaluator_payload(self, payload: dict[str, Any]) -> None:
        self.candidate_evaluator_payloads.append(payload)

    def output_for(self, *, run_id: str, item_id: str) -> str | None:
        for trace in self.traces:
            if trace.get("run_id") == run_id and trace.get("metadata", {}).get("dataset_item_id") == item_id:
                output = trace.get("output")
                return str(output) if output is not None else None
        return None

    def fetch_scores(self, run_id: str) -> list[dict[str, Any]]:
        self.check_reachable(operation="fetch-scores")
        self.calls.append(("fetch_scores", {"run_id": run_id}))
        return self.scores.get(run_id, [])

    def traces_for_run(
        self,
        run_id: str,
        *,
        dataset_names: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        traces = [trace for trace in self.traces if trace.get("run_id") == run_id]
        if traces or self.client is None:
            return traces
        live_traces = self._live_traces_for_run(run_id, dataset_names=dataset_names)
        self.traces.extend(live_traces)
        return live_traces

    def _live_traces_for_run(
        self,
        run_id: str,
        *,
        dataset_names: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        trace_client = getattr(getattr(self.client, "api", None), "trace", None)
        list_traces = getattr(trace_client, "list", None)
        if not callable(list_traces):
            return self._live_dataset_run_traces_for_run(
                run_id,
                dataset_names=dataset_names,
            )
        filters = [
            f'metadata.run_id = "{run_id}"',
            f"metadata.run_id = {run_id}",
        ]
        for filter_expression in filters:
            try:
                page = list_traces(limit=100, filter=filter_expression)
            except Exception:
                continue
            traces = [
                _live_trace_to_dict(trace)
                for trace in (getattr(page, "data", None) or [])
            ]
            traces = [trace for trace in traces if trace.get("run_id") == run_id]
            if traces:
                return traces
        return self._live_dataset_run_traces_for_run(
            run_id,
            dataset_names=dataset_names,
        )

    def _live_dataset_run_traces_for_run(
        self,
        run_id: str,
        *,
        dataset_names: list[str] | None = None,
    ) -> list[dict[str, Any]]:
        get_dataset_runs = getattr(self.client, "get_dataset_runs", None)
        if not callable(get_dataset_runs):
            return []
        traces: list[dict[str, Any]] = []
        for dataset_name in dataset_names or self._candidate_dataset_names():
            try:
                page = get_dataset_runs(dataset_name=dataset_name, limit=100)
            except Exception:
                continue
            for run in getattr(page, "data", None) or getattr(page, "runs", None) or []:
                run_name = getattr(run, "name", None) or getattr(run, "run_name", None)
                if str(run_name) != run_id:
                    continue
                metadata = getattr(run, "metadata", None) or {}
                trace = _trace_from_metadata(dict(metadata), run_id=run_id)
                if trace is not None:
                    traces.append(trace)
                    continue
                traces.extend(
                    self._live_dataset_run_item_traces(
                        dataset_name=str(dataset_name),
                        run_id=run_id,
                    )
                )
        return traces

    def _candidate_dataset_names(self) -> list[str]:
        names = {
            str(trace.get("metadata", {}).get("dataset_name"))
            for trace in self.traces
            if trace.get("metadata", {}).get("dataset_name")
        }
        return sorted(names or {"rewrite-quality/v1"})

    def _live_dataset_run_item_traces(
        self,
        *,
        dataset_name: str,
        run_id: str,
    ) -> list[dict[str, Any]]:
        get_dataset_run = getattr(self.client, "get_dataset_run", None)
        if not callable(get_dataset_run):
            return []
        try:
            run_with_items = get_dataset_run(
                dataset_name=dataset_name,
                run_name=run_id,
            )
        except Exception:
            return []
        traces: list[dict[str, Any]] = []
        for item in getattr(run_with_items, "items", None) or []:
            metadata = getattr(item, "metadata", None) or {}
            trace = _trace_from_metadata(dict(metadata), run_id=run_id)
            if trace is not None:
                traces.append(trace)
        return traces

    def trace_by_id(self, trace_id: str) -> dict[str, Any]:
        for trace in self.traces:
            if trace.get("trace_id") == trace_id:
                return trace
        raise ConfigError(f"Trace not found: {trace_id}")

    def build_annotation_queue_payload(
        self,
        config: ProjectConfig,
        selection: Any,
    ) -> dict[str, Any]:
        trace = self.trace_by_id(selection.trace_id)
        metadata = trace.get("metadata", {})
        baseline_reference = metadata.get("baseline_reference") or {}
        baseline_run_id = baseline_reference.get("baseline_run_id")
        baseline_output = (
            self.output_for(run_id=baseline_run_id, item_id=selection.item_id)
            if baseline_run_id
            else trace.get("output")
        )
        candidate_output = trace.get("output") if baseline_run_id else None
        return {
            "queue_item_id": f"{selection.run_id}:{selection.trace_id}",
            "run_id": selection.run_id,
            "trace_id": selection.trace_id,
            "item_id": selection.item_id,
            "selection_reason": selection.selection_reason,
            "selection_bucket": selection.selection_bucket,
            "input": trace.get("input"),
            "baseline_output": baseline_output,
            "candidate_output": candidate_output,
            "ground_truth": metadata.get("ground_truth"),
            "trace_context": {
                "trace_id": selection.trace_id,
                "run_id": selection.run_id,
                "prompt_shape": metadata.get("prompt_shape"),
                "prompt_roles": metadata.get("prompt_roles"),
                "prompt_identity": metadata.get("prompt_identity"),
                "baseline_prompt_identity": metadata.get("baseline_prompt_identity"),
                "candidate_prompt_identity": metadata.get("candidate_prompt_identity"),
                "parameter_identity": metadata.get("parameter_identity"),
                "generation_parameter_hash": metadata.get("generation_parameter_hash"),
                "variant_identity": metadata.get("variant_identity"),
            },
            "evaluators": [
                {
                    "name": evaluator.name,
                    "version": evaluator.version,
                    "type": evaluator.type,
                }
                if evaluator.blind
                else {
                    "name": evaluator.name,
                    "version": evaluator.version,
                    "type": evaluator.type,
                    "provider": metadata.get("provider"),
                    "model": metadata.get("model"),
                }
                for evaluator in config.evaluators
            ],
        }

    def route_annotation_items(
        self,
        queue_id: str,
        items: list[dict[str, Any]],
    ) -> AnnotationRoutingResult:
        self.check_reachable(operation="route-annotation-items")
        queued_count = 0
        skipped_duplicate_count = 0
        for item in items:
            queue_item_id = str(
                item.get("queue_item_id")
                or f"{item.get('run_id')}:{item.get('trace_id')}"
            )
            key = (queue_id, queue_item_id)
            if key in self._annotation_queue_keys:
                skipped_duplicate_count += 1
                continue
            self._annotation_queue_keys.add(key)
            routed_item = {
                "queue_id": queue_id,
                "queue_item_id": queue_item_id,
                "object_id": item.get("trace_id"),
                "object_type": "TRACE",
                **item,
            }
            if self.client is not None:
                live_item = self._create_live_annotation_queue_item(
                    queue_id,
                    object_id=str(item.get("trace_id")),
                )
                if live_item is not None:
                    routed_item["langfuse_queue_item_id"] = live_item.get("id")
            self.annotation_queue_items.append(routed_item)
            queued_count += 1
        self.calls.append(
            (
                "route_annotation_items",
                {
                    "queue_id": queue_id,
                    "queued_count": queued_count,
                    "skipped_duplicate_count": skipped_duplicate_count,
                },
            )
        )
        return AnnotationRoutingResult(
            queue_id=queue_id,
            queued_count=queued_count,
            skipped_duplicate_count=skipped_duplicate_count,
        )

    def create_annotation_queue(
        self,
        *,
        name: str,
        score_config_ids: list[str],
        description: str | None = None,
    ) -> dict[str, Any]:
        self.check_reachable(operation="create-annotation-queue")
        self.calls.append(
            (
                "create_annotation_queue",
                {
                    "name": name,
                    "score_config_ids": score_config_ids,
                    "description": description,
                },
            )
        )
        if self.client is not None:
            live_queue = self._create_live_annotation_queue(
                name=name,
                score_config_ids=score_config_ids,
                description=description,
            )
            if live_queue is not None:
                self.annotation_queues[str(live_queue["id"])] = live_queue
                return live_queue
        queue = {
            "id": f"annotation-queue-{len(self.annotation_queues) + 1}",
            "name": name,
            "score_config_ids": list(score_config_ids),
            "description": description,
        }
        self.annotation_queues[queue["id"]] = queue
        return queue

    def list_annotation_queues(self) -> list[dict[str, Any]]:
        self.check_reachable(operation="list-annotation-queues")
        self.calls.append(("list_annotation_queues", {}))
        if self.client is not None:
            live_queues = self._list_live_annotation_queues()
            if live_queues is not None:
                for queue in live_queues:
                    self.annotation_queues[str(queue["id"])] = queue
                return live_queues
        return list(self.annotation_queues.values())

    def get_annotation_queue(self, queue_id: str) -> dict[str, Any]:
        self.check_reachable(operation="get-annotation-queue")
        self.calls.append(("get_annotation_queue", {"queue_id": queue_id}))
        if self.client is not None:
            live_queue = self._get_live_annotation_queue(queue_id)
            if live_queue is not None:
                self.annotation_queues[str(live_queue["id"])] = live_queue
                return live_queue
        queue = self.annotation_queues.get(queue_id)
        if queue is None:
            raise ConfigError(f"Annotation queue not found: {queue_id}")
        return queue

    def _create_live_annotation_queue(
        self,
        *,
        name: str,
        score_config_ids: list[str],
        description: str | None,
    ) -> dict[str, Any] | None:
        annotation_queues = getattr(getattr(self.client, "api", None), "annotation_queues", None)
        create_queue = getattr(annotation_queues, "create_queue", None)
        if not callable(create_queue):
            return None
        try:
            queue = create_queue(
                name=name,
                score_config_ids=score_config_ids,
                description=description,
            )
        except Exception as exc:
            raise LangfuseError(f"Unable to create annotation queue {name}: {exc}") from exc
        return _object_to_queue_dict(queue)

    def _list_live_annotation_queues(self) -> list[dict[str, Any]] | None:
        annotation_queues = getattr(getattr(self.client, "api", None), "annotation_queues", None)
        list_queues = getattr(annotation_queues, "list_queues", None)
        if not callable(list_queues):
            return None
        try:
            page = list_queues(limit=100)
        except Exception as exc:
            raise LangfuseError(f"Unable to list annotation queues: {exc}") from exc
        return [_object_to_queue_dict(queue) for queue in getattr(page, "data", [])]

    def _get_live_annotation_queue(self, queue_id: str) -> dict[str, Any] | None:
        annotation_queues = getattr(getattr(self.client, "api", None), "annotation_queues", None)
        get_queue = getattr(annotation_queues, "get_queue", None)
        if not callable(get_queue):
            return None
        try:
            queue = get_queue(queue_id)
        except Exception as exc:
            raise LangfuseError(f"Unable to get annotation queue {queue_id}: {exc}") from exc
        return _object_to_queue_dict(queue)

    def _create_live_annotation_queue_item(
        self,
        queue_id: str,
        *,
        object_id: str,
    ) -> dict[str, Any] | None:
        annotation_queues = getattr(getattr(self.client, "api", None), "annotation_queues", None)
        create_queue_item = getattr(annotation_queues, "create_queue_item", None)
        if not callable(create_queue_item):
            return None
        try:
            from langfuse.api.annotation_queues.types.annotation_queue_object_type import (
                AnnotationQueueObjectType,
            )
            from langfuse.api.annotation_queues.types.annotation_queue_status import (
                AnnotationQueueStatus,
            )

            item = create_queue_item(
                queue_id,
                object_id=object_id,
                object_type=AnnotationQueueObjectType.TRACE,
                status=AnnotationQueueStatus.PENDING,
            )
        except Exception as exc:
            message = str(exc).lower()
            if "duplicate" in message or "already" in message:
                return None
            raise LangfuseError(
                f"Unable to create annotation queue item for trace {object_id}: {exc}"
            ) from exc
        return _object_to_queue_dict(item)

    def _score_payload(self, managed_name: str, score: ScoreConfigRef) -> dict[str, Any]:
        return {
            "name": managed_name,
            "data_type": score.data_type.value,
            "min_value": score.min_value,
            "max_value": score.max_value,
            "categories": score.categories or None,
            "description": score.description,
        }

    def _assert_score_config_compatible(
        self,
        managed_name: str,
        existing: dict[str, Any],
        expected: dict[str, Any],
    ) -> None:
        if existing.get("archived"):
            raise ConfigError(
                f"Score config {managed_name} is archived and still conflicts"
            )
        compared_fields = ["name", "data_type", "min_value", "max_value", "categories"]
        differences = [
            field
            for field in compared_fields
            if existing.get(field) != expected.get(field)
        ]
        if differences:
            raise ConfigError(
                f"Score config {managed_name} has incompatible schema: "
                + ", ".join(differences)
            )


def _reference_matches(reference: Any, fingerprint: Any) -> bool:
    if fingerprint is None:
        return True
    ref_data = (
        reference.model_dump(mode="json")
        if hasattr(reference, "model_dump")
        else dict(reference)
    )
    fp_data = (
        fingerprint.model_dump(mode="json")
        if hasattr(fingerprint, "model_dump")
        else getattr(fingerprint, "__dict__", {})
    )
    return all(ref_data.get(field) == fp_data.get(field) for field in _FINGERPRINT_FIELDS)


def _metadata_matches(metadata: dict[str, Any], fingerprint: Any) -> bool:
    fp_data = (
        fingerprint.model_dump(mode="json")
        if hasattr(fingerprint, "model_dump")
        else getattr(fingerprint, "__dict__", {})
    )
    return all(
        _metadata_fingerprint_value(metadata, field) == str(fp_data.get(field))
        for field in _FINGERPRINT_FIELDS
    )


def _metadata_fingerprint_value(metadata: dict[str, Any], field: str) -> str:
    if field == "dataset_version":
        value = metadata.get("dataset_compatibility_version") or metadata.get(field)
    else:
        value = metadata.get(field)
    return str(value)


def _live_trace_to_dict(trace: Any) -> dict[str, Any]:
    metadata = getattr(trace, "metadata", None) or {}
    trace_id = str(getattr(trace, "id", None) or metadata.get("trace_id"))
    run_id = str(metadata.get("run_id") or "")
    return {
        "trace_id": trace_id,
        "run_id": run_id,
        "name": getattr(trace, "name", None),
        "input": getattr(trace, "input", None),
        "output": getattr(trace, "output", None),
        "error": metadata.get("error"),
        "metadata": dict(metadata),
        "timestamp": str(getattr(trace, "timestamp", None) or ""),
    }


def _trace_from_metadata(metadata: dict[str, Any], *, run_id: str) -> dict[str, Any] | None:
    trace_id = metadata.get("trace_id")
    if not trace_id:
        return None
    return {
        "trace_id": str(trace_id),
        "run_id": str(metadata.get("run_id") or run_id),
        "name": metadata.get("trace_name"),
        "input": None,
        "output": None,
        "error": metadata.get("error"),
        "metadata": metadata,
        "timestamp": "",
    }


def _object_to_queue_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        raw = value
    elif hasattr(value, "model_dump"):
        raw = value.model_dump(mode="json")
    elif hasattr(value, "dict"):
        raw = value.dict()
    else:
        raw = {
            key: getattr(value, key)
            for key in ("id", "name", "description", "score_config_ids", "scoreConfigIds")
            if hasattr(value, key)
        }
    if "scoreConfigIds" in raw and "score_config_ids" not in raw:
        raw["score_config_ids"] = raw["scoreConfigIds"]
    return dict(raw)


def _object_to_score_config_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        raw = dict(value)
    elif hasattr(value, "model_dump"):
        raw = value.model_dump(mode="json")
    elif hasattr(value, "dict"):
        raw = value.dict()
    else:
        raw = {
            key: getattr(value, key)
            for key in (
                "id",
                "name",
                "data_type",
                "min_value",
                "max_value",
                "categories",
                "description",
                "archived",
                "is_archived",
            )
            if hasattr(value, key)
        }
    if "is_archived" in raw and "archived" not in raw:
        raw["archived"] = raw["is_archived"]
    if "isArchived" in raw and "archived" not in raw:
        raw["archived"] = raw["isArchived"]
    if "dataType" in raw and "data_type" not in raw:
        raw["data_type"] = raw["dataType"]
    if "minValue" in raw and "min_value" not in raw:
        raw["min_value"] = raw["minValue"]
    if "maxValue" in raw and "max_value" not in raw:
        raw["max_value"] = raw["maxValue"]
    if hasattr(raw.get("data_type"), "value"):
        raw["data_type"] = raw["data_type"].value
    raw["categories"] = _normalize_score_categories(raw.get("categories"))
    return raw


def _extract_rest_collection(payload: Any) -> list[Any]:
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in ("data", "items", "evaluationRules", "evaluation_rules"):
        value = payload.get(key)
        if isinstance(value, list):
            return value
    return []


def _rest_custom_evaluator_payload(payload: dict[str, Any]) -> dict[str, Any]:
    name = str(payload.get("name") or payload.get("display_name"))
    output_definition = (
        payload.get("outputDefinition")
        or payload.get("output_definition")
        or {
            "dataType": "NUMERIC",
            "reasoning": {"description": "Explain the score."},
            "score": {"description": "Score."},
        }
    )
    result: dict[str, Any] = {
        "name": name,
        "prompt": str(payload.get("prompt") or ""),
        "outputDefinition": output_definition,
    }
    model_config = payload.get("modelConfig") or payload.get("model_config")
    if model_config:
        result["modelConfig"] = model_config
    return result


def _rest_evaluation_rule_payload(
    payload: dict[str, Any],
    *,
    evaluator_ref: dict[str, str],
) -> dict[str, Any]:
    return {
        "name": str(payload.get("name") or payload.get("display_name")),
        "evaluator": evaluator_ref,
        "target": str(payload.get("target") or "observation"),
        "enabled": bool(payload.get("enabled", payload.get("active", True))),
        "sampling": _sampling_fraction(payload.get("sampling_percent")),
        "filter": _rest_evaluation_rule_filters(payload.get("filters") or {}),
        "mapping": _rest_evaluation_rule_mapping(payload.get("variables") or {}),
    }


def _rest_evaluation_rule_update_payload(changes: dict[str, Any]) -> dict[str, Any]:
    payload: dict[str, Any] = {}
    if "display_name" in changes or "name" in changes:
        payload["name"] = str(changes.get("name") or changes.get("display_name"))
    if "active" in changes or "enabled" in changes:
        payload["enabled"] = bool(changes.get("enabled", changes.get("active")))
    if "sampling_percent" in changes:
        payload["sampling"] = _sampling_fraction(changes.get("sampling_percent"))
    if "target" in changes:
        payload["target"] = str(changes["target"])
    if "filters" in changes:
        filters = changes.get("filters") or {}
        payload["target"] = str(filters.get("target") or changes.get("target") or "observation")
        payload["filter"] = _rest_evaluation_rule_filters(filters)
    if "variables" in changes:
        payload["mapping"] = _rest_evaluation_rule_mapping(changes.get("variables") or {})
    return payload


def _sampling_fraction(value: Any) -> float:
    if value is None:
        return 1.0
    numeric = float(value)
    return numeric / 100 if numeric > 1 else numeric


def _rest_evaluation_rule_mapping(variables: dict[str, str]) -> list[dict[str, Any]]:
    mapping: list[dict[str, Any]] = []
    for variable, path in variables.items():
        if path.endswith(".input"):
            mapping.append({"variable": variable, "source": "input"})
        elif path.endswith(".output"):
            mapping.append({"variable": variable, "source": "output"})
        elif ".metadata." in path:
            metadata_key = path.rsplit(".metadata.", 1)[1]
            mapping.append(
                {
                    "variable": variable,
                    "source": "metadata",
                    "jsonPath": f"$.{metadata_key}",
                }
            )
    return mapping


def _rest_evaluation_rule_filters(filters: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for key in ("project", "project_version", "evaluator_set_id", "observation_role"):
        if filters.get(key):
            result.append(
                {
                    "type": "stringObject",
                    "column": "metadata",
                    "key": key,
                    "operator": "contains" if key == "evaluator_set_id" else "=",
                    "value": str(filters[key]),
                }
            )
    return result


def _object_to_evaluator_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        raw = dict(value)
    elif hasattr(value, "model_dump"):
        raw = value.model_dump(mode="json")
    elif hasattr(value, "dict"):
        raw = value.dict()
    else:
        raw = {
            key: getattr(value, key)
            for key in (
                "id",
                "evaluationRuleId",
                "name",
                "display_name",
                "displayName",
                "active",
                "enabled",
                "filters",
                "variables",
                "score_config_id",
                "scoreConfigId",
                "sampling_percent",
                "samplingPercent",
                "target",
            )
            if hasattr(value, key)
        }
    if "evaluationRuleId" in raw and "id" not in raw:
        raw["id"] = raw["evaluationRuleId"]
    if "displayName" in raw and "display_name" not in raw:
        raw["display_name"] = raw["displayName"]
    if "scoreConfigId" in raw and "score_config_id" not in raw:
        raw["score_config_id"] = raw["scoreConfigId"]
    if "samplingPercent" in raw and "sampling_percent" not in raw:
        raw["sampling_percent"] = raw["samplingPercent"]
    if "sampling" in raw and "sampling_percent" not in raw:
        raw["sampling_percent"] = int(float(raw["sampling"]) * 100)
    if "mapping" in raw and "variables" not in raw:
        raw["variables"] = _rest_mapping_to_variables(raw["mapping"])
    if "filter" in raw and "filters" not in raw:
        raw["filters"] = _rest_filters_to_internal(raw["filter"])
    if "enabled" in raw and "active" not in raw:
        raw["active"] = raw["enabled"]
    return raw


def _rest_mapping_to_variables(mapping: Any) -> dict[str, str]:
    if not isinstance(mapping, list):
        return {}
    variables: dict[str, str] = {}
    for item in mapping:
        if not isinstance(item, dict) or not item.get("variable"):
            continue
        source = item.get("source")
        variable = str(item["variable"])
        if source == "input":
            variables[variable] = "observation.input"
        elif source == "output":
            variables[variable] = "observation.output"
        elif source == "metadata":
            json_path = str(item.get("jsonPath") or "")
            metadata_key = json_path[2:] if json_path.startswith("$.") else variable
            variables[variable] = f"trace.metadata.{metadata_key}"
    return variables


def _rest_filters_to_internal(filters: Any) -> dict[str, Any]:
    if not isinstance(filters, list):
        return {}
    internal: dict[str, Any] = {}
    for item in filters:
        if not isinstance(item, dict):
            continue
        column = item.get("column")
        value = item.get("value")
        if column == "name" and isinstance(value, list) and value:
            internal["_has_top_level_name_filter"] = True
        elif column == "environment":
            internal["_has_top_level_environment_filter"] = True
        elif column == "type":
            internal["_has_top_level_type_filter"] = True
        elif column == "metadata" and item.get("key"):
            key = str(item["key"])
            internal[key] = value
            if key == "evaluator_set_id":
                internal["_evaluator_set_id_operator"] = item.get("operator")
    return internal


def _normalize_score_categories(value: Any) -> list[str] | None:
    if value is None:
        return None
    categories: list[str] = []
    for category in value:
        if isinstance(category, str):
            categories.append(category)
        elif isinstance(category, dict):
            categories.append(str(category.get("label") or category.get("value")))
        else:
            categories.append(str(getattr(category, "label", getattr(category, "value", category))))
    return categories


def _score_config_is_compatible(existing: dict[str, Any], expected: dict[str, Any]) -> bool:
    compared_fields = ["name", "data_type", "min_value", "max_value", "categories"]
    return all(existing.get(field) == expected.get(field) for field in compared_fields)


def _archived_score_config_name(old_name: str, config_id: str) -> str:
    suffix = f"_arch_{config_id[:8]}"
    return f"{old_name[: 35 - len(suffix)]}{suffix}"
