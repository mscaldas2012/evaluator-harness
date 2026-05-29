from __future__ import annotations

import csv
import json
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


def export_summary(traces: list[dict[str, Any]], output_path: Path) -> ExportResult:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=EXPORT_FIELDS)
        writer.writeheader()
        for trace in traces:
            writer.writerow(_trace_row(trace))
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
