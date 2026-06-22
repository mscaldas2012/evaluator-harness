from __future__ import annotations

import time
from typing import Any

from evaluator_harness.errors import ConfigError
from evaluator_harness.langfuse_records import LangfuseOperationOutcome
from evaluator_harness.langfuse_settings import (
    langfuse_trace_poll_interval_seconds,
    langfuse_trace_wait_seconds,
)


def output_for_workflow(owner: Any, *, run_id: str, item_id: str) -> str | None:
    for trace in owner.traces:
        if _trace_matches_run_item(trace, run_id=run_id, item_id=item_id):
            output = trace.get("output")
            return str(output) if output is not None else None
    return None


def trace_by_id_workflow(owner: Any, trace_id: str) -> dict[str, Any]:
    for trace in owner.traces:
        if trace.get("trace_id") == trace_id:
            return trace
    raise ConfigError(f"Trace not found: {trace_id}")


def traces_for_run_workflow(
    owner: Any,
    run_id: str,
    *,
    dataset_names: list[str] | None = None,
    expected_count: int | None = None,
    wait_timeout_seconds: float | None = None,
    poll_interval_seconds: float | None = None,
) -> list[dict[str, Any]]:
    traces = [trace for trace in owner.traces if trace.get("run_id") == run_id]
    if owner.client is None:
        return traces
    if traces and has_expected_trace_count(traces, expected_count):
        return traces

    deadline = time.monotonic() + (
        wait_timeout_seconds
        if wait_timeout_seconds is not None
        else langfuse_trace_wait_seconds()
    )
    poll_interval = (
        poll_interval_seconds
        if poll_interval_seconds is not None
        else langfuse_trace_poll_interval_seconds()
    )
    best_traces = traces
    while True:
        live_traces = owner._live_traces_for_run(run_id, dataset_names=dataset_names)
        if live_traces:
            owner.traces = merge_traces(owner.traces, live_traces)
            best_traces = [
                trace for trace in owner.traces if trace.get("run_id") == run_id
            ]
        if has_expected_trace_count(best_traces, expected_count):
            return best_traces
        if expected_count is None or time.monotonic() >= deadline:
            return best_traces
        owner.retry_sleep(poll_interval)


def live_traces_for_run(
    owner: Any,
    run_id: str,
    *,
    dataset_names: list[str] | None = None,
) -> list[dict[str, Any]]:
    trace_client = getattr(getattr(owner.client, "api", None), "trace", None)
    list_traces = getattr(trace_client, "list", None)
    if not callable(list_traces):
        return live_dataset_run_traces_for_run(
            owner,
            run_id,
            dataset_names=dataset_names,
        )
    direct_traces = _direct_traces_for_run(owner, list_traces, run_id)
    dataset_run_traces = live_dataset_run_traces_for_run(
        owner,
        run_id,
        dataset_names=dataset_names,
    )
    if dataset_run_traces:
        return merge_traces(direct_traces, dataset_run_traces)
    return direct_traces


def live_dataset_run_traces_for_run(
    owner: Any,
    run_id: str,
    *,
    dataset_names: list[str] | None = None,
) -> list[dict[str, Any]]:
    get_dataset_runs = getattr(owner.client, "get_dataset_runs", None)
    if not callable(get_dataset_runs):
        return []
    traces: list[dict[str, Any]] = []
    for dataset_name in dataset_names or candidate_dataset_names(owner):
        try:
            page = get_dataset_runs(dataset_name=dataset_name, limit=100)
        except Exception as exc:
            _record_lookup_warning(
                owner,
                operation="trace_lookup",
                message="Langfuse dataset run trace lookup failed.",
                examples=(f"run={run_id} dataset={dataset_name}",),
                details={
                    "dataset_name": dataset_name,
                    "run_id": run_id,
                    "exception_type": type(exc).__name__,
                    "error": str(exc),
                },
            )
            continue
        for run in getattr(page, "data", None) or getattr(page, "runs", None) or []:
            traces.extend(
                _traces_from_dataset_run(owner, run, str(dataset_name), run_id)
            )
    return traces


def candidate_dataset_names(owner: Any) -> list[str]:
    names = {
        str(trace.get("metadata", {}).get("dataset_name"))
        for trace in owner.traces
        if trace.get("metadata", {}).get("dataset_name")
    }
    return sorted(names or {"rewrite-quality/v1"})


def live_dataset_run_item_traces(
    owner: Any,
    *,
    dataset_name: str,
    run_id: str,
) -> list[dict[str, Any]]:
    get_dataset_run = getattr(owner.client, "get_dataset_run", None)
    if not callable(get_dataset_run):
        return []
    try:
        run_with_items = get_dataset_run(dataset_name=dataset_name, run_name=run_id)
    except Exception as exc:
        _record_lookup_warning(
            owner,
            operation="trace_lookup",
            message="Langfuse dataset run item trace lookup failed.",
            examples=(f"run={run_id} dataset={dataset_name}",),
            details={
                "dataset_name": dataset_name,
                "run_id": run_id,
                "exception_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        return []
    traces: list[dict[str, Any]] = []
    for item in dataset_run_items(run_with_items):
        trace_id = getattr(item, "trace_id", None)
        fetched_trace = live_trace_by_id(owner, str(trace_id)) if trace_id else None
        if fetched_trace is not None:
            traces.append(fetched_trace)
            continue
        trace = trace_from_metadata(
            dict(getattr(item, "metadata", None) or {}),
            run_id=run_id,
        )
        if trace is not None:
            traces.append(trace)
    return traces


def live_trace_by_id(owner: Any, trace_id: str) -> dict[str, Any] | None:
    trace_client = getattr(getattr(owner.client, "api", None), "trace", None)
    get_trace = getattr(trace_client, "get", None)
    if not callable(get_trace):
        return None
    try:
        trace = get_trace(trace_id)
    except Exception as exc:
        _record_lookup_warning(
            owner,
            operation="trace_lookup",
            message="Langfuse trace lookup failed.",
            examples=(trace_id,),
            details={
                "trace_id": trace_id,
                "exception_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        return None
    if trace is None:
        return None
    return live_trace_to_dict(trace)


def _direct_traces_for_run(
    owner: Any,
    get_traces: Any,
    run_id: str,
) -> list[dict[str, Any]]:
    filters = [
        f'metadata.run_id = "{run_id}"',
        f"metadata.run_id = {run_id}",
    ]
    for filter_expression in filters:
        try:
            page = get_traces(limit=100, filter=filter_expression)
        except Exception as exc:
            _record_lookup_warning(
                owner,
                operation="trace_lookup",
                message="Langfuse direct trace lookup failed.",
                examples=(run_id,),
                details={
                    "run_id": run_id,
                    "filter": filter_expression,
                    "exception_type": type(exc).__name__,
                    "error": str(exc),
                },
            )
            continue
        direct_traces = [
            live_trace_to_dict(trace) for trace in (getattr(page, "data", None) or [])
        ]
        direct_traces = [
            trace for trace in direct_traces if trace.get("run_id") == run_id
        ]
        if direct_traces:
            return direct_traces
    return []


def _traces_from_dataset_run(
    owner: Any,
    run: Any,
    dataset_name: str,
    run_id: str,
) -> list[dict[str, Any]]:
    run_name = getattr(run, "name", None) or getattr(run, "run_name", None)
    if str(run_name) != run_id:
        return []
    item_traces = live_dataset_run_item_traces(
        owner,
        dataset_name=dataset_name,
        run_id=run_id,
    )
    if item_traces:
        return item_traces
    trace = trace_from_metadata(
        dict(getattr(run, "metadata", None) or {}),
        run_id=run_id,
    )
    return [trace] if trace is not None else []


def has_expected_trace_count(
    traces: list[dict[str, Any]],
    expected_count: int | None,
) -> bool:
    return expected_count is None or len(traces) >= expected_count


def _trace_matches_run_item(
    trace: dict[str, Any],
    *,
    run_id: str,
    item_id: str,
) -> bool:
    return (
        trace.get("run_id") == run_id
        and trace.get("metadata", {}).get("dataset_item_id") == item_id
    )


def live_trace_to_dict(trace: Any) -> dict[str, Any]:
    metadata = getattr(trace, "metadata", None) or {}
    trace_id = str(getattr(trace, "id", None) or metadata.get("trace_id"))
    return {
        "trace_id": trace_id,
        "run_id": str(metadata.get("run_id") or ""),
        "name": getattr(trace, "name", None),
        "input": getattr(trace, "input", None),
        "output": getattr(trace, "output", None),
        "error": metadata.get("error"),
        "metadata": dict(metadata),
        "timestamp": str(getattr(trace, "timestamp", None) or ""),
    }


def dataset_run_items(run_with_items: Any) -> list[Any]:
    return list(
        getattr(run_with_items, "dataset_run_items", None)
        or getattr(run_with_items, "items", None)
        or getattr(run_with_items, "data", None)
        or []
    )


def merge_traces(
    primary: list[dict[str, Any]],
    fallback: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    for trace in fallback:
        trace_id = trace.get("trace_id")
        if trace_id:
            merged[str(trace_id)] = trace
    for trace in primary:
        trace_id = trace.get("trace_id")
        if trace_id:
            merged[str(trace_id)] = trace
    return list(merged.values())


def trace_from_metadata(
    metadata: dict[str, Any],
    *,
    run_id: str,
) -> dict[str, Any] | None:
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
