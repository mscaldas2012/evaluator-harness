from __future__ import annotations

from evaluator_harness.langfuse_settings import (
    langfuse_trace_poll_interval_seconds,
    langfuse_trace_wait_seconds,
    positive_float_env,
)


def test_positive_float_env_returns_default_for_missing_invalid_and_negative(
    monkeypatch,
) -> None:
    monkeypatch.delenv("TEST_FLOAT", raising=False)
    assert positive_float_env("TEST_FLOAT", default=3.0) == 3.0

    monkeypatch.setenv("TEST_FLOAT", "not-a-float")
    assert positive_float_env("TEST_FLOAT", default=3.0) == 3.0

    monkeypatch.setenv("TEST_FLOAT", "-1")
    assert positive_float_env("TEST_FLOAT", default=3.0) == 3.0


def test_positive_float_env_accepts_zero_and_positive_values(monkeypatch) -> None:
    monkeypatch.setenv("TEST_FLOAT", "0")
    assert positive_float_env("TEST_FLOAT", default=3.0) == 0

    monkeypatch.setenv("TEST_FLOAT", "1.5")
    assert positive_float_env("TEST_FLOAT", default=3.0) == 1.5


def test_trace_polling_defaults_and_overrides(monkeypatch) -> None:
    monkeypatch.delenv("EVALUATOR_HARNESS_LANGFUSE_TRACE_WAIT_SECONDS", raising=False)
    monkeypatch.delenv(
        "EVALUATOR_HARNESS_LANGFUSE_TRACE_POLL_INTERVAL_SECONDS",
        raising=False,
    )
    assert langfuse_trace_wait_seconds() == 180.0
    assert langfuse_trace_poll_interval_seconds() == 2.0

    monkeypatch.setenv("EVALUATOR_HARNESS_LANGFUSE_TRACE_WAIT_SECONDS", "5")
    monkeypatch.setenv("EVALUATOR_HARNESS_LANGFUSE_TRACE_POLL_INTERVAL_SECONDS", "0.25")
    assert langfuse_trace_wait_seconds() == 5.0
    assert langfuse_trace_poll_interval_seconds() == 0.25
