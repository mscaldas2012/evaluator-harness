from __future__ import annotations

from types import SimpleNamespace

from evaluator_harness.langfuse_scores import _scores_for_trace


def test_scores_for_trace_paginates_and_normalizes_scores() -> None:
    pages = {
        1: SimpleNamespace(
            data=[SimpleNamespace(id="score-1", trace_id="trace-1", value=1)],
            meta=SimpleNamespace(total_pages=2),
        ),
        2: SimpleNamespace(
            data=[SimpleNamespace(id="score-2", trace_id="trace-1", value=0)],
            meta=SimpleNamespace(total_pages=2),
        ),
    }

    scores = _scores_for_trace(
        lambda *, trace_id, fields, page, limit: pages[page],
        "trace-1",
    )

    assert [score["id"] for score in scores] == ["score-1", "score-2"]
    assert {score["trace_id"] for score in scores} == {"trace-1"}


def test_scores_for_trace_returns_partial_results_when_later_page_fails() -> None:
    def get_many(*, trace_id: str, fields: str, page: int, limit: int) -> object:
        if page == 2:
            raise RuntimeError("rate limited")
        return SimpleNamespace(
            data=[SimpleNamespace(id="score-1", trace_id=trace_id, value=1)],
            meta=SimpleNamespace(total_pages=2),
        )

    assert len(_scores_for_trace(get_many, "trace-1")) == 1
