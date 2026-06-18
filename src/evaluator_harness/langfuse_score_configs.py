from __future__ import annotations

from typing import Any

from evaluator_harness.config import ProjectConfig, ScoreConfigRef
from evaluator_harness.errors import ConfigError, LangfuseError
from evaluator_harness.langfuse_mappers import (
    object_to_score_config_dict,
    score_config_is_compatible,
)
from evaluator_harness.langfuse_records import require_non_empty_string
from evaluator_harness.progress import NullProgressReporter, ProgressReporter

ScoreConfigSyncResultFactory = Any


def sync_score_configs_workflow(
    owner: Any,
    config: ProjectConfig,
    *,
    result_factory: ScoreConfigSyncResultFactory,
    progress: ProgressReporter | None = None,
    dry_run: bool = False,
) -> list[Any]:
    if not dry_run:
        owner.check_reachable(operation="sync-score-configs")
    results: list[Any] = []
    reporter = progress or NullProgressReporter()
    description = "Checking score configs" if dry_run else "Syncing score configs"
    with reporter.task(description, total=len(config.evaluators)) as task:
        for evaluator in config.evaluators:
            results.append(
                sync_one_score_config(
                    owner,
                    config,
                    evaluator,
                    result_factory=result_factory,
                    dry_run=dry_run,
                )
            )
            task.advance()
    owner.calls.append(
        ("sync_score_configs", {"count": len(results), "dry_run": dry_run})
    )
    return results


def sync_one_score_config(
    owner: Any,
    config: ProjectConfig,
    evaluator: Any,
    *,
    result_factory: ScoreConfigSyncResultFactory,
    dry_run: bool = False,
) -> Any:
    score = evaluator.score
    if not score.managed_by_harness:
        score_config_id = score.langfuse_score_config_id
        if not score_config_id:
            raise ConfigError(
                f"Evaluator {evaluator.name} requires langfuse_score_config_id"
            )
        return result_factory(
            evaluator_name=evaluator.name,
            name=score_config_id,
            score_config_id=score_config_id,
            status="user_owned",
            ownership="user_owned",
        )

    managed_name = f"{config.project.score_config_prefix}{score.name}"
    payload = score_payload(managed_name, score)
    if len(managed_name) > 35:
        raise ConfigError(
            f"Score config {managed_name} exceeds Langfuse name limit of 35 characters"
        )
    owner._gateway.load_live_score_configs_by_name(managed_name, payload)
    existing = owner.score_configs.get(managed_name)
    if existing is None:
        return _create_missing_score_config(
            owner,
            evaluator_name=evaluator.name,
            managed_name=managed_name,
            payload=payload,
            result_factory=result_factory,
            dry_run=dry_run,
        )
    assert_score_config_compatible(managed_name, existing, payload)
    return result_factory(
        evaluator_name=evaluator.name,
        name=managed_name,
        score_config_id=str(existing["id"]),
        status="reused",
        ownership="managed_by_harness",
    )


def load_live_score_configs_by_name(
    owner: Any,
    name: str,
    expected: dict[str, Any],
) -> None:
    if owner.client is None:
        return
    api = getattr(owner.client, "api", None)
    score_configs = getattr(api, "score_configs", None)
    get = getattr(score_configs, "get", None)
    if not callable(get):
        return
    try:
        page = owner._with_langfuse_retries(
            operation="list score configs",
            callback=lambda: get(limit=100),
        )
    except Exception as exc:
        raise LangfuseError(f"Unable to list score configs: {exc}") from exc

    page_configs = [
        object_to_score_config_dict(config) for config in getattr(page, "data", [])
    ]
    _store_best_score_config_match(
        owner,
        name=name,
        expected=expected,
        matches=[config for config in page_configs if config.get("name") == name],
    )


def create_live_score_config(owner: Any, payload: dict[str, Any]) -> str:
    api = getattr(owner.client, "api", None)
    score_configs = getattr(api, "score_configs", None)
    create = getattr(score_configs, "create", None)
    if not callable(create):
        raise LangfuseError(
            "Installed Langfuse SDK does not expose score config creation"
        )
    try:
        created = owner._with_langfuse_retries(
            operation=f"create score config {payload['name']}",
            callback=lambda: create(**_score_config_create_kwargs(payload)),
        )
    except Exception as exc:
        raise LangfuseError(
            f"Unable to create Langfuse score config {payload['name']}: {exc}"
        ) from exc
    try:
        return require_non_empty_string(
            getattr(created, "id", None) or getattr(created, "score_config_id", None),
            field_name="score config id",
        )
    except ValueError:
        raise LangfuseError(
            f"Unable to create Langfuse score config {payload['name']}: "
            "missing id in response"
        )


def align_score_config_to_existing_id(
    owner: Any,
    *,
    target_score_config_id: str,
    managed_name: str,
) -> None:
    if owner.client is None:
        return
    api = getattr(owner.client, "api", None)
    score_configs = getattr(api, "score_configs", None)
    get_by_id = getattr(score_configs, "get_by_id", None)
    get = getattr(score_configs, "get", None)
    update = getattr(score_configs, "update", None)
    if not callable(get_by_id) or not callable(get) or not callable(update):
        return
    try:
        target = object_to_score_config_dict(get_by_id(target_score_config_id))
        if target.get("name") == managed_name and not target.get("archived"):
            owner.score_configs[managed_name] = target
            return
        _archive_active_managed_score_configs(owner, get, update, managed_name)
        update(target_score_config_id, name=managed_name, is_archived=False)
        updated = object_to_score_config_dict(get_by_id(target_score_config_id))
    except Exception as exc:
        raise LangfuseError(
            f"Unable to align Langfuse score config {target_score_config_id} "
            f"to managed name {managed_name}: {exc}"
        ) from exc
    owner.score_configs[managed_name] = updated


def score_payload(managed_name: str, score: ScoreConfigRef) -> dict[str, Any]:
    return {
        "name": managed_name,
        "data_type": score.data_type.value,
        "min_value": score.min_value,
        "max_value": score.max_value,
        "categories": score.categories or None,
        "description": score.description,
    }


def assert_score_config_compatible(
    managed_name: str,
    existing: dict[str, Any],
    expected: dict[str, Any],
) -> None:
    if existing.get("archived"):
        raise ConfigError(
            f"Score config {managed_name} is archived and still conflicts"
        )
    if not score_config_is_compatible(existing, expected):
        raise ConfigError(
            f"Managed score config {managed_name} exists with incompatible schema. "
            "Change the score name/prefix or update the Langfuse config manually."
        )


def archived_score_config_name(old_name: str, config_id: str) -> str:
    suffix = f"_arch_{config_id[:8]}"
    return f"{old_name[: 35 - len(suffix)]}{suffix}"


def _create_missing_score_config(
    owner: Any,
    *,
    evaluator_name: str,
    managed_name: str,
    payload: dict[str, Any],
    result_factory: ScoreConfigSyncResultFactory,
    dry_run: bool,
) -> Any:
    if dry_run:
        return result_factory(
            evaluator_name=evaluator_name,
            name=managed_name,
            score_config_id="",
            status="planned_create",
            ownership="managed_by_harness",
        )
    score_config_id = f"score-config-{len(owner.score_configs) + 1}"
    if owner.client is not None:
        score_config_id = owner._gateway.create_live_score_config(payload)
    owner.score_configs[managed_name] = {
        "id": score_config_id,
        **payload,
        "archived": False,
    }
    return result_factory(
        evaluator_name=evaluator_name,
        name=managed_name,
        score_config_id=score_config_id,
        status="created",
        ownership="managed_by_harness",
    )


def _store_best_score_config_match(
    owner: Any,
    *,
    name: str,
    expected: dict[str, Any],
    matches: list[dict[str, Any]],
) -> None:
    active_matches = [config for config in matches if not config.get("archived")]
    compatible_active = [
        config
        for config in active_matches
        if score_config_is_compatible(config, expected)
    ]
    if compatible_active:
        owner.score_configs[name] = compatible_active[0]
        return
    if not active_matches:
        archived_matches = [config for config in matches if config.get("archived")]
        if archived_matches:
            owner.score_configs[name] = archived_matches[0]
        return
    owner.score_configs[name] = active_matches[0]


def _score_config_create_kwargs(payload: dict[str, Any]) -> dict[str, Any]:
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
    return {
        "name": payload["name"],
        "data_type": ScoreConfigDataType(payload["data_type"]),
        "categories": categories,
        "min_value": payload.get("min_value"),
        "max_value": payload.get("max_value"),
        "description": payload.get("description"),
    }


def _archive_active_managed_score_configs(
    owner: Any,
    get: Any,
    update: Any,
    managed_name: str,
) -> None:
    page = get(limit=100)
    for config in getattr(page, "data", []):
        candidate = object_to_score_config_dict(config)
        if candidate.get("name") != managed_name or candidate.get("archived"):
            continue
        candidate_id = require_non_empty_string(
            candidate.get("id"),
            field_name="score config id",
        )
        update(
            candidate_id,
            name=archived_score_config_name(managed_name, candidate_id),
            is_archived=True,
        )
