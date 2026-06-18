from __future__ import annotations

import os


def langfuse_trace_wait_seconds() -> float:
    return positive_float_env(
        "EVALUATOR_HARNESS_LANGFUSE_TRACE_WAIT_SECONDS",
        default=180.0,
    )


def langfuse_trace_poll_interval_seconds() -> float:
    return positive_float_env(
        "EVALUATOR_HARNESS_LANGFUSE_TRACE_POLL_INTERVAL_SECONDS",
        default=2.0,
    )


def positive_float_env(name: str, *, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return value if value >= 0 else default
