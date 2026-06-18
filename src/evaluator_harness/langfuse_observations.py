from __future__ import annotations

import hashlib
from contextlib import contextmanager, nullcontext
from typing import Any

from evaluator_harness.errors import LangfuseError
from evaluator_harness.langfuse_sdk import (
    callable_attribute,
    flush_if_supported,
    update_observation,
)


def create_run_workflow(owner: Any, *args: Any, **kwargs: Any) -> Any:
    owner.calls.append(("create_run", {"args": args, "kwargs": kwargs}))
    run_id = str(
        kwargs.get("run_id") or (args[0] if args else f"run-{len(owner.runs) + 1}")
    )
    run = {"run_id": run_id, "args": args, "kwargs": kwargs}
    owner.runs[run_id] = run
    return run


def log_trace_workflow(owner: Any, trace: dict[str, Any]) -> dict[str, Any]:
    stored_trace = {
        key: value for key, value in trace.items() if key != "_live_observation_logged"
    }
    owner.calls.append(("log_trace", stored_trace))
    owner.traces.append(stored_trace)
    if owner.client is not None and not trace.get("_live_observation_logged"):
        _create_live_trace_event(owner, trace)
    return stored_trace


@contextmanager
def trace_span_workflow(
    owner: Any,
    *,
    trace_id: str,
    name: str,
    input: Any,
    metadata: dict[str, Any],
    session_id: str | None = None,
):
    start = callable_attribute(owner.client, "start_as_current_observation")
    if start is None:
        yield None
        return
    with session_attributes_context(session_id):
        with start(
            trace_context={"trace_id": trace_id},
            as_type="span",
            name=name,
            input=input,
            metadata=metadata,
        ) as observation:
            yield observation
    flush_if_supported(owner.client)


def supports_observation_spans(owner: Any) -> bool:
    return callable_attribute(owner.client, "start_as_current_observation") is not None


@contextmanager
def generation_span_workflow(
    owner: Any,
    *,
    name: str,
    input: Any,
    metadata: dict[str, Any],
    model: str,
    model_parameters: dict[str, Any],
    session_id: str | None = None,
):
    start = callable_attribute(owner.client, "start_as_current_observation")
    if start is None:
        yield None
        return
    with session_attributes_context(session_id):
        with start(
            as_type="generation",
            name=name,
            input=input,
            metadata=metadata,
            model=model,
            model_parameters=model_parameters,
        ) as observation:
            yield observation
    flush_if_supported(owner.client)


def observation_id_workflow(observation: Any | None) -> str | None:
    if observation is None:
        return None
    value = getattr(observation, "id", None) or getattr(
        observation,
        "observation_id",
        None,
    )
    return str(value) if value else None


def update_trace_span_workflow(
    owner: Any,
    observation: Any | None,
    trace: dict[str, Any],
) -> bool:
    updated = update_observation(
        observation,
        output=trace.get("output"),
        metadata=trace.get("metadata") or {},
        level="ERROR" if trace.get("error") else "DEFAULT",
        status_message=trace.get("error"),
    )
    if updated:
        flush_if_supported(owner.client)
    return updated


def update_generation_span_workflow(
    owner: Any,
    observation: Any | None,
    response: Any,
) -> bool:
    return update_observation(
        observation,
        output=response.output,
        usage_details=_response_usage_details(response),
        cost_details=_response_cost_details(response),
    )


def create_trace_id_workflow(owner: Any, seed: str) -> str:
    if owner.client is not None:
        create_trace_id = callable_attribute(owner.client, "create_trace_id")
        if create_trace_id is not None:
            return str(create_trace_id(seed=seed))
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:32]


def session_attributes_context(session_id: Any):
    if not isinstance(session_id, str) or not session_id:
        return nullcontext()
    try:
        from langfuse import propagate_attributes
    except Exception:
        return nullcontext()
    return propagate_attributes(session_id=session_id)


def _create_live_trace_event(owner: Any, trace: dict[str, Any]) -> None:
    create_event = callable_attribute(owner.client, "create_event")
    if create_event is None:
        return
    try:
        with session_attributes_context(trace.get("session_id")):
            create_event(
                trace_context={"trace_id": str(trace["trace_id"])},
                name=trace.get("name"),
                input=trace.get("input"),
                output=trace.get("output"),
                metadata=trace.get("metadata") or {},
            )
        flush_if_supported(owner.client)
    except Exception as exc:
        raise LangfuseError(
            f"Unable to create Langfuse trace {trace.get('trace_id')}: {exc}"
        ) from exc


def _response_usage_details(response: Any) -> dict[str, Any] | None:
    if response.input_tokens is None and response.output_tokens is None:
        return None
    return {
        key: value
        for key, value in {
            "input": response.input_tokens,
            "output": response.output_tokens,
        }.items()
        if value is not None
    }


def _response_cost_details(response: Any) -> dict[str, Any] | None:
    return {"total": response.cost_usd} if response.cost_usd is not None else None
