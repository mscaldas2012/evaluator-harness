from __future__ import annotations

from evaluator_harness.config import HumanReviewPolicy
from evaluator_harness.review_selection import stable_review_cohort


def test_stable_review_cohort_is_repeatable_for_same_dataset_and_policy() -> None:
    policy = HumanReviewPolicy(enabled=True, minimum_sample_percent=40)
    item_ids = ["1", "2", "3", "4", "5"]

    first = stable_review_cohort(
        item_ids,
        policy,
        project_name="rewrite-quality",
        dataset_name="rewrite-quality/v1",
        dataset_version="v1",
    )
    second = stable_review_cohort(
        list(reversed(item_ids)),
        policy,
        project_name="rewrite-quality",
        dataset_name="rewrite-quality/v1",
        dataset_version="v1",
    )

    assert first == second
    assert len(first) == 2


def test_stable_review_cohort_changes_with_dataset_version() -> None:
    policy = HumanReviewPolicy(enabled=True, minimum_sample_percent=40)
    item_ids = ["1", "2", "3", "4", "5"]

    first = stable_review_cohort(
        item_ids,
        policy,
        project_name="rewrite-quality",
        dataset_name="rewrite-quality/v1",
        dataset_version="v1",
    )
    second = stable_review_cohort(
        item_ids,
        policy,
        project_name="rewrite-quality",
        dataset_name="rewrite-quality/v1",
        dataset_version="v2",
    )

    assert first != second
