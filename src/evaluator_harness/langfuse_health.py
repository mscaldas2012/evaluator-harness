from __future__ import annotations

from typing import Any

from evaluator_harness.errors import FailureContext, LangfuseError


def check_reachable_workflow(
    owner: Any,
    *,
    operation: str = "langfuse",
    dataset_item_id: str | None = None,
) -> None:
    owner.calls.append(("check_reachable", {"operation": operation}))
    if not owner.reachable:
        raise LangfuseError(
            f"Langfuse is unreachable during {operation}",
            context=FailureContext(
                operation=operation,
                dataset_item_id=dataset_item_id,
            ),
        )
    if owner.client is not None:
        verify_workspace_access(owner, operation, dataset_item_id)


def verify_workspace_access(
    owner: Any,
    operation: str,
    dataset_item_id: str | None,
) -> None:
    try:
        auth_check = getattr(owner.client, "auth_check", None)
        if callable(auth_check):
            auth_check()
    except Exception as exc:
        raise LangfuseError(
            "Langfuse workspace access could not be verified during "
            f"{operation}: {exc}",
            context=FailureContext(
                operation=operation,
                dataset_item_id=dataset_item_id,
            ),
        ) from exc
