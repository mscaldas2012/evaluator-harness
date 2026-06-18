from __future__ import annotations

import os
import time
from datetime import UTC, datetime
from typing import Any

from evaluator_harness.config import BaselineReference
from evaluator_harness.errors import ConfigError, LangfuseError
from evaluator_harness.langfuse_mappers import (
    object_to_prompt_dict,
    object_to_score_dict,
)
from evaluator_harness.progress import NullProgressReporter, ProgressReporter

FINGERPRINT_FIELDS = [
    "project_name",
    "project_version",
    "dataset_name",
    "dataset_version",
    "prompt_version",
    "evaluator_set_id",
    "baseline_model",
    "baseline_parameters_hash",
]


def lookup_baseline_workflow(owner: Any, *args: Any, **kwargs: Any) -> Any:
    owner.calls.append(("lookup_baseline", {"args": args, "kwargs": kwargs}))
    selector = str(kwargs.get("selector") or (args[0] if args else "latest-compatible"))
    fingerprint = kwargs.get("fingerprint") or (args[1] if len(args) > 1 else None)
    live_reference = owner._gateway.lookup_live_baseline(
        selector=selector,
        fingerprint=fingerprint,
    )
    if live_reference is not None:
        return live_reference
    if selector != "latest-compatible":
        reference = owner.baseline_references.get(selector)
        if reference is not None and reference_matches(reference, fingerprint):
            return reference
        return None
    for reference in reversed(list(owner.baseline_references.values())):
        if reference_matches(reference, fingerprint):
            return reference
    return None


def lookup_live_baseline_workflow(
    owner: Any,
    *,
    selector: str,
    fingerprint: Any,
) -> Any | None:
    if owner.client is None or fingerprint is None:
        return None
    get_dataset_runs = getattr(owner.client, "get_dataset_runs", None)
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
    matches = _matching_baseline_runs(owner, runs, selector, fingerprint, dataset_name)
    if not matches:
        return None
    run, metadata, _index = max(
        matches,
        key=lambda match: baseline_reference_sort_key(*match),
    )
    return BaselineReference(
        baseline_run_id=str(
            metadata.get("baseline_run_id")
            or getattr(run, "name", None)
            or getattr(run, "run_name", None)
        ),
        langfuse_run_name=str(
            getattr(run, "name", None) or getattr(run, "run_name", None)
        ),
        created_at=str(metadata.get("created_at") or ""),
        **{
            field: metadata_fingerprint_value(metadata, field)
            for field in FINGERPRINT_FIELDS
        },
    )


def dataset_run_metadata_workflow(
    owner: Any,
    *,
    dataset_name: str,
    fingerprint: Any,
    run: Any,
) -> dict[str, Any]:
    metadata = getattr(run, "metadata", None) or {}
    if metadata and metadata_matches(dict(metadata), fingerprint):
        return dict(metadata)
    get_dataset_run = getattr(owner.client, "get_dataset_run", None)
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
    for item in getattr(run_with_items, "items", None) or []:
        item_metadata = getattr(item, "metadata", None) or {}
        if item_metadata and metadata_matches(dict(item_metadata), fingerprint):
            return dict(item_metadata)
    return dict(metadata)


def fetch_scores_workflow(
    owner: Any,
    run_id: str,
    *,
    trace_ids: list[str] | None = None,
    progress: ProgressReporter | None = None,
) -> list[dict[str, Any]]:
    owner.check_reachable(operation="fetch-scores")
    owner.calls.append(("fetch_scores", {"run_id": run_id, "trace_ids": trace_ids}))
    if owner.client is not None:
        return live_scores_for_traces(owner, trace_ids or [], progress=progress)
    scores = owner.scores.get(run_id, [])
    if not trace_ids:
        return scores
    trace_id_set = {str(trace_id) for trace_id in trace_ids}
    return [score for score in scores if str(score.get("trace_id")) in trace_id_set]


def list_prompt_versions_workflow(
    owner: Any,
    name: str | None = None,
) -> list[dict[str, Any]]:
    owner.check_reachable(operation="list-prompts")
    owner.calls.append(("list_prompt_versions", {"name": name}))
    if owner.client is not None:
        return live_list_prompt_versions(owner, name=name)
    if name is not None:
        return list(owner.prompt_versions.get(name, []))
    return [
        prompt for versions in owner.prompt_versions.values() for prompt in versions
    ]


def create_prompt_version_workflow(
    owner: Any,
    payload: dict[str, Any],
) -> dict[str, Any]:
    owner.check_reachable(operation="create-prompt")
    owner.calls.append(("create_prompt_version", payload))
    if owner.client is not None:
        return live_create_prompt_version(owner, payload)
    versions = owner.prompt_versions.setdefault(str(payload["name"]), [])
    created = {"version": len(versions) + 1, **payload}
    versions.append(created)
    return created


def output_for_workflow(owner: Any, *, run_id: str, item_id: str) -> str | None:
    for trace in owner.traces:
        if _trace_matches_run_item(trace, run_id=run_id, item_id=item_id):
            output = trace.get("output")
            return str(output) if output is not None else None
    return None


def find_prompt_version_workflow(
    owner: Any,
    name: str,
    *,
    label: str,
) -> dict[str, Any] | None:
    for prompt in owner.list_prompt_versions(name):
        if prompt_has_label(prompt, label):
            return prompt
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
    direct_traces = _direct_traces_for_run(list_traces, run_id)
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
        except Exception:
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
    except Exception:
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
        return live_trace_to_dict(get_trace(trace_id))
    except Exception:
        return None


def live_list_prompt_versions(
    owner: Any,
    *,
    name: str | None = None,
) -> list[dict[str, Any]]:
    prompts_client = getattr(getattr(owner.client, "api", None), "prompts", None)
    list_prompts = getattr(prompts_client, "list", None)
    get_prompt = getattr(prompts_client, "get", None)
    if not callable(list_prompts):
        return []
    versions: list[dict[str, Any]] = []
    page_number = 1
    while True:
        try:
            page = list_prompts(name=name, page=page_number, limit=100)
        except Exception as exc:
            raise LangfuseError(f"Unable to list Langfuse prompts: {exc}") from exc
        versions.extend(_prompt_versions_from_page(page, name, get_prompt))
        meta = getattr(page, "meta", None)
        total_pages = int(getattr(meta, "total_pages", page_number) or page_number)
        if page_number >= total_pages:
            break
        page_number += 1
    return versions


def _direct_traces_for_run(get_traces: Any, run_id: str) -> list[dict[str, Any]]:
    filters = [
        f'metadata.run_id = "{run_id}"',
        f"metadata.run_id = {run_id}",
    ]
    for filter_expression in filters:
        try:
            page = get_traces(limit=100, filter=filter_expression)
        except Exception:
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


def live_create_prompt_version(owner: Any, payload: dict[str, Any]) -> dict[str, Any]:
    prompts_client = getattr(getattr(owner.client, "api", None), "prompts", None)
    create = getattr(prompts_client, "create", None)
    if not callable(create):
        raise LangfuseError("Installed Langfuse SDK does not expose prompt creation")
    try:
        request = _prompt_create_request(payload)
        return object_to_prompt_dict(create(request=request))
    except Exception as exc:
        raise LangfuseError(
            f"Unable to create Langfuse prompt {payload.get('name')}: {exc}"
        ) from exc


def live_scores_for_traces(
    owner: Any,
    trace_ids: list[str],
    *,
    progress: ProgressReporter | None = None,
) -> list[dict[str, Any]]:
    if not trace_ids:
        return []
    scores_client = getattr(getattr(owner.client, "api", None), "scores", None)
    get_many = getattr(scores_client, "get_many", None)
    if not callable(get_many):
        return []
    scores: list[dict[str, Any]] = []
    unique_trace_ids = list(dict.fromkeys(trace_ids))
    reporter = progress or NullProgressReporter()
    with reporter.task("Fetching scores", total=len(unique_trace_ids)) as task:
        for trace_id in unique_trace_ids:
            scores.extend(_scores_for_trace(get_many, trace_id))
            task.advance()
    return scores


def reference_matches(reference: Any, fingerprint: Any) -> bool:
    if fingerprint is None:
        return True
    ref_data = (
        reference.model_dump(mode="json")
        if hasattr(reference, "model_dump")
        else getattr(reference, "__dict__", {})
    )
    fp_data = (
        fingerprint.model_dump(mode="json")
        if hasattr(fingerprint, "model_dump")
        else getattr(fingerprint, "__dict__", {})
    )
    return all(
        ref_data.get(field) == fp_data.get(field) for field in FINGERPRINT_FIELDS
    )


def has_expected_trace_count(
    traces: list[dict[str, Any]],
    expected_count: int | None,
) -> bool:
    return expected_count is None or len(traces) >= expected_count


def langfuse_trace_wait_seconds() -> float:
    return positive_float_env(
        "EVALUATOR_HARNESS_LANGFUSE_TRACE_WAIT_SECONDS",
        default=180.0,
    )


def langfuse_trace_poll_interval_seconds() -> float:
    return positive_float_env(
        "EVALUATOR_HARNESS_LANGFUSE_TRACE_POLL_INTERVAL_SECONDS",
        default=2.0,
    )


def positive_float_env(name: str, *, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return value if value >= 0 else default


def prompt_has_label(prompt: dict[str, Any], label: str) -> bool:
    labels = prompt.get("labels") or []
    if label in labels:
        return True
    config = prompt.get("config") or {}
    return isinstance(config, dict) and config.get("artifact_version") == label


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


def metadata_matches(metadata: dict[str, Any], fingerprint: Any) -> bool:
    fp_data = (
        fingerprint.model_dump(mode="json")
        if hasattr(fingerprint, "model_dump")
        else getattr(fingerprint, "__dict__", {})
    )
    return all(
        metadata_fingerprint_value(metadata, field) == str(fp_data.get(field))
        for field in FINGERPRINT_FIELDS
    )


def metadata_fingerprint_value(metadata: dict[str, Any], field: str) -> str:
    value = (
        metadata.get("dataset_compatibility_version") or metadata.get(field)
        if field == "dataset_version"
        else metadata.get(field)
    )
    return str(value)


def baseline_reference_sort_key(
    run: Any,
    metadata: dict[str, Any],
    index: int,
) -> tuple[datetime, int]:
    created_at = (
        metadata.get("created_at")
        or getattr(run, "created_at", None)
        or getattr(run, "createdAt", None)
        or getattr(run, "created_at_iso", None)
    )
    parsed = parse_datetime(created_at)
    return (parsed or datetime.min.replace(tzinfo=UTC), index)


def parse_datetime(value: Any) -> datetime | None:
    if isinstance(value, datetime):
        return value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=UTC)


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


def _matching_baseline_runs(
    owner: Any,
    runs: list[Any],
    selector: str,
    fingerprint: Any,
    dataset_name: Any,
) -> list[tuple[Any, dict[str, Any], int]]:
    matches: list[tuple[Any, dict[str, Any], int]] = []
    for index, run in enumerate(runs):
        metadata = owner._gateway.dataset_run_metadata(
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
        if metadata_matches(metadata, fingerprint):
            matches.append((run, metadata, index))
    return matches


def _prompt_versions_from_page(
    page: Any,
    name: str | None,
    get_prompt: Any,
) -> list[dict[str, Any]]:
    versions: list[dict[str, Any]] = []
    for item in getattr(page, "data", None) or []:
        meta = object_to_prompt_dict(item)
        prompt_name = str(meta.get("name") or name or "")
        prompt_versions = meta.get("versions") or []
        if callable(get_prompt) and prompt_versions:
            versions.extend(
                _resolved_prompt_versions(get_prompt, prompt_name, prompt_versions)
            )
        else:
            versions.append(meta)
    return versions


def _resolved_prompt_versions(
    get_prompt: Any,
    prompt_name: str,
    prompt_versions: list[Any],
) -> list[dict[str, Any]]:
    versions: list[dict[str, Any]] = []
    for version in prompt_versions:
        version_number = (
            version.get("version") if isinstance(version, dict) else version
        )
        try:
            versions.append(
                object_to_prompt_dict(
                    get_prompt(prompt_name, version=int(version_number), resolve=False)
                )
            )
        except Exception:
            continue
    return versions


def _prompt_create_request(payload: dict[str, Any]) -> Any:
    if payload.get("type") == "chat":
        from langfuse.api.prompts.types.chat_message import ChatMessage
        from langfuse.api.prompts.types.create_chat_prompt_request import (
            CreateChatPromptRequest,
        )
        from langfuse.api.prompts.types.create_chat_prompt_type import (
            CreateChatPromptType,
        )

        return CreateChatPromptRequest(
            name=payload["name"],
            type=CreateChatPromptType.CHAT,
            prompt=[
                ChatMessage(role=message["role"], content=message["content"])
                for message in payload["prompt"]
            ],
            labels=payload.get("labels"),
            tags=payload.get("tags"),
            config=payload.get("config"),
            commit_message=payload.get("commit_message"),
        )

    from langfuse.api.prompts.types.create_text_prompt_request import (
        CreateTextPromptRequest,
    )
    from langfuse.api.prompts.types.create_text_prompt_type import (
        CreateTextPromptType,
    )

    return CreateTextPromptRequest(
        name=payload["name"],
        type=CreateTextPromptType.TEXT,
        prompt=str(payload["prompt"]),
        labels=payload.get("labels"),
        tags=payload.get("tags"),
        config=payload.get("config"),
        commit_message=payload.get("commit_message"),
    )


def _scores_for_trace(get_many: Any, trace_id: str) -> list[dict[str, Any]]:
    scores: list[dict[str, Any]] = []
    page_number = 1
    while True:
        try:
            page = get_many(
                trace_id=trace_id,
                fields="score",
                page=page_number,
                limit=100,
            )
        except Exception:
            break
        scores.extend(
            object_to_score_dict(score) for score in (getattr(page, "data", None) or [])
        )
        meta = getattr(page, "meta", None)
        total_pages = int(getattr(meta, "total_pages", page_number) or page_number)
        if page_number >= total_pages:
            break
        page_number += 1
    return scores
