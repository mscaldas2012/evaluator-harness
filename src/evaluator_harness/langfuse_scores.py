from __future__ import annotations

from typing import Any

from evaluator_harness.langfuse_mappers import object_to_score_dict
from evaluator_harness.langfuse_records import LangfuseOperationOutcome
from evaluator_harness.progress import NullProgressReporter, ProgressReporter


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


def fetch_calibration_scores_workflow(
    owner: Any,
    run_id: str,
    *,
    trace_ids: list[str] | None = None,
    progress: ProgressReporter | None = None,
) -> list[dict[str, Any]]:
    scores = fetch_scores_workflow(
        owner,
        run_id,
        trace_ids=trace_ids,
        progress=progress,
    )
    return [*scores, *annotation_scores_for_traces(owner, trace_ids or [])]


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
        _record_score_retrieval_warning(
            owner,
            message="Langfuse score retrieval is unavailable.",
            affected_count=len(set(trace_ids)),
            examples=trace_ids,
            details={"reason": "scores.get_many is not callable"},
        )
        return []
    scores: list[dict[str, Any]] = []
    unique_trace_ids = list(dict.fromkeys(trace_ids))
    reporter = progress or NullProgressReporter()
    with reporter.task("Fetching scores", total=len(unique_trace_ids)) as task:
        for trace_id in unique_trace_ids:
            scores.extend(_scores_for_trace(get_many, trace_id, owner=owner))
            task.advance()
    return scores


def annotation_scores_for_traces(
    owner: Any,
    trace_ids: list[str],
) -> list[dict[str, Any]]:
    trace_id_set = {str(trace_id) for trace_id in trace_ids}
    annotation_scores: list[dict[str, Any]] = []
    for item in getattr(owner, "annotation_queue_items", []):
        if not isinstance(item, dict):
            continue
        if str(item.get("status") or "").upper() not in {"COMPLETED", "DONE"}:
            continue
        trace_id = str(item.get("trace_id") or item.get("object_id") or "")
        if not trace_id or trace_id not in trace_id_set:
            continue
        for score in _annotation_item_scores(item):
            name = score.get("name") or score.get("score_name") or score.get("scoreName")
            value = score.get("value")
            if value is None:
                value = score.get("score")
            if not name or value is None:
                continue
            annotation_scores.append(
                {
                    "trace_id": trace_id,
                    "name": str(name),
                    "value": value,
                    "comment": score.get("comment"),
                    "source": "ANNOTATION",
                }
            )
    return annotation_scores


def _annotation_item_scores(item: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("scores", "annotations", "score_values", "scoreValues"):
        value = item.get(key)
        if isinstance(value, list):
            return [score for score in value if isinstance(score, dict)]
        if isinstance(value, dict):
            return [
                {"name": name, "value": score}
                for name, score in value.items()
            ]
    return []


def _scores_for_trace(
    get_many: Any,
    trace_id: str,
    *,
    owner: Any | None = None,
) -> list[dict[str, Any]]:
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
        except Exception as exc:
            if owner is not None:
                _record_score_retrieval_warning(
                    owner,
                    message=(
                        "Langfuse score retrieval failed; scores may be incomplete."
                    ),
                    affected_count=1,
                    examples=(trace_id,),
                    details={
                        "trace_id": trace_id,
                        "page": page_number,
                        "exception_type": type(exc).__name__,
                        "error": str(exc),
                    },
                )
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


def _record_score_retrieval_warning(
    owner: Any,
    *,
    message: str,
    affected_count: int,
    examples: list[str] | tuple[str, ...],
    details: dict[str, Any],
) -> None:
    record_outcome = getattr(owner, "record_langfuse_outcome", None)
    if not callable(record_outcome):
        return
    record_outcome(
        LangfuseOperationOutcome(
            operation="score_retrieval",
            status="partial_success",
            severity="warning",
            message=message,
            affected_count=max(1, affected_count),
            examples=tuple(str(example) for example in examples),
            details=details,
        )
    )
