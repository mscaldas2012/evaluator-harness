from __future__ import annotations

import os
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from evaluator_harness.config import DatasetItem, DatasetKind, DatasetSource
from evaluator_harness.dataset_loader import dataset_compatibility_version
from evaluator_harness.errors import ConfigError
from evaluator_harness.progress import NullProgressReporter, ProgressReporter

DatasetSyncResultFactory = Callable[..., Any]


def sync_dataset_workflow(
    owner: Any,
    source: DatasetSource,
    items: list[DatasetItem],
    *,
    result_factory: DatasetSyncResultFactory,
    progress: ProgressReporter | None = None,
    dry_run: bool = False,
) -> Any:
    if not dry_run:
        owner.check_reachable(operation="sync-dataset")
    name = source.langfuse_dataset_name or source.langfuse_dataset_id
    if not name:
        raise ConfigError("Dataset sync requires a Langfuse dataset name or ID")
    compatibility_version = (
        source.langfuse_dataset_version or dataset_compatibility_version(items)
    )
    owner.calls.append(
        (
            "sync_dataset",
            {"name": name, "item_count": len(items), "dry_run": dry_run},
        )
    )
    if dry_run:
        return result_factory(
            name=name,
            version=source.langfuse_dataset_version or "latest",
            compatibility_version=compatibility_version,
            item_count=len(items),
            status="planned",
        )
    status = _sync_or_resolve_dataset(
        owner,
        source=source,
        name=name,
        items=items,
        compatibility_version=compatibility_version,
        progress=progress,
    )
    return result_factory(
        name=name,
        version=source.langfuse_dataset_version or "latest",
        compatibility_version=compatibility_version,
        item_count=len(items),
        status=status,
    )


def record_dataset_run_item_workflow(
    owner: Any,
    *,
    dataset_sync: Any,
    item_id: str,
    run_name: str,
    trace_id: str,
    observation_id: str | None,
    metadata: dict[str, Any],
) -> None:
    if owner.client is None:
        return
    api = getattr(owner.client, "api", None)
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
        create(dataset_item_id=f"{dataset_sync.name}:{item_id}", **payload)
        return
    except Exception:
        fallback_item_id = find_dataset_item_id(
            owner,
            dataset_name=dataset_sync.name,
            item_id=item_id,
        )
        if not fallback_item_id:
            return
    try:
        create(dataset_item_id=fallback_item_id, **payload)
    except Exception:
        return


def find_dataset_item_id(
    owner: Any,
    *,
    dataset_name: str,
    item_id: str,
) -> str | None:
    if owner.client is None:
        return None
    api = getattr(owner.client, "api", None)
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


def dataset_item_sync_payload(
    *,
    name: str,
    item: DatasetItem,
    compatibility_version: str,
) -> dict[str, dict[str, Any]]:
    expected_output = item.ground_truth or item.reference_output
    metadata = {
        **item.metadata,
        "item_id": item.item_id,
        "input_hash": item.input_hash,
    }
    return {
        "live": {
            "dataset_name": name,
            "id": f"{name}:{item.item_id}",
            "input": {"input": item.input},
            "expected_output": expected_output,
            "metadata": {
                **metadata,
                "compatibility_version": compatibility_version,
            },
        },
        "local": {
            "id": item.item_id,
            "langfuse_item_id": f"{name}:{item.item_id}",
            "input": item.input,
            "expected_output": expected_output,
            "metadata": metadata,
        },
    }


def dataset_sync_workers() -> int:
    raw_value = os.environ.get("EVALUATOR_HARNESS_DATASET_SYNC_WORKERS")
    if raw_value is None:
        return 4
    try:
        return max(1, int(raw_value))
    except ValueError:
        return 4


def _sync_or_resolve_dataset(
    owner: Any,
    *,
    source: DatasetSource,
    name: str,
    items: list[DatasetItem],
    compatibility_version: str,
    progress: ProgressReporter | None,
) -> str:
    if source.kind == DatasetKind.LANGFUSE:
        owner.datasets.setdefault(name, [])
        return "resolved"
    create_dataset_item = _prepare_live_dataset(
        owner,
        source,
        name,
        compatibility_version,
    )
    item_payloads = [
        dataset_item_sync_payload(
            name=name,
            item=item,
            compatibility_version=compatibility_version,
        )
        for item in items
    ]
    _sync_dataset_items(
        owner,
        item_payloads=item_payloads,
        create_dataset_item=create_dataset_item,
        progress=progress,
    )
    owner.datasets[name] = [payload["local"] for payload in item_payloads]
    return "synced"


def _prepare_live_dataset(
    owner: Any,
    source: DatasetSource,
    name: str,
    compatibility_version: str,
) -> Any | None:
    if owner.client is None:
        return None
    create_dataset = getattr(owner.client, "create_dataset", None)
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
            pass
    return getattr(owner.client, "create_dataset_item", None)


def _sync_dataset_items(
    owner: Any,
    *,
    item_payloads: list[dict[str, dict[str, Any]]],
    create_dataset_item: Any,
    progress: ProgressReporter | None,
) -> None:
    reporter = progress or NullProgressReporter()
    with reporter.task("Syncing dataset items", total=len(item_payloads)) as task:
        if not callable(create_dataset_item):
            for _payload in item_payloads:
                task.advance()
            return
        workers = dataset_sync_workers()
        if workers > 1 and len(item_payloads) > 1:
            _sync_dataset_items_concurrently(
                owner,
                item_payloads=item_payloads,
                create_dataset_item=create_dataset_item,
                workers=workers,
                task=task,
            )
            return
        for payload in item_payloads:
            _create_dataset_item_with_retries(owner, create_dataset_item, payload)
            task.advance()


def _sync_dataset_items_concurrently(
    owner: Any,
    *,
    item_payloads: list[dict[str, dict[str, Any]]],
    create_dataset_item: Any,
    workers: int,
    task: Any,
) -> None:
    with ThreadPoolExecutor(max_workers=min(workers, len(item_payloads))) as executor:
        futures = [
            executor.submit(
                _create_dataset_item_with_retries,
                owner,
                create_dataset_item,
                payload,
            )
            for payload in item_payloads
        ]
        for future in as_completed(futures):
            future.result()
            task.advance()


def _create_dataset_item_with_retries(
    owner: Any,
    create_dataset_item: Any,
    payload: dict[str, dict[str, Any]],
) -> None:
    owner._with_langfuse_retries(
        operation=f"sync dataset item {payload['local']['id']}",
        callback=lambda payload=payload: create_dataset_item(**payload["live"]),
    )
