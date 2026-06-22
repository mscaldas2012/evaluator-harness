from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from evaluator_harness.config import BaselineReference
from evaluator_harness.langfuse_records import LangfuseOperationOutcome

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
    except Exception as exc:
        _record_lookup_warning(
            owner,
            operation="baseline_lookup",
            message="Langfuse baseline lookup failed.",
            examples=(selector,),
            details={
                "selector": selector,
                "dataset_name": dataset_name,
                "exception_type": type(exc).__name__,
                "error": str(exc),
            },
        )
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
    except Exception as exc:
        _record_lookup_warning(
            owner,
            operation="dataset_run_metadata_lookup",
            message="Langfuse dataset run metadata lookup failed.",
            examples=(str(run_name),),
            details={
                "dataset_name": dataset_name,
                "run_name": str(run_name),
                "exception_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        return {}
    for item in getattr(run_with_items, "items", None) or []:
        item_metadata = getattr(item, "metadata", None) or {}
        if item_metadata and metadata_matches(dict(item_metadata), fingerprint):
            return dict(item_metadata)
    return dict(metadata)


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
