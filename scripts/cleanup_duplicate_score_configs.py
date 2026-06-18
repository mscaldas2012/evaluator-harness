from __future__ import annotations

import argparse
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from evaluator_harness.config import LiveSettings, load_project_config
from evaluator_harness.langfuse_gateways import (
    LangfuseGateway,
    build_langfuse_gateway_from_env,
)


@dataclass(frozen=True)
class ScoreConfigCleanupPlan:
    name: str
    keep_id: str
    archive_ids: list[str]


@dataclass(frozen=True)
class ScoreConfigRenamePlan:
    config_id: str
    old_name: str
    new_name: str


def build_cleanup_plan(
    score_configs: list[dict[str, Any]],
    *,
    prefix: str,
    name: str | None = None,
) -> list[ScoreConfigCleanupPlan]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for config in score_configs:
        config_name = str(config.get("name") or "")
        if name and config_name != name:
            continue
        if not name and not config_name.startswith(prefix):
            continue
        if config.get("archived"):
            continue
        grouped[config_name].append(config)

    plans: list[ScoreConfigCleanupPlan] = []
    for config_name, configs in grouped.items():
        if len(configs) < 2:
            continue
        sorted_configs = sorted(configs, key=_created_at_sort_key, reverse=True)
        keep = sorted_configs[0]
        archive = sorted_configs[1:]
        plans.append(
            ScoreConfigCleanupPlan(
                name=config_name,
                keep_id=str(keep["id"]),
                archive_ids=[str(config["id"]) for config in archive],
            )
        )
    return plans


def build_rename_archived_plan(
    score_configs: list[dict[str, Any]],
    *,
    prefix: str,
    name: str | None = None,
) -> list[ScoreConfigRenamePlan]:
    plans: list[ScoreConfigRenamePlan] = []
    for config in score_configs:
        old_name = str(config.get("name") or "")
        if name and old_name != name:
            continue
        if not name and not old_name.startswith(prefix):
            continue
        if not config.get("archived"):
            continue
        config_id = str(config["id"])
        if "_archived_" in old_name:
            continue
        plans.append(
            ScoreConfigRenamePlan(
                config_id=config_id,
                old_name=old_name,
                new_name=_archived_score_config_name(old_name, config_id),
            )
        )
    return plans


def fetch_score_configs(client: LangfuseGateway) -> list[dict[str, Any]]:
    api = getattr(client.client, "api", None)
    score_configs_api = getattr(api, "score_configs", None)
    get = getattr(score_configs_api, "get", None)
    if not callable(get):
        raise RuntimeError("Langfuse SDK does not expose score_configs.get")

    configs: list[dict[str, Any]] = []
    page = 1
    while True:
        response = get(page=page, limit=100)
        configs.extend(_normalize_score_config(config) for config in getattr(response, "data", []))
        meta = getattr(response, "meta", None)
        total_pages = int(getattr(meta, "total_pages", page) or page)
        if page >= total_pages:
            return configs
        page += 1


def archive_score_configs(
    client: LangfuseGateway,
    plans: list[ScoreConfigCleanupPlan],
) -> None:
    api = getattr(client.client, "api", None)
    score_configs_api = getattr(api, "score_configs", None)
    update = getattr(score_configs_api, "update", None)
    if not callable(update):
        raise RuntimeError("Langfuse SDK does not expose score_configs.update")
    for plan in plans:
        for config_id in plan.archive_ids:
            update(config_id, is_archived=True)


def rename_score_configs(
    client: LangfuseGateway,
    plans: list[ScoreConfigRenamePlan],
) -> None:
    api = getattr(client.client, "api", None)
    score_configs_api = getattr(api, "score_configs", None)
    update = getattr(score_configs_api, "update", None)
    if not callable(update):
        raise RuntimeError("Langfuse SDK does not expose score_configs.update")
    for plan in plans:
        update(plan.config_id, name=plan.new_name)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Archive duplicate active harness-managed Langfuse score configs."
    )
    parser.add_argument(
        "--project",
        default="configs/projects/rewrite_quality.yaml",
        help="Project YAML used to read the managed score config prefix.",
    )
    parser.add_argument(
        "--prefix",
        default=None,
        help="Override the managed score config prefix. Defaults to project.score_config_prefix.",
    )
    parser.add_argument(
        "--name",
        default=None,
        help="Clean up one exact score config name instead of all configs with the prefix.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Archive duplicates. Without this flag the script only prints the plan.",
    )
    parser.add_argument(
        "--rename-archived",
        action="store_true",
        help="Rename archived managed score configs so they no longer share the active name.",
    )
    args = parser.parse_args()

    LiveSettings.from_env().require_langfuse()
    project = load_project_config(Path(args.project))
    prefix = args.prefix or project.project.score_config_prefix
    client = build_langfuse_gateway_from_env()

    score_configs = fetch_score_configs(client)
    plans = build_cleanup_plan(score_configs, prefix=prefix, name=args.name)
    rename_plans = (
        build_rename_archived_plan(score_configs, prefix=prefix, name=args.name)
        if args.rename_archived
        else []
    )
    if plans:
        print("Duplicate active score configs:")
        for plan in plans:
            print(f"- {plan.name}")
            print(f"  keep:    {plan.keep_id}")
            for config_id in plan.archive_ids:
                print(f"  archive: {config_id}")
    else:
        print("No duplicate active managed score configs found.")

    if rename_plans:
        print("\nArchived score configs to rename:")
        for plan in rename_plans:
            print(f"- {plan.config_id}: {plan.old_name} -> {plan.new_name}")
    elif args.rename_archived:
        print("No archived managed score configs need renaming.")

    if not plans and not rename_plans:
        return 0

    if not args.apply:
        print("\nDry run only. Re-run with --apply to make changes.")
        return 0

    if plans:
        archive_score_configs(client, plans)
        print("\nArchived duplicate score configs.")
    if rename_plans:
        rename_score_configs(client, rename_plans)
        print("Renamed archived score configs.")
    return 0


def _normalize_score_config(value: Any) -> dict[str, Any]:
    raw = value.model_dump(mode="json") if hasattr(value, "model_dump") else dict(value)
    return {
        "id": str(raw["id"]),
        "name": str(raw["name"]),
        "archived": bool(raw.get("archived") or raw.get("is_archived") or raw.get("isArchived")),
        "created_at": raw.get("created_at") or raw.get("createdAt"),
    }


def _created_at_sort_key(config: dict[str, Any]) -> datetime:
    value = str(config.get("created_at") or "")
    if not value:
        return datetime.min
    return datetime.fromisoformat(value.replace("Z", "+00:00")).replace(tzinfo=None)


def _archived_score_config_name(old_name: str, config_id: str) -> str:
    suffix = f"_arch_{config_id[:8]}"
    return f"{old_name[: 35 - len(suffix)]}{suffix}"


if __name__ == "__main__":
    raise SystemExit(main())
