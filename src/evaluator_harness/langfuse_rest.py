from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class LangfuseRestGateway:
    owner: Any
    settings: Any
    http_transport: Any | None = None

    def request(
        self,
        method: str,
        path: str,
        *,
        json_payload: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return self.owner._rest_evaluator_request(
            method,
            path,
            json_payload=json_payload,
        )

    def list_evaluators(self) -> list[dict[str, Any]]:
        return self.owner._list_rest_evaluators()

    def get_evaluator(self, evaluator_id: str) -> dict[str, Any] | None:
        return self.owner._get_rest_evaluator(evaluator_id)

    def create_evaluator(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.owner._create_rest_evaluator(payload)

    def update_evaluator(
        self,
        evaluator_id: str,
        changes: dict[str, Any],
    ) -> dict[str, Any]:
        return self.owner._update_rest_evaluator(evaluator_id, changes)

    def list_annotation_queues(self) -> list[dict[str, Any]] | None:
        return self.owner._list_live_annotation_queues()

    def get_annotation_queue(self, queue_id: str) -> dict[str, Any] | None:
        return self.owner._get_live_annotation_queue(queue_id)

    def create_annotation_queue(self, **kwargs: Any) -> dict[str, Any] | None:
        return self.owner._create_live_annotation_queue(**kwargs)

    def annotation_queue_object_ids(self, queue_id: str) -> set[str]:
        return self.owner._live_annotation_queue_object_ids(queue_id)

    def create_annotation_queue_item(
        self,
        queue_id: str,
        *,
        object_id: str,
    ) -> dict[str, Any] | None:
        return self.owner._create_live_annotation_queue_item(
            queue_id,
            object_id=object_id,
        )
