from __future__ import annotations

from types import SimpleNamespace

from evaluator_harness.langfuse_default_gateway import DefaultLangfuseGateway
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


def test_live_score_retrieval_failure_produces_lookup_warning() -> None:
    def get_many(*, trace_id: str, fields: str, page: int, limit: int) -> object:
        raise RuntimeError("authorization: sk-secret123")

    gateway = DefaultLangfuseGateway(
        client=SimpleNamespace(api=SimpleNamespace(scores=SimpleNamespace(get_many=get_many)))
    )

    scores = gateway.fetch_scores("candidate-1", trace_ids=["trace-1"])

    warnings = gateway.current_langfuse_warnings()
    assert scores == []
    assert len(warnings) == 1
    assert warnings[0].operation == "score_retrieval"
    assert warnings[0].affected_count == 1
    assert warnings[0].examples == ("trace-1",)
    assert warnings[0].details["error"] == "authorization: [REDACTED]"


def test_calibration_scores_include_completed_annotation_queue_scores() -> None:
    gateway = DefaultLangfuseGateway(
        scores={
            "candidate-1": [
                {
                    "id": "score-1",
                    "trace_id": "trace-1",
                    "name": "clarity",
                    "value": 0.8,
                    "source": "EVAL",
                }
            ]
        },
        annotation_queue_items=[
            {
                "queue_id": "queue-1",
                "trace_id": "trace-1",
                "object_id": "trace-1",
                "status": "COMPLETED",
                "scores": [
                    {
                        "name": "clarity",
                        "value": 0.6,
                        "comment": "human label",
                    }
                ],
            }
        ],
    )

    scores = gateway.fetch_calibration_scores(
        "candidate-1",
        trace_ids=["trace-1"],
    )

    assert scores == [
        {
            "id": "score-1",
            "trace_id": "trace-1",
            "name": "clarity",
            "value": 0.8,
            "source": "EVAL",
        },
        {
            "trace_id": "trace-1",
            "name": "clarity",
            "value": 0.6,
            "comment": "human label",
            "source": "ANNOTATION",
        },
    ]
