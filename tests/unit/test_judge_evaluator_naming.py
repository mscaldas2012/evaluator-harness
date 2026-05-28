from __future__ import annotations

import pytest

from evaluator_harness.langfuse_evaluator_setup import (
    build_managed_evaluator_name,
    validate_managed_evaluator_name,
)


def test_managed_evaluator_name_uses_project_version_dimension_source_and_target() -> None:
    assert (
        build_managed_evaluator_name(
            project_slug="rewrite-quality",
            project_version="v1",
            dimension="clarity",
            evaluator_version="v2",
            source_type="custom",
            target_type="observation",
        )
        == "EH_rewrite-quality_v1_judge_clarity_v2_custom_observation"
    )


def test_managed_evaluator_name_rejects_score_source_terms() -> None:
    with pytest.raises(ValueError, match="score source"):
        validate_managed_evaluator_name(
            "EH_rewrite-quality_v1_judge_clarity_v2_custom_observation_eval"
        )


def test_managed_evaluator_name_rejects_unsafe_characters() -> None:
    with pytest.raises(ValueError, match="slug-safe"):
        validate_managed_evaluator_name("EH_rewrite-quality v1")
