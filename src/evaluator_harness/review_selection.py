from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from math import ceil
import random
from typing import Any, Literal

from evaluator_harness.config import HumanReviewPolicy, HumanReviewSelection


SelectionReason = Literal[
    "failure",
    "low_confidence",
    "disputed",
    "sample",
    "annotated_queue_item",
]
SampleStrategy = Literal["stable", "random"]


@dataclass(frozen=True)
class ReviewCandidate:
    item_id: str
    run_id: str
    trace_id: str
    failed: bool = False
    confidence: float | None = None
    disputed: bool = False

    @classmethod
    def from_trace(
        cls,
        trace: dict[str, Any],
        *,
        scores: list[dict[str, Any]],
    ) -> ReviewCandidate:
        trace_id = str(trace["trace_id"])
        trace_scores = [score for score in scores if score.get("trace_id") == trace_id]
        confidence_values = [
            float(score["confidence"])
            for score in trace_scores
            if score.get("confidence") is not None
        ]
        return cls(
            item_id=str(trace.get("metadata", {}).get("dataset_item_id")),
            run_id=str(trace["run_id"]),
            trace_id=trace_id,
            failed=bool(trace.get("error")),
            confidence=min(confidence_values) if confidence_values else None,
            disputed=any(bool(score.get("disputed")) for score in trace_scores),
        )

    def to_selection(self, reason: SelectionReason) -> HumanReviewSelection:
        bucket = (
            "stable_calibration"
            if reason == "sample"
            else "completed_annotation"
            if reason == "annotated_queue_item"
            else "run_risk"
        )
        return HumanReviewSelection(
            item_id=self.item_id,
            run_id=self.run_id,
            trace_id=self.trace_id,
            selection_reason=reason,
            selection_bucket=bucket,
        )


def review_policy_version(policy: HumanReviewPolicy) -> str:
    if policy.review_policy_version:
        return policy.review_policy_version
    payload = {
        "minimum_sample_percent": policy.minimum_sample_percent,
        "minimum_sample_count": policy.minimum_sample_count,
        "sample_strategy": policy.sample_strategy,
        "prioritize": policy.prioritize,
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()[:16]


def stable_review_cohort(
    item_ids: list[str],
    policy: HumanReviewPolicy,
    *,
    project_name: str,
    dataset_name: str,
    dataset_version: str,
) -> list[str]:
    if not policy.enabled or not item_ids:
        return []
    unique_item_ids = sorted(set(item_ids))
    target_count = _sample_count(len(unique_item_ids), policy)
    seed_prefix = (
        f"{project_name}|{dataset_name}|{dataset_version}|"
        f"{review_policy_version(policy)}|"
    )
    return sorted(
        unique_item_ids,
        key=lambda item_id: hashlib.sha256(
            (seed_prefix + item_id).encode("utf-8")
        ).hexdigest(),
    )[:target_count]


def random_review_cohort(
    item_ids: list[str],
    policy: HumanReviewPolicy,
) -> list[str]:
    if not policy.enabled or not item_ids:
        return []
    unique_item_ids = sorted(set(item_ids))
    target_count = _sample_count(len(unique_item_ids), policy)
    return random.sample(unique_item_ids, k=target_count)


def select_review_items(
    candidates: list[ReviewCandidate],
    policy: HumanReviewPolicy,
    *,
    project_name: str = "default",
    dataset_name: str = "default",
    dataset_version: str = "default",
    sample_strategy: SampleStrategy | None = None,
) -> list[HumanReviewSelection]:
    if not policy.enabled or not candidates:
        return []

    selected: list[HumanReviewSelection] = []
    selected_trace_ids: set[str] = set()
    candidate_by_item = {
        candidate.item_id: candidate
        for candidate in sorted(candidates, key=lambda item: item.trace_id)
    }

    strategy = sample_strategy or policy.sample_strategy
    item_ids = [candidate.item_id for candidate in candidates]
    sample_item_ids = (
        random_review_cohort(item_ids, policy)
        if strategy == "random"
        else stable_review_cohort(
            item_ids,
            policy,
            project_name=project_name,
            dataset_name=dataset_name,
            dataset_version=dataset_version,
        )
    )
    for item_id in sample_item_ids:
        candidate = candidate_by_item[item_id]
        selected.append(candidate.to_selection("sample"))
        selected_trace_ids.add(candidate.trace_id)

    reason_predicates: dict[str, Any] = {
        "failures": lambda candidate: candidate.failed,
        "low_confidence": lambda candidate: (
            candidate.confidence is not None and candidate.confidence < 0.5
        ),
        "disputed": lambda candidate: candidate.disputed,
    }
    reason_names: dict[str, SelectionReason] = {
        "failures": "failure",
        "low_confidence": "low_confidence",
        "disputed": "disputed",
    }

    for priority in policy.prioritize:
        predicate = reason_predicates.get(priority)
        if predicate is None:
            continue
        for candidate in candidates:
            if candidate.trace_id in selected_trace_ids or not predicate(candidate):
                continue
            selected.append(candidate.to_selection(reason_names[priority]))
            selected_trace_ids.add(candidate.trace_id)

    return selected


def _sample_count(unique_item_count: int, policy: HumanReviewPolicy) -> int:
    if unique_item_count <= 0:
        return 0
    percent_count = ceil(unique_item_count * policy.minimum_sample_percent / 100)
    target_count = max(policy.minimum_sample_count, percent_count)
    return min(unique_item_count, target_count)
