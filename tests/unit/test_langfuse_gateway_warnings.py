from __future__ import annotations

import pytest

from evaluator_harness.langfuse_default_gateway import DefaultLangfuseGateway
from evaluator_harness.langfuse_records import (
    LangfuseOperationOutcome,
    LangfuseWarning,
    aggregate_langfuse_warnings,
)


def test_operation_outcome_redacts_details() -> None:
    outcome = LangfuseOperationOutcome(
        operation="dataset_run_item_recording",
        status="partial_success",
        severity="warning",
        message="Langfuse dataset run item was not recorded.",
        details={"error": "authorization: sk-secret123"},
    )

    assert outcome.details["error"] == "authorization: [REDACTED]"


def test_warning_details_redact_bearer_credentials() -> None:
    warning = LangfuseWarning(
        code="trace_lookup",
        operation="trace_lookup",
        message="Langfuse trace lookup failed.",
        details={
            "headers": "Authorization: Bearer super-secret-token",
            "body": "LANGFUSE_SECRET_KEY=sk-secret123",
        },
    )

    assert warning.details["headers"] == "Authorization: [REDACTED]"
    assert "super-secret-token" not in warning.details["headers"]
    assert "sk-secret123" not in warning.details["body"]


def test_operation_outcome_rejects_info_failure() -> None:
    with pytest.raises(ValueError, match="require warning or error"):
        LangfuseOperationOutcome(
            operation="score_retrieval",
            status="failure",
            severity="info",
            message="failed",
        )


def test_expected_not_found_does_not_become_warning() -> None:
    gateway = DefaultLangfuseGateway()

    gateway.record_langfuse_outcome(
        LangfuseOperationOutcome(
            operation="baseline_lookup",
            status="expected_not_found",
            severity="info",
            message="No baseline matched selector.",
        )
    )

    assert gateway.current_langfuse_warnings() == ()


def test_warning_aggregation_bounds_examples() -> None:
    warnings = aggregate_langfuse_warnings(
        [
            LangfuseWarning(
                code="dataset_run_item_recording",
                operation="dataset_run_item_recording",
                message="Langfuse dataset run item was not recorded.",
                examples=("item-1",),
            ),
            LangfuseWarning(
                code="dataset_run_item_recording",
                operation="dataset_run_item_recording",
                message="Langfuse dataset run item was not recorded.",
                examples=("item-2", "item-3", "item-4"),
            ),
        ]
    )

    assert len(warnings) == 1
    assert warnings[0].affected_count == 2
    assert warnings[0].examples == ("item-1", "item-2", "item-3")


def test_gateway_aggregates_multiple_affected_run_items() -> None:
    gateway = DefaultLangfuseGateway()

    for item_id in ("item-1", "item-2"):
        gateway.record_langfuse_outcome(
            LangfuseOperationOutcome(
                operation="dataset_run_item_recording",
                status="partial_success",
                severity="warning",
                message="Langfuse dataset run item was not recorded.",
                examples=(item_id,),
            )
        )

    warnings = gateway.current_langfuse_warnings()

    assert len(warnings) == 1
    assert warnings[0].affected_count == 2
    assert warnings[0].examples == ("item-1", "item-2")
