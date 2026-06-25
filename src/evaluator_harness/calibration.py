from __future__ import annotations

import csv
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any

from evaluator_harness.config import ProjectConfig
from evaluator_harness.errors import ConfigError
from evaluator_harness.evaluators import managed_score_name
from evaluator_harness.review_routing import review_dataset_identity
from evaluator_harness.review_selection import ReviewCandidate, select_review_items


@dataclass(frozen=True)
class CalibrationRecord:
    item_id: str
    trace_id: str
    run_id: str
    evaluator_name: str
    selection_reason: str
    selection_bucket: str
    score_target: str | None = None
    evaluator_version: str | None = None
    automated_score: float | None = None
    human_score: float | None = None
    automated_score_source: str | None = None
    human_score_source: str | None = None
    prompt_version: str | None = None
    evaluator_set_id: str | None = None

    @property
    def score_delta(self) -> float | None:
        if self.automated_score is None or self.human_score is None:
            return None
        return round(self.human_score - self.automated_score, 10)

    @property
    def paired(self) -> bool:
        return self.automated_score is not None and self.human_score is not None

    @property
    def pending_label(self) -> bool:
        return self.automated_score is not None and self.human_score is None

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "trace_id": self.trace_id,
            "run_id": self.run_id,
            "evaluator_name": self.evaluator_name,
            "score_target": self.score_target,
            "evaluator_version": self.evaluator_version,
            "selection_reason": self.selection_reason,
            "selection_bucket": self.selection_bucket,
            "automated_score": self.automated_score,
            "human_score": self.human_score,
            "automated_score_source": self.automated_score_source,
            "human_score_source": self.human_score_source,
            "prompt_version": self.prompt_version,
            "evaluator_set_id": self.evaluator_set_id,
            "score_delta": self.score_delta,
            "paired": self.paired,
            "pending_label": self.pending_label,
        }


@dataclass(frozen=True)
class CalibrationSnapshotResult:
    output_path: Path
    row_count: int
    paired_count: int
    pending_count: int
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class CalibrationEvaluatorSummary:
    project_name: str
    project_version: str
    run_id: str
    evaluator_name: str
    score_target: str | None
    record_count: int
    paired_count: int
    pending_count: int
    paired_coverage: float
    disagreement_rate: float
    mean_absolute_score_delta: float
    directional_bias: float
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "project_name": self.project_name,
            "project_version": self.project_version,
            "run_id": self.run_id,
            "evaluator_name": self.evaluator_name,
            "score_target": self.score_target,
            "record_count": self.record_count,
            "paired_count": self.paired_count,
            "pending_count": self.pending_count,
            "paired_coverage": self.paired_coverage,
            "disagreement_rate": self.disagreement_rate,
            "mean_absolute_score_delta": self.mean_absolute_score_delta,
            "directional_bias": self.directional_bias,
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class CalibrationSummaryResult:
    output_path: Path
    summary_count: int
    paired_count: int
    pending_count: int
    warnings: tuple[str, ...] = ()


def build_calibration_snapshot(
    *,
    project_name: str,
    project_version: str,
    run_id: str,
    run_type: str,
    traces: list[dict[str, Any]],
    scores: list[dict[str, Any]],
    selections: list[dict[str, Any]],
    evaluator_names: list[str] | None = None,
    evaluator_versions: dict[str, str] | None = None,
    evaluator_score_names: dict[str, list[str]] | None = None,
    warnings: tuple[str, ...] = (),
    output_dir: Path,
) -> CalibrationSnapshotResult:
    effective_versions = evaluator_versions or {
        name: None for name in (evaluator_names or [])
    }
    effective_score_names = evaluator_score_names or {
        name: [name] for name in effective_versions
    }
    records = _build_records(
        traces=traces,
        scores=scores,
        selections=selections,
        evaluator_versions=effective_versions,
        evaluator_score_names=effective_score_names,
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{run_id}.json"
    csv_path = output_dir / f"{run_id}.csv"
    payload = [record.to_dict() for record in records]
    warnings = (*warnings, *_capture_warnings(payload, selections))
    existing_payload = _read_snapshot_payload(output_path)
    if existing_payload is not None and _snapshot_is_richer(existing_payload, payload):
        existing_counts = _snapshot_counts(existing_payload)
        preserve_warning = (
            "preserved existing calibration snapshot because the new capture "
            "was smaller or less paired; use a clean output path after confirming "
            "Langfuse trace and score retrieval is complete."
        )
        return CalibrationSnapshotResult(
            output_path=output_path,
            row_count=existing_counts["row_count"],
            paired_count=existing_counts["paired_count"],
            pending_count=existing_counts["pending_count"],
            warnings=(preserve_warning, *warnings),
        )
    _write_json(output_path, payload)
    _write_csv(csv_path, payload)
    return CalibrationSnapshotResult(
        output_path=output_path,
        row_count=len(records),
        paired_count=sum(1 for record in records if record.paired),
        pending_count=sum(1 for record in records if record.pending_label),
        warnings=warnings,
    )


def capture_calibration_snapshot(
    *,
    config: ProjectConfig,
    run_id: str,
    run_type: str,
    traces: list[dict[str, Any]],
    scores: list[dict[str, Any]],
    completed_annotation_trace_ids: set[str] | None = None,
    warnings: tuple[str, ...] = (),
    output_dir: Path,
) -> CalibrationSnapshotResult:
    dataset_name, dataset_version = review_dataset_identity(config, traces)
    candidates = [ReviewCandidate.from_trace(trace, scores=scores) for trace in traces]
    if completed_annotation_trace_ids:
        completed_ids = {str(trace_id) for trace_id in completed_annotation_trace_ids}
        selections = [
            candidate.to_selection("annotated_queue_item").model_dump(mode="json")
            for candidate in candidates
            if candidate.trace_id in completed_ids
        ]
    else:
        selections = [
            selection.model_dump(mode="json")
            for selection in select_review_items(
                candidates,
                config.human_review,
                project_name=config.project.name,
                dataset_name=dataset_name,
                dataset_version=dataset_version,
            )
        ]
    evaluator_versions = {
        evaluator.name: evaluator.version for evaluator in config.evaluators
    }
    evaluator_score_names = {
        evaluator.name: list(
            dict.fromkeys(
                [
                    managed_score_name(config, evaluator.score),
                    evaluator.score.name,
                    evaluator.name,
                ]
            )
        )
        for evaluator in config.evaluators
    }
    return build_calibration_snapshot(
        project_name=config.project.name,
        project_version=config.project.version,
        run_id=run_id,
        run_type=run_type,
        traces=traces,
        scores=scores,
        selections=selections,
        evaluator_versions=evaluator_versions,
        evaluator_score_names=evaluator_score_names,
        warnings=warnings,
        output_dir=output_dir,
    )


def load_calibration_inputs_from_export(
    export_path: Path,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    traces: list[dict[str, Any]] = []
    scores: list[dict[str, Any]] = []
    with export_path.open(newline="", encoding="utf-8-sig") as handle:
        for row in csv.DictReader(handle):
            trace_id = str(row.get("trace_id") or "")
            if not trace_id:
                continue
            metadata = _metadata_from_export_row(row)
            traces.append(
                {
                    "trace_id": trace_id,
                    "run_id": row.get("run_id"),
                    "input": row.get("input"),
                    "output": row.get("output"),
                    "error": row.get("error") or None,
                    "timestamp": row.get("timestamp") or "",
                    "metadata": metadata,
                }
            )
            scores.extend(_scores_from_export_row(row, trace_id=trace_id))
    return traces, scores


def summarize_calibration_snapshot(
    snapshot_path: Path,
    *,
    project_name: str,
    project_version: str,
    output_dir: Path | None = None,
) -> CalibrationSummaryResult:
    if not snapshot_path.exists():
        raise ConfigError(f"Calibration snapshot not found: {snapshot_path}")
    try:
        payload = json.loads(snapshot_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"Invalid calibration snapshot: {snapshot_path}") from exc
    if not isinstance(payload, list):
        raise ConfigError(f"Invalid calibration snapshot: {snapshot_path}")

    summaries = _summarize_records(
        payload,
        project_name=project_name,
        project_version=project_version,
        fallback_run_id=snapshot_path.stem,
    )
    effective_output_dir = output_dir or snapshot_path.parent
    effective_output_dir.mkdir(parents=True, exist_ok=True)
    output_path = effective_output_dir / f"{snapshot_path.stem}-summary.json"
    summary_payload = [summary.to_dict() for summary in summaries]
    _write_json(output_path, summary_payload)
    warnings = tuple(
        warning for summary in summaries for warning in summary.warnings
    )
    return CalibrationSummaryResult(
        output_path=output_path,
        summary_count=len(summaries),
        paired_count=sum(summary.paired_count for summary in summaries),
        pending_count=sum(summary.pending_count for summary in summaries),
        warnings=warnings,
    )


def calibration_reports_dir(project_name: str, *, reports_root: Path | None = None) -> Path:
    root = reports_root or Path("reports")
    return root / project_name / "calibration"


def _summarize_records(
    records: list[Any],
    *,
    project_name: str,
    project_version: str,
    fallback_run_id: str,
) -> list[CalibrationEvaluatorSummary]:
    grouped: dict[tuple[str, str | None], list[dict[str, Any]]] = {}
    for record in records:
        if not isinstance(record, dict):
            raise ConfigError("Calibration snapshot records must be objects")
        evaluator_name = str(record.get("evaluator_name") or "")
        if not evaluator_name:
            raise ConfigError("Calibration snapshot record missing evaluator_name")
        score_target = record.get("score_target") or evaluator_name
        grouped.setdefault((evaluator_name, str(score_target)), []).append(record)

    summaries: list[CalibrationEvaluatorSummary] = []
    for (evaluator_name, score_target), evaluator_records in sorted(grouped.items()):
        run_id = str(evaluator_records[0].get("run_id") or fallback_run_id)
        paired_records = [
            record
            for record in evaluator_records
            if _numeric_value(record.get("automated_score")) is not None
            and _numeric_value(record.get("human_score")) is not None
        ]
        deltas = [
            round(
                _numeric_value(record.get("human_score"))
                - _numeric_value(record.get("automated_score")),
                10,
            )
            for record in paired_records
        ]
        pending_count = sum(
            1
            for record in evaluator_records
            if bool(record.get("pending_label"))
            or (
                _numeric_value(record.get("automated_score")) is not None
                and _numeric_value(record.get("human_score")) is None
            )
        )
        warnings: tuple[str, ...] = ()
        if not paired_records:
            warnings = (
                f"Evaluator {evaluator_name} has zero paired coverage for run {run_id}.",
            )
        summaries.append(
            CalibrationEvaluatorSummary(
                project_name=project_name,
                project_version=project_version,
                run_id=run_id,
                evaluator_name=evaluator_name,
                score_target=score_target,
                record_count=len(evaluator_records),
                paired_count=len(paired_records),
                pending_count=pending_count,
                paired_coverage=_rounded_ratio(len(paired_records), len(evaluator_records)),
                disagreement_rate=_rounded_ratio(
                    sum(1 for delta in deltas if delta != 0.0),
                    len(paired_records),
                ),
                mean_absolute_score_delta=_rounded_mean(
                    [abs(delta) for delta in deltas]
                ),
                directional_bias=_rounded_mean(deltas),
                warnings=warnings,
            )
        )
    return summaries


def _build_records(
    *,
    traces: list[dict[str, Any]],
    scores: list[dict[str, Any]],
    selections: list[dict[str, Any]],
    evaluator_versions: dict[str, str],
    evaluator_score_names: dict[str, list[str]],
) -> list[CalibrationRecord]:
    traces_by_id = {
        str(trace.get("trace_id") or ""): trace for trace in traces if trace.get("trace_id")
    }
    scores_by_trace: dict[str, list[dict[str, Any]]] = {}
    for score in scores:
        trace_id = score.get("trace_id")
        if trace_id is None:
            continue
        scores_by_trace.setdefault(str(trace_id), []).append(score)

    records: list[CalibrationRecord] = []
    for selection in selections:
        trace_id = str(selection.get("trace_id") or "")
        trace = traces_by_id.get(trace_id, {})
        metadata = trace.get("metadata", {}) if isinstance(trace, dict) else {}
        trace_scores = scores_by_trace.get(trace_id, [])
        for evaluator_name, evaluator_version in evaluator_versions.items():
            score_names = evaluator_score_names.get(evaluator_name, [evaluator_name])
            automated = _score_for_source(trace_scores, score_names, "EVAL")
            human = _score_for_source(trace_scores, score_names, "ANNOTATION")
            if (
                selection.get("selection_bucket") == "completed_annotation"
                and (automated is None or human is None)
            ):
                continue
            if automated is None and human is None:
                continue
            records.append(
                CalibrationRecord(
                    item_id=str(selection.get("item_id") or metadata.get("dataset_item_id") or ""),
                    trace_id=trace_id,
                    run_id=str(selection.get("run_id") or trace.get("run_id") or ""),
                    evaluator_name=evaluator_name,
                    score_target=score_names[0] if score_names else evaluator_name,
                    evaluator_version=evaluator_version,
                    selection_reason=str(selection.get("selection_reason") or "sample"),
                    selection_bucket=str(selection.get("selection_bucket") or "stable_calibration"),
                    automated_score=_score_value(automated),
                    human_score=_score_value(human),
                    automated_score_source=_score_source(automated),
                    human_score_source=_score_source(human),
                    prompt_version=str(metadata.get("prompt_version") or "") or None,
                    evaluator_set_id=str(metadata.get("evaluator_set_id") or "") or None,
                )
            )
    return records


def _score_for_source(
    scores: list[dict[str, Any]],
    score_names: list[str],
    source: str,
) -> dict[str, Any] | None:
    for score_name in score_names:
        for score in scores:
            if str(score.get("name") or "") != score_name:
                continue
            if str(score.get("source") or "").upper() != source:
                continue
            return score
    return None


def _score_value(score: dict[str, Any] | None) -> float | None:
    if score is None:
        return None
    value = score.get("value")
    if value is None:
        value = score.get("score")
    if value is None:
        return None
    return float(value)


def _score_source(score: dict[str, Any] | None) -> str | None:
    if score is None:
        return None
    source = score.get("source")
    if source is None:
        return None
    return str(source)


def _metadata_from_export_row(row: dict[str, str]) -> dict[str, Any]:
    metadata_keys = [
        "project",
        "project_version",
        "scenario_group",
        "scenario_name",
        "scenario_display_name",
        "dataset_name",
        "dataset_version",
        "prompt_version",
        "prompt_shape",
        "prompt_artifact_type",
        "prompt_artifact_name",
        "prompt_local_path",
        "prompt_content_identity",
        "prompt_managed_name",
        "langfuse_prompt_name",
        "langfuse_prompt_version",
        "evaluator_set_id",
        "provider",
        "model",
        "model_name",
        "temperature",
        "generation_parameter_hash",
        "item_comparison_session_id",
        "parameter_identity",
        "variant_identity",
        "latency_ms",
        "input_tokens",
        "output_tokens",
        "cost_usd",
    ]
    metadata = {
        key: row.get(key)
        for key in metadata_keys
        if row.get(key) not in (None, "")
    }
    if row.get("item_id"):
        metadata["dataset_item_id"] = row["item_id"]
    if row.get("baseline_run_id"):
        metadata["baseline_reference"] = {"baseline_run_id": row["baseline_run_id"]}
    if row.get("dataset_version"):
        metadata["dataset_compatibility_version"] = row["dataset_version"]
    return metadata


def _scores_from_export_row(
    row: dict[str, str],
    *,
    trace_id: str,
) -> list[dict[str, Any]]:
    scores: list[dict[str, Any]] = []
    for key, value in row.items():
        if not key.startswith("score_") or key.endswith("_comment"):
            continue
        if value in (None, ""):
            continue
        score_name = key.removeprefix("score_")
        scores.append(
            {
                "trace_id": trace_id,
                "name": score_name,
                "value": float(value),
                "comment": row.get(f"{key}_comment") or None,
                "source": "EVAL",
            }
        )
    return scores


def _numeric_value(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _rounded_ratio(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 0.0
    return round(numerator / denominator, 10)


def _rounded_mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 10)


def _write_csv(output_path: Path, payload: list[dict[str, Any]]) -> None:
    fieldnames = list(payload[0].keys()) if payload else []
    with output_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        if fieldnames:
            writer.writeheader()
        writer.writerows(payload)


def _write_json(output_path: Path, payload: list[dict[str, Any]]) -> None:
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _capture_warnings(
    payload: list[dict[str, Any]],
    selections: list[dict[str, Any]],
) -> tuple[str, ...]:
    if selections and not payload:
        return (
            "Calibration capture found selected review items but no matching "
            "evaluator or annotation scores.",
        )
    return ()


def _read_snapshot_payload(output_path: Path) -> list[dict[str, Any]] | None:
    if not output_path.exists():
        return None
    try:
        payload = json.loads(output_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    if not isinstance(payload, list):
        return None
    return [item for item in payload if isinstance(item, dict)]


def _snapshot_is_richer(
    existing_payload: list[dict[str, Any]],
    new_payload: list[dict[str, Any]],
) -> bool:
    existing_counts = _snapshot_counts(existing_payload)
    new_counts = _snapshot_counts(new_payload)
    if existing_counts["paired_count"] > new_counts["paired_count"]:
        return True
    return (
        existing_counts["paired_count"] == new_counts["paired_count"]
        and existing_counts["pending_count"] <= new_counts["pending_count"]
        and existing_counts["row_count"] > new_counts["row_count"]
    )


def _snapshot_counts(payload: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "row_count": len(payload),
        "paired_count": sum(
            1
            for item in payload
            if bool(item.get("paired"))
            or (
                item.get("automated_score") is not None
                and item.get("human_score") is not None
            )
        ),
        "pending_count": sum(
            1
            for item in payload
            if bool(item.get("pending_label"))
            or (
                item.get("automated_score") is not None
                and item.get("human_score") is None
            )
        ),
    }
