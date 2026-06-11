from __future__ import annotations

from evaluator_harness.config import HumanReviewPolicy
from evaluator_harness.review_selection import ReviewCandidate, select_review_items


def test_select_review_items_prioritizes_risky_outputs_then_deterministic_sample() -> None:
    candidates = [
        ReviewCandidate(item_id="1", run_id="run", trace_id="trace-1", failed=True),
        ReviewCandidate(item_id="2", run_id="run", trace_id="trace-2", confidence=0.3),
        ReviewCandidate(item_id="3", run_id="run", trace_id="trace-3", disputed=True),
        ReviewCandidate(item_id="4", run_id="run", trace_id="trace-4"),
        ReviewCandidate(item_id="5", run_id="run", trace_id="trace-5"),
    ]
    policy = HumanReviewPolicy(enabled=True, minimum_sample_percent=20)

    selected = select_review_items(candidates, policy)

    assert len([item for item in selected if item.selection_bucket == "stable_calibration"]) == 1
    assert any(item.selection_bucket == "run_risk" for item in selected)
    assert ("1", "failure", "run_risk") in [
        (item.item_id, item.selection_reason, item.selection_bucket)
        for item in selected
    ] or any(item.item_id == "1" for item in selected)


def test_select_review_items_enforces_minimum_one_item() -> None:
    candidates = [ReviewCandidate(item_id="1", run_id="run", trace_id="trace-1")]
    policy = HumanReviewPolicy(enabled=True, minimum_sample_percent=5)

    selected = select_review_items(candidates, policy)

    assert len(selected) == 1
    assert selected[0].selection_reason == "sample"
    assert selected[0].selection_bucket == "stable_calibration"


def test_select_review_items_uses_minimum_sample_count_floor() -> None:
    candidates = [
        ReviewCandidate(item_id=str(index), run_id="run", trace_id=f"trace-{index}")
        for index in range(1, 13)
    ]
    policy = HumanReviewPolicy(
        enabled=True,
        minimum_sample_percent=5,
        minimum_sample_count=3,
    )

    selected = select_review_items(candidates, policy)

    assert len([item for item in selected if item.selection_reason == "sample"]) == 3


def test_select_review_items_random_strategy_uses_random_sample(monkeypatch) -> None:
    candidates = [
        ReviewCandidate(item_id=str(index), run_id="run", trace_id=f"trace-{index}")
        for index in range(1, 6)
    ]
    policy = HumanReviewPolicy(
        enabled=True,
        minimum_sample_percent=20,
        minimum_sample_count=2,
        sample_strategy="random",
    )

    def fake_sample(items, *, k):
        assert items == ["1", "2", "3", "4", "5"]
        assert k == 2
        return ["5", "2"]

    monkeypatch.setattr("evaluator_harness.review_selection.random.sample", fake_sample)

    selected = select_review_items(candidates, policy)

    assert [item.item_id for item in selected if item.selection_reason == "sample"] == [
        "5",
        "2",
    ]


def test_select_review_items_cli_strategy_override_wins(monkeypatch) -> None:
    candidates = [
        ReviewCandidate(item_id=str(index), run_id="run", trace_id=f"trace-{index}")
        for index in range(1, 6)
    ]
    policy = HumanReviewPolicy(
        enabled=True,
        minimum_sample_percent=20,
        minimum_sample_count=2,
        sample_strategy="stable",
    )

    monkeypatch.setattr(
        "evaluator_harness.review_selection.random.sample",
        lambda _items, *, k: ["4", "3"][:k],
    )

    selected = select_review_items(candidates, policy, sample_strategy="random")

    assert [item.item_id for item in selected if item.selection_reason == "sample"] == [
        "4",
        "3",
    ]


def test_select_review_items_returns_empty_when_disabled() -> None:
    candidates = [ReviewCandidate(item_id="1", run_id="run", trace_id="trace-1", failed=True)]
    policy = HumanReviewPolicy(enabled=False)

    assert select_review_items(candidates, policy) == []


def test_review_candidate_from_trace_ignores_session_metadata_for_selection() -> None:
    trace = {
        "trace_id": "trace-1",
        "run_id": "candidate-1",
        "error": "provider timeout",
        "metadata": {
            "dataset_item_id": "1",
            "item_comparison_session_id": "eh-item-session",
        },
    }
    scores = [
        {
            "trace_id": "trace-1",
            "confidence": 0.2,
            "disputed": True,
        }
    ]

    candidate = ReviewCandidate.from_trace(trace, scores=scores)

    assert candidate.item_id == "1"
    assert candidate.run_id == "candidate-1"
    assert candidate.trace_id == "trace-1"
    assert candidate.failed is True
    assert candidate.confidence == 0.2
    assert candidate.disputed is True
