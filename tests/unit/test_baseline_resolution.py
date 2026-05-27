from __future__ import annotations

import pytest

from evaluator_harness.baseline_registry import (
    BaselineRegistry,
    build_baseline_fingerprint,
)
from evaluator_harness.config import load_project_config
from evaluator_harness.errors import ConfigError


def test_resolves_latest_compatible_baseline() -> None:
    config = load_project_config("configs/projects/rewrite_quality.yaml")
    fingerprint = build_baseline_fingerprint(
        config,
        dataset_name="rewrite-quality/v1",
        dataset_version="latest",
    )
    registry = BaselineRegistry()
    registry.record("baseline-old", fingerprint)
    registry.record("baseline-new", fingerprint)

    assert registry.resolve("latest-compatible", fingerprint) == "baseline-new"


def test_resolves_explicit_compatible_baseline_run_id() -> None:
    config = load_project_config("configs/projects/rewrite_quality.yaml")
    fingerprint = build_baseline_fingerprint(
        config,
        dataset_name="rewrite-quality/v1",
        dataset_version="latest",
    )
    registry = BaselineRegistry()
    registry.record("baseline-123", fingerprint)

    assert registry.resolve("baseline-123", fingerprint) == "baseline-123"


def test_rejects_incompatible_explicit_baseline_run_id() -> None:
    config = load_project_config("configs/projects/rewrite_quality.yaml")
    fingerprint = build_baseline_fingerprint(
        config,
        dataset_name="rewrite-quality/v1",
        dataset_version="latest",
    )
    registry = BaselineRegistry()
    registry.record(
        "baseline-123",
        fingerprint.model_copy(update={"dataset_version": "other"}),
    )

    with pytest.raises(ConfigError, match="compatible baseline"):
        registry.resolve("baseline-123", fingerprint)
