from __future__ import annotations

from dataclasses import dataclass
from typing import Any


def callable_attribute(value: Any, name: str) -> Any | None:
    candidate = getattr(value, name, None) if value is not None else None
    return candidate if callable(candidate) else None


def flush_if_supported(client: Any | None) -> None:
    flush = callable_attribute(client, "flush")
    if flush is not None:
        flush()


def update_observation(observation: Any | None, **kwargs: Any) -> bool:
    update = callable_attribute(observation, "update")
    if update is None:
        return False
    update(**kwargs)
    return True


@dataclass
class LangfuseSdkGateway:
    owner: Any
    client: Any
    rest: Any | None = None

    def check_reachable(
        self,
        *,
        operation: str,
        dataset_item_id: str | None = None,
    ) -> None:
        self.owner.check_reachable(operation=operation, dataset_item_id=dataset_item_id)

    def sync_dataset(self, *args: Any, **kwargs: Any) -> Any:
        return self.owner._sync_dataset_impl(*args, **kwargs)

    def record_dataset_run_item(self, **kwargs: Any) -> None:
        self.owner._record_dataset_run_item_impl(**kwargs)

    def sync_score_configs(self, *args: Any, **kwargs: Any) -> Any:
        return self.owner._sync_score_configs_impl(*args, **kwargs)

    def load_live_score_configs_by_name(self, *args: Any, **kwargs: Any) -> Any:
        return self.owner._load_live_score_configs_by_name(*args, **kwargs)

    def create_live_score_config(self, *args: Any, **kwargs: Any) -> Any:
        return self.owner._create_live_score_config(*args, **kwargs)

    def list_evaluators(self) -> list[dict[str, Any]]:
        return self.owner._list_evaluators_impl()

    def get_evaluator(self, evaluator_id: str) -> dict[str, Any] | None:
        return self.owner._get_evaluator_impl(evaluator_id)

    def create_evaluator(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.owner._create_evaluator_impl(payload)

    def update_evaluator(
        self,
        evaluator_id: str,
        changes: dict[str, Any],
    ) -> dict[str, Any]:
        return self.owner._update_evaluator_impl(evaluator_id, changes)

    def lookup_baseline(self, *args: Any, **kwargs: Any) -> Any:
        return self.owner._lookup_baseline_impl(*args, **kwargs)

    def lookup_live_baseline(self, **kwargs: Any) -> Any:
        return self.owner._lookup_live_baseline_impl(**kwargs)

    def dataset_run_metadata(self, **kwargs: Any) -> dict[str, Any]:
        return self.owner._dataset_run_metadata_impl(**kwargs)

    def fetch_scores(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return self.owner._fetch_scores_impl(*args, **kwargs)

    def list_prompt_versions(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return self.owner._list_prompt_versions_impl(*args, **kwargs)

    def create_prompt_version(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self.owner._create_prompt_version_impl(*args, **kwargs)

    def traces_for_run(self, *args: Any, **kwargs: Any) -> list[dict[str, Any]]:
        return self.owner._traces_for_run_impl(*args, **kwargs)

    def route_annotation_items(self, *args: Any, **kwargs: Any) -> Any:
        return self.owner._route_annotation_items_impl(*args, **kwargs)

    def annotation_queue_object_ids(self, *args: Any, **kwargs: Any) -> set[str]:
        return self.owner._annotation_queue_object_ids_impl(*args, **kwargs)

    def create_annotation_queue(self, *args: Any, **kwargs: Any) -> dict[str, Any]:
        return self.owner._create_annotation_queue_impl(*args, **kwargs)

    def list_annotation_queues(self) -> list[dict[str, Any]]:
        return self.owner._list_annotation_queues_impl()

    def get_annotation_queue(self, queue_id: str) -> dict[str, Any]:
        return self.owner._get_annotation_queue_impl(queue_id)
