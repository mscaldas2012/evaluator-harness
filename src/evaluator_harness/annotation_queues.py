from __future__ import annotations

import json
import os
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from evaluator_harness.config import ProjectConfig
from evaluator_harness.errors import ConfigError, LangfuseError


QUEUE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
SLUG_PATTERN = re.compile(r"[^A-Za-z0-9_-]+")
DEFAULT_QUEUE_REFERENCE_DIR = Path(".evaluator-harness") / "queue-references"


QueueOwnership = Literal["managed_by_harness", "user_owned", "environment_override"]


class AnnotationQueueReference(BaseModel):
    schema_version: str = "1"
    project_name: str
    project_version: str
    review_policy_version: str
    queue_id: str
    queue_name: str
    ownership: QueueOwnership
    score_config_ids: list[str] = Field(default_factory=list)
    status: Literal["created", "reused", "resolved", "skipped", "user_owned", "environment_override"]
    created_at: str | None = None
    synced_at: str


class AnnotationQueueSyncResult(BaseModel):
    queue_id: str | None = None
    queue_name: str | None = None
    ownership: QueueOwnership | Literal["skipped"] = "managed_by_harness"
    status: Literal[
        "created",
        "reused",
        "resolved",
        "planned",
        "skipped",
        "user_owned",
        "environment_override",
        "conflict",
        "failed",
    ]
    score_config_ids: list[str] = Field(default_factory=list)
    reference_path: str | None = None
    message: str
    manual_fallback_reason: str | None = None


class AnnotationQueueReferenceStore:
    def __init__(self, base_dir: Path | str = DEFAULT_QUEUE_REFERENCE_DIR) -> None:
        self.base_dir = Path(base_dir)

    def path_for(
        self,
        project_name: str,
        project_version: str,
        review_policy_version: str,
    ) -> Path:
        return queue_reference_path(
            project_name,
            project_version,
            review_policy_version,
            base_dir=self.base_dir,
        )

    def save(self, reference: AnnotationQueueReference) -> Path:
        path = self.path_for(
            reference.project_name,
            reference.project_version,
            reference.review_policy_version,
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(reference.model_dump(mode="json"), indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return path

    def load(
        self,
        project_name: str,
        project_version: str,
        review_policy_version: str,
    ) -> AnnotationQueueReference | None:
        path = self.path_for(project_name, project_version, review_policy_version)
        if not path.exists():
            return None
        return AnnotationQueueReference.model_validate_json(path.read_text(encoding="utf-8"))


def queue_reference_path(
    project_name: str,
    project_version: str,
    review_policy_version: str,
    *,
    base_dir: Path | str = DEFAULT_QUEUE_REFERENCE_DIR,
) -> Path:
    filename = (
        f"{slugify(project_name)}__{slugify(project_version)}__"
        f"{slugify(review_policy_version)}.json"
    )
    return Path(base_dir) / filename


def managed_queue_name(
    project_name: str,
    project_version: str,
    review_policy_version: str,
) -> str:
    return (
        f"EH_{slugify(project_name)}_{slugify(project_version)}_review_"
        f"{slugify(review_policy_version)}"
    )


def slugify(value: str) -> str:
    slug = SLUG_PATTERN.sub("-", value.strip())
    slug = slug.strip("-_")
    return slug or "default"


def validate_queue_name(value: str) -> str:
    if not QUEUE_NAME_PATTERN.fullmatch(value):
        raise ValueError(
            "queue_name must contain only letters, numbers, underscores, and hyphens"
        )
    return value


def now_utc() -> str:
    return datetime.now(UTC).isoformat()


def sync_annotation_queue(
    config: ProjectConfig,
    langfuse_client: object,
    score_config_results: list[object],
    *,
    store: AnnotationQueueReferenceStore | None = None,
    dry_run: bool = False,
) -> AnnotationQueueSyncResult:
    policy = config.human_review
    review_version = queue_review_policy_version(config)
    reference_store = store or AnnotationQueueReferenceStore()

    if not policy.enabled:
        return AnnotationQueueSyncResult(
            ownership="skipped",
            status="skipped",
            message="human review disabled",
        )

    if policy.queue_ownership == "user_owned":
        queue_id = str(policy.annotation_queue_id or "")
        if not queue_id:
            raise ConfigError("user_owned human review requires annotation_queue_id")
        _get_annotation_queue(langfuse_client, queue_id)
        return AnnotationQueueSyncResult(
            queue_id=queue_id,
            queue_name=queue_id,
            ownership="user_owned",
            status="user_owned",
            message="using user-owned annotation queue",
        )

    score_config_ids = [
        str(getattr(result, "score_config_id"))
        for result in score_config_results
        if getattr(result, "score_config_id", None)
    ]
    if not score_config_ids and not dry_run:
        raise ConfigError("score config IDs are required before annotation queue sync")

    queue_name = policy.queue_name or managed_queue_name(
        config.project.name,
        config.project.version,
        review_version,
    )
    existing_reference = reference_store.load(
        config.project.name,
        config.project.version,
        review_version,
    )
    if dry_run:
        return _dry_run_annotation_queue(
            config,
            review_version,
            queue_name,
            langfuse_client,
            score_config_results,
            existing_reference,
        )
    if existing_reference is not None:
        try:
            existing_queue = _get_annotation_queue(langfuse_client, existing_reference.queue_id)
        except (ConfigError, LangfuseError) as exc:
            if isinstance(exc, LangfuseError) and "not found" not in str(exc).lower():
                raise
            # The local reference is disposable state. If the remote queue no
            # longer exists, recreate or reuse by deterministic name below.
            pass
        else:
            queue_score_ids = _queue_score_config_ids(existing_queue) or score_config_ids
            _align_queue_score_configs(
                langfuse_client,
                queue_score_ids=queue_score_ids,
                score_config_results=score_config_results,
            )
            return _save_queue_reference(
                config,
                review_version,
                existing_queue,
                queue_score_ids,
                reference_store,
                status="reused",
                message="reused local annotation queue reference",
            )

    for queue in _list_annotation_queues(langfuse_client):
        if queue.get("name") != queue_name:
            continue
        queue_score_ids = _queue_score_config_ids(queue) or score_config_ids
        _align_queue_score_configs(
            langfuse_client,
            queue_score_ids=queue_score_ids,
            score_config_results=score_config_results,
        )
        return _save_queue_reference(
            config,
            review_version,
            queue,
            queue_score_ids,
            reference_store,
            status="reused",
            message="reused existing Langfuse annotation queue",
        )

    try:
        created = _create_annotation_queue(
            langfuse_client,
            name=queue_name,
            score_config_ids=score_config_ids,
            description=(
                f"Evaluation Harness review queue for {config.project.name}/"
                f"{config.project.version} policy {review_version}"
            ),
        )
    except LangfuseError as exc:
        if "maximum number of annotation queues reached" not in str(exc).lower():
            raise
        queues = _list_annotation_queues(langfuse_client)
        if len(queues) != 1:
            raise
        queue = queues[0]
        queue_score_ids = _queue_score_config_ids(queue) or score_config_ids
        _align_queue_score_configs(
            langfuse_client,
            queue_score_ids=queue_score_ids,
            score_config_results=score_config_results,
        )
        return _save_queue_reference(
            config,
            review_version,
            queue,
            queue_score_ids,
            reference_store,
            status="reused",
            message="reused sole existing Langfuse annotation queue due plan limit",
        )
    return _save_queue_reference(
        config,
        review_version,
        created,
        score_config_ids,
        reference_store,
        status="created",
        message="created managed annotation queue",
    )


def resolve_annotation_queue(
    config: ProjectConfig,
    langfuse_client: object,
    score_config_results: list[object],
    *,
    store: AnnotationQueueReferenceStore | None = None,
) -> AnnotationQueueSyncResult:
    policy = config.human_review
    if not policy.enabled:
        return AnnotationQueueSyncResult(
            ownership="skipped",
            status="skipped",
            message="human review disabled",
        )
    if policy.queue_ownership == "user_owned":
        return sync_annotation_queue(
            config,
            langfuse_client,
            score_config_results,
            store=store,
        )
    if policy.fallback_to_env:
        queue_id = os.getenv("LANGFUSE_ANNOTATION_QUEUE_ID")
        if queue_id:
            _get_annotation_queue(langfuse_client, queue_id)
            return AnnotationQueueSyncResult(
                queue_id=queue_id,
                queue_name=queue_id,
                ownership="environment_override",
                status="environment_override",
                message="using LANGFUSE_ANNOTATION_QUEUE_ID override",
            )
    return sync_annotation_queue(
        config,
        langfuse_client,
        score_config_results,
        store=store,
    )


def queue_review_policy_version(config: ProjectConfig) -> str:
    return config.human_review.review_policy_version or "default"


def _save_queue_reference(
    config: ProjectConfig,
    review_version: str,
    queue: dict[str, object],
    score_config_ids: list[str],
    store: AnnotationQueueReferenceStore,
    *,
    status: Literal["created", "reused"],
    message: str,
) -> AnnotationQueueSyncResult:
    reference = AnnotationQueueReference(
        project_name=config.project.name,
        project_version=config.project.version,
        review_policy_version=review_version,
        queue_id=str(queue["id"]),
        queue_name=str(queue["name"]),
        ownership="managed_by_harness",
        score_config_ids=score_config_ids,
        status=status,
        created_at=str(queue.get("created_at") or queue.get("createdAt") or "") or None,
        synced_at=now_utc(),
    )
    path = store.save(reference)
    return AnnotationQueueSyncResult(
        queue_id=reference.queue_id,
        queue_name=reference.queue_name,
        ownership=reference.ownership,
        status=status,
        score_config_ids=reference.score_config_ids,
        reference_path=str(path),
        message=message,
    )


def _dry_run_annotation_queue(
    config: ProjectConfig,
    review_version: str,
    queue_name: str,
    langfuse_client: object,
    score_config_results: list[object],
    existing_reference: AnnotationQueueReference | None,
) -> AnnotationQueueSyncResult:
    desired_ids = {
        str(getattr(result, "score_config_id"))
        for result in score_config_results
        if getattr(result, "score_config_id", None)
    }
    score_config_names = [
        str(getattr(result, "name"))
        for result in score_config_results
        if getattr(result, "name", None)
    ]
    if not desired_ids:
        return AnnotationQueueSyncResult(
            queue_name=queue_name,
            ownership="managed_by_harness",
            status="planned",
            score_config_ids=[],
            message=(
                "annotation queue would be checked after score configs are applied: "
                + ", ".join(score_config_names)
            ),
        )

    if existing_reference is not None:
        try:
            queue = _get_annotation_queue(langfuse_client, existing_reference.queue_id)
        except (ConfigError, LangfuseError) as exc:
            if isinstance(exc, LangfuseError) and "not found" not in str(exc).lower():
                raise
        else:
            return _dry_run_queue_match_result(
                queue,
                desired_ids,
                score_config_ids=sorted(desired_ids),
                message="local annotation queue reference points to an existing queue",
            )

    for queue in _list_annotation_queues(langfuse_client):
        if queue.get("name") == queue_name:
            return _dry_run_queue_match_result(
                queue,
                desired_ids,
                score_config_ids=sorted(desired_ids),
                message="matching Langfuse annotation queue already exists",
            )

    queues = _list_annotation_queues(langfuse_client)
    if len(queues) == 1:
        queue = queues[0]
        queue_score_ids = set(_queue_score_config_ids(queue))
        if queue_score_ids and queue_score_ids != desired_ids:
            return AnnotationQueueSyncResult(
                queue_id=str(queue.get("id") or ""),
                queue_name=str(queue.get("name") or queue_name),
                ownership="managed_by_harness",
                status="conflict",
                score_config_ids=_queue_score_config_ids(queue),
                message=(
                    "Existing annotation queue has score configs that do not match this project. "
                    "Delete the queue if you want this project's scores attached to it, "
                    "or use a separate Langfuse project."
                ),
            )

    return AnnotationQueueSyncResult(
        queue_name=queue_name,
        ownership="managed_by_harness",
        status="planned",
        score_config_ids=sorted(desired_ids),
        message="annotation queue would be created",
    )


def _dry_run_queue_match_result(
    queue: dict[str, object],
    desired_ids: set[str],
    *,
    score_config_ids: list[str],
    message: str,
) -> AnnotationQueueSyncResult:
    queue_score_ids = set(_queue_score_config_ids(queue))
    if queue_score_ids and queue_score_ids != desired_ids:
        return AnnotationQueueSyncResult(
            queue_id=str(queue.get("id") or ""),
            queue_name=str(queue.get("name") or ""),
            ownership="managed_by_harness",
            status="conflict",
            score_config_ids=_queue_score_config_ids(queue),
            message=(
                "Existing annotation queue has score configs that do not match this project. "
                "Delete the queue if you want this project's scores attached to it, "
                "or use a separate Langfuse project."
            ),
        )
    return AnnotationQueueSyncResult(
        queue_id=str(queue.get("id") or ""),
        queue_name=str(queue.get("name") or ""),
        ownership="managed_by_harness",
        status="reused",
        score_config_ids=score_config_ids,
        message=message,
    )


def _queue_score_config_ids(queue: dict[str, object]) -> list[str]:
    values = queue.get("score_config_ids") or queue.get("scoreConfigIds") or []
    return [str(value) for value in values]


def _align_queue_score_configs(
    langfuse_client: object,
    *,
    queue_score_ids: list[str],
    score_config_results: list[object],
) -> None:
    desired_ids = [
        str(getattr(result, "score_config_id"))
        for result in score_config_results
        if getattr(result, "score_config_id", None)
    ]
    if set(queue_score_ids) == set(desired_ids):
        return
    if len(queue_score_ids) != len(score_config_results):
        return
    align = getattr(langfuse_client, "align_score_config_to_existing_id", None)
    if not callable(align):
        return
    for queue_score_id, result in zip(queue_score_ids, score_config_results, strict=True):
        align(
            target_score_config_id=str(queue_score_id),
            managed_name=str(getattr(result, "name")),
        )


def _create_annotation_queue(
    langfuse_client: object,
    *,
    name: str,
    score_config_ids: list[str],
    description: str,
) -> dict[str, object]:
    create = getattr(langfuse_client, "create_annotation_queue")
    return create(name=name, score_config_ids=score_config_ids, description=description)


def _list_annotation_queues(langfuse_client: object) -> list[dict[str, object]]:
    list_queues = getattr(langfuse_client, "list_annotation_queues")
    return list_queues()


def _get_annotation_queue(langfuse_client: object, queue_id: str) -> dict[str, object]:
    get_queue = getattr(langfuse_client, "get_annotation_queue")
    return get_queue(queue_id)
