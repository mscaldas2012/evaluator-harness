from __future__ import annotations

from typing import Any

from evaluator_harness.langfuse_mappers import object_to_score_dict
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
