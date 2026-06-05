from __future__ import annotations

from evaluator_harness.model_output_targeting import (
    MODEL_OUTPUT_ROLE,
    RUN_ITEM_ROLE,
    final_output_metadata,
    parent_observation_metadata,
)


def test_parent_observation_metadata_uses_non_final_role() -> None:
    metadata = parent_observation_metadata(
        {
            "project": "rewrite-quality",
            "project_version": "v1",
            "observation_role": MODEL_OUTPUT_ROLE,
        }
    )

    assert metadata["project"] == "rewrite-quality"
    assert metadata["project_version"] == "v1"
    assert metadata["observation_role"] == RUN_ITEM_ROLE


def test_final_output_metadata_uses_model_output_role() -> None:
    metadata = final_output_metadata(
        {
            "project": "rewrite-quality",
            "project_version": "v1",
            "observation_role": RUN_ITEM_ROLE,
        }
    )

    assert metadata["project"] == "rewrite-quality"
    assert metadata["project_version"] == "v1"
    assert metadata["observation_role"] == MODEL_OUTPUT_ROLE
