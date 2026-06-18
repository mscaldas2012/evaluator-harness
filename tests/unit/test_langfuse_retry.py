from __future__ import annotations

import httpx
import pytest

from evaluator_harness.errors import LangfuseError
from evaluator_harness.langfuse_retry import (
    is_retryable_langfuse_error,
    redact_langfuse_message,
    retry_after_seconds,
    with_langfuse_retries,
)


def _status_error(
    status_code: int,
    *,
    retry_after: str | None = None,
) -> httpx.HTTPStatusError:
    request = httpx.Request("GET", "https://langfuse.test")
    response = httpx.Response(
        status_code,
        request=request,
        headers={"Retry-After": retry_after} if retry_after is not None else {},
    )
    return httpx.HTTPStatusError("failed", request=request, response=response)


def test_retryable_langfuse_error_classification() -> None:
    assert is_retryable_langfuse_error(_status_error(429))
    assert is_retryable_langfuse_error(httpx.ConnectTimeout("timeout"))
    assert is_retryable_langfuse_error(RuntimeError("HTTP 503 temporarily unavailable"))
    assert not is_retryable_langfuse_error(_status_error(404))


def test_retry_after_seconds_parses_non_negative_numbers() -> None:
    assert retry_after_seconds(_status_error(429, retry_after="1.5")) == 1.5
    assert retry_after_seconds(_status_error(429, retry_after="-1")) is None
    assert retry_after_seconds(_status_error(429, retry_after="soon")) is None


def test_redact_langfuse_message_removes_key_material() -> None:
    message = "authorization: sk-secret token=pk-public api-key=abc123"

    assert redact_langfuse_message(message) == (
        "authorization: [REDACTED] token=[REDACTED] api-key=[REDACTED]"
    )


def test_with_langfuse_retries_sleeps_then_succeeds() -> None:
    calls = 0
    sleeps: list[float] = []

    def callback() -> str:
        nonlocal calls
        calls += 1
        if calls == 1:
            raise _status_error(429, retry_after="0")
        return "ok"

    assert (
        with_langfuse_retries(
            "list score configs",
            callback,
            attempts=2,
            sleep=sleeps.append,
            default_delay=3.0,
        )
        == "ok"
    )
    assert sleeps == [3.0]


def test_with_langfuse_retries_raises_sanitized_langfuse_error() -> None:
    def callback() -> str:
        raise RuntimeError("HTTP 500 authorization: sk-secret")

    with pytest.raises(LangfuseError, match=r"\[REDACTED\]"):
        with_langfuse_retries(
            "sync",
            callback,
            attempts=1,
            sleep=lambda _delay: None,
            default_delay=0,
        )
