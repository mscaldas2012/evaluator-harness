from __future__ import annotations

import os
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from evaluator_harness.config import DatasetItem, DatasetKind, DatasetSource
from evaluator_harness.dataset_loader import dataset_compatibility_version
from evaluator_harness.errors import ConfigError
from evaluator_harness.langfuse_records import LangfuseOperationOutcome
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
        _record_dataset_run_item_warning(
            owner,
            dataset_sync=dataset_sync,
            item_id=item_id,
            run_name=run_name,
            trace_id=trace_id,
            message="Langfuse dataset run item recording is unavailable.",
            details={"reason": "dataset_run_items.create is not callable"},
        )
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
    except Exception as exc:
        primary_exc = exc
        fallback_item_id = find_dataset_item_id(
            owner,
            dataset_name=dataset_sync.name,
            item_id=item_id,
        )
        if not fallback_item_id:
            _record_dataset_run_item_warning(
                owner,
                dataset_sync=dataset_sync,
                item_id=item_id,
                run_name=run_name,
                trace_id=trace_id,
                message="Langfuse dataset run item was not recorded.",
                details={
                    "reason": "fallback dataset item lookup returned no id",
                    "exception_type": type(primary_exc).__name__,
                    "error": str(primary_exc),
                },
            )
            return
    try:
        create(dataset_item_id=fallback_item_id, **payload)
    except Exception as exc:
        _record_dataset_run_item_warning(
            owner,
            dataset_sync=dataset_sync,
            item_id=item_id,
            run_name=run_name,
            trace_id=trace_id,
            message="Langfuse dataset run item was not recorded.",
            details={
                "reason": "fallback dataset run item create failed",
                "exception_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        return


def _record_dataset_run_item_warning(
    owner: Any,
    *,
    dataset_sync: Any,
    item_id: str,
    run_name: str,
    trace_id: str,
    message: str,
    details: dict[str, Any],
) -> None:
    record_outcome = getattr(owner, "record_langfuse_outcome", None)
    if not callable(record_outcome):
        return
    record_outcome(
        LangfuseOperationOutcome(
            operation="dataset_run_item_recording",
            status="partial_success",
            severity="warning",
            message=message,
            affected_count=1,
            examples=(f"run={run_name} item={item_id} trace={trace_id}",),
            details={
                "dataset": getattr(dataset_sync, "name", None),
                "run_name": run_name,
                "item_id": item_id,
                "trace_id": trace_id,
                **details,
            },
        )
    )


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
    except Exception as exc:
        _record_lookup_warning(
            owner,
            operation="dataset_item_lookup",
            message="Langfuse dataset item lookup failed.",
            examples=(f"dataset={dataset_name} item={item_id}",),
            details={
                "dataset_name": dataset_name,
                "item_id": item_id,
                "exception_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        return None
    items = getattr(page, "data", None) or getattr(page, "items", None) or []
    for item in items:
        metadata = getattr(item, "metadata", None) or {}
        if str(metadata.get("item_id")) == str(item_id):
            value = getattr(item, "id", None)
            return str(value) if value else None
    return None


def _record_lookup_warning(
    owner: Any,
    *,
    operation: str,
    message: str,
    examples: tuple[str, ...],
    details: dict[str, Any],
) -> None:
    record_outcome = getattr(owner, "record_langfuse_outcome", None)
    if not callable(record_outcome):
        return
    record_outcome(
        LangfuseOperationOutcome(
            operation=operation,
            status="partial_success",
            severity="warning",
            message=message,
            affected_count=1,
            examples=examples,
            details=details,
        )
    )


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
