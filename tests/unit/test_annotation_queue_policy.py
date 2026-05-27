from __future__ import annotations

from pathlib import Path

import pytest

from evaluator_harness.config import HumanReviewPolicy, load_project_config
from evaluator_harness.errors import ConfigError


def test_managed_review_policy_defaults() -> None:
    policy = HumanReviewPolicy()

    assert policy.queue_ownership == "managed_by_harness"
    assert policy.queue_name is None
    assert policy.fallback_to_env is True


def test_user_owned_policy_requires_queue_id() -> None:
    with pytest.raises(ValueError, match="annotation_queue_id"):
        HumanReviewPolicy(queue_ownership="user_owned")


def test_queue_name_must_be_slug_safe() -> None:
    with pytest.raises(ValueError, match="queue_name"):
        HumanReviewPolicy(queue_name="not a safe queue")


def test_project_config_accepts_managed_queue_policy() -> None:
    config = load_project_config("tests/fixtures/projects/managed_annotation_queue.yaml")

    assert config.human_review.queue_ownership == "managed_by_harness"


def test_project_validation_reports_invalid_user_owned_queue() -> None:
    project = Path(".evaluator-harness/test-artifacts/invalid-user-owned.yaml")
    project.parent.mkdir(parents=True, exist_ok=True)
    text = "tests/fixtures/projects/managed_annotation_queue.yaml"
    project.write_text(
        open(text, encoding="utf-8").read().replace(
            "queue_ownership: managed_by_harness",
            "queue_ownership: user_owned",
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="annotation_queue_id"):
        load_project_config(project)
