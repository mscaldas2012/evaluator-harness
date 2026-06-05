from __future__ import annotations

from evaluator_harness.model_output_targeting import (
    MODEL_OUTPUT_ROLE,
    diagnose_model_output_targeting,
)


def test_diagnostic_reports_aligned_targeting() -> None:
    diagnostic = diagnose_model_output_targeting(
        [
            {
                "trace_id": "trace-1",
                "metadata": {"observation_role": MODEL_OUTPUT_ROLE},
            },
            {
                "trace_id": "trace-2",
                "metadata": {"observation_role": MODEL_OUTPUT_ROLE},
            },
        ],
        expected_completed_count=2,
    )

    assert diagnostic.status == "aligned"
    assert "2 model-output observations" in diagnostic.message


def test_diagnostic_reports_missing_targeting() -> None:
    diagnostic = diagnose_model_output_targeting(
        [{"trace_id": "trace-1", "metadata": {"observation_role": "run_item"}}],
        expected_completed_count=1,
    )

    assert diagnostic.status == "missing"
    assert "0 model-output observations" in diagnostic.message


def test_diagnostic_reports_duplicate_targeting() -> None:
    diagnostic = diagnose_model_output_targeting(
        [
            {
                "trace_id": "trace-1",
                "metadata": {"observation_role": MODEL_OUTPUT_ROLE},
            },
            {
                "trace_id": "trace-1",
                "metadata": {"observation_role": MODEL_OUTPUT_ROLE},
            },
        ],
        expected_completed_count=1,
    )

    assert diagnostic.status == "duplicate"
    assert "Duplicate" in diagnostic.message


def test_diagnostic_reports_provider_specific_targeting() -> None:
    diagnostic = diagnose_model_output_targeting(
        [
            {
                "trace_id": "trace-1",
                "name": "provider-specific-output",
                "metadata": {"observation_role": "provider_output"},
            }
        ],
        expected_completed_count=1,
    )

    assert diagnostic.status == "provider_specific"
    assert "explicit target_observation_name" in diagnostic.message
