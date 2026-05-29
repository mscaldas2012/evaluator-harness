from __future__ import annotations

import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


EXPORT_FIELDS = [
    "trace_id",
    "run_id",
    "item_id",
    "project",
    "project_version",
    "dataset_name",
    "dataset_version",
    "prompt_version",
    "prompt_shape",
    "prompt_roles",
    "evaluator_set_id",
    "provider",
    "model",
    "model_name",
    "temperature",
    "generation_parameter_hash",
    "parameter_identity",
    "variant_identity",
    "latency_ms",
    "input_tokens",
    "output_tokens",
    "cost_usd",
    "baseline_run_id",
    "error",
    "timestamp",
    "input",
    "output",
]


@dataclass(frozen=True)
class ExportResult:
    output_path: Path
    row_count: int


def export_summary(
    traces: list[dict[str, Any]],
    output_path: Path,
    *,
    scores: list[dict[str, Any]] | None = None,
) -> ExportResult:
    score_columns = _score_columns(scores or [])
    fieldnames = [*EXPORT_FIELDS, *score_columns]
    scores_by_trace = _scores_by_trace(scores or [])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for trace in traces:
            row = _trace_row(trace)
            row.update(
                _score_row(
                    scores_by_trace.get(str(trace.get("trace_id") or ""), []),
                    score_columns,
                )
            )
            writer.writerow(row)
    return ExportResult(output_path=output_path, row_count=len(traces))


def _trace_row(trace: dict[str, Any]) -> dict[str, Any]:
    metadata = trace.get("metadata", {})
    baseline_reference = metadata.get("baseline_reference") or {}
    return {
        "trace_id": trace.get("trace_id"),
        "run_id": trace.get("run_id"),
        "item_id": metadata.get("dataset_item_id"),
        "project": metadata.get("project"),
        "project_version": metadata.get("project_version"),
        "dataset_name": metadata.get("dataset_name"),
        "dataset_version": metadata.get("dataset_version"),
        "prompt_version": metadata.get("prompt_version"),
        "prompt_shape": metadata.get("prompt_shape"),
        "prompt_roles": _json_or_empty(metadata.get("prompt_roles")),
        "evaluator_set_id": metadata.get("evaluator_set_id"),
        "provider": metadata.get("provider"),
        "model": metadata.get("model"),
        "model_name": metadata.get("model_name"),
        "temperature": metadata.get("temperature"),
        "generation_parameter_hash": metadata.get("generation_parameter_hash"),
        "parameter_identity": _json_or_empty(metadata.get("parameter_identity")),
        "variant_identity": _json_or_empty(metadata.get("variant_identity")),
        "latency_ms": metadata.get("latency_ms"),
        "input_tokens": metadata.get("input_tokens"),
        "output_tokens": metadata.get("output_tokens"),
        "cost_usd": metadata.get("cost_usd"),
        "baseline_run_id": baseline_reference.get("baseline_run_id"),
        "error": trace.get("error"),
        "timestamp": trace.get("timestamp"),
        "input": trace.get("input"),
        "output": trace.get("output"),
    }


def _json_or_empty(value: Any) -> str:
    if value is None:
        return ""
    return json.dumps(value, sort_keys=True)


def _score_columns(scores: list[dict[str, Any]]) -> list[str]:
    names = sorted(
        {
            str(score.get("name"))
            for score in scores
            if score.get("name") is not None and score.get("trace_id") is not None
        }
    )
    columns: list[str] = []
    for name in names:
        slug = _score_name_slug(name)
        columns.extend([f"score_{slug}", f"score_{slug}_comment"])
    return columns


def _scores_by_trace(scores: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_trace: dict[str, list[dict[str, Any]]] = {}
    for score in scores:
        trace_id = score.get("trace_id")
        if trace_id is None:
            continue
        by_trace.setdefault(str(trace_id), []).append(score)
    return by_trace


def _score_row(scores: list[dict[str, Any]], score_columns: list[str]) -> dict[str, Any]:
    row = {column: "" for column in score_columns}
    for score in sorted(scores, key=_score_sort_key):
        name = score.get("name")
        if name is None:
            continue
        slug = _score_name_slug(str(name))
        value = score.get("value")
        if value is None:
            value = score.get("score")
        if value is None:
            value = score.get("string_value")
        row[f"score_{slug}"] = value if value is not None else ""
        row[f"score_{slug}_comment"] = score.get("comment") or ""
    return row


def _score_name_slug(name: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", name).strip("_").lower()
    return slug or "unnamed"


def _score_sort_key(score: dict[str, Any]) -> tuple[str, str, str]:
    return (
        str(score.get("timestamp") or ""),
        str(score.get("created_at") or score.get("createdAt") or ""),
        str(score.get("id") or ""),
    )
