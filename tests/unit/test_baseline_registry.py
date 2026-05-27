from __future__ import annotations

import pytest

from evaluator_harness.baseline_registry import (
    BaselineRegistry,
    build_baseline_fingerprint,
)
from evaluator_harness.config import load_project_config
from evaluator_harness.errors import ConfigError


def test_baseline_fingerprint_includes_comparison_fields() -> None:
    config = load_project_config("configs/projects/rewrite_quality.yaml")

    fingerprint = build_baseline_fingerprint(
        config,
        dataset_name="rewrite-quality/v1",
        dataset_version="v1",
    )

    assert fingerprint.project_name == "rewrite-quality"
    assert fingerprint.prompt_version == "v1"
    assert fingerprint.baseline_model == "gpt5.2-dgw-default"
    assert fingerprint.baseline_parameters_hash
    assert "clarity:v1" in fingerprint.evaluator_set_id


def test_baseline_registry_rejects_mismatch() -> None:
    registry = BaselineRegistry()
    config = load_project_config("configs/projects/rewrite_quality.yaml")
    fingerprint = build_baseline_fingerprint(config, dataset_name="dataset", dataset_version="v1")
    registry.record("baseline-1", fingerprint)

    mismatched = fingerprint.model_copy(update={"dataset_version": "v2"})

    with pytest.raises(ConfigError, match="compatible baseline"):
        registry.resolve_latest_compatible(mismatched)
