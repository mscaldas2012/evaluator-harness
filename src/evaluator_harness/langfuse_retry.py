from __future__ import annotations

import os
import re
from collections.abc import Callable
from typing import Any, TypeVar

import httpx

from evaluator_harness.errors import LangfuseError

RETRYABLE_LANGFUSE_STATUS_CODES = {408, 409, 425, 429, 500, 502, 503, 504}
_SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9._-]+"),
    re.compile(r"pk-[A-Za-z0-9._-]+"),
)
_SECRET_WORDS = ("authorization", "secret", "token", "api-key", "apikey")
T = TypeVar("T")


def is_retryable_langfuse_error(exc: Exception) -> bool:
    if isinstance(exc, httpx.HTTPStatusError):
        return exc.response.status_code in RETRYABLE_LANGFUSE_STATUS_CODES
    if isinstance(exc, httpx.TransportError):
        return True
    text = str(exc).lower()
    retry_markers = [
        "429",
        "408",
        "409",
        "425",
        "500",
        "502",
        "503",
        "504",
        "rate limit",
        "too many requests",
        "temporarily unavailable",
        "timeout",
        "timed out",
    ]
    return any(marker in text for marker in retry_markers)


def retry_after_seconds(exc: Exception) -> float | None:
    if not isinstance(exc, httpx.HTTPStatusError):
        return None
    retry_after = exc.response.headers.get("Retry-After")
    if not retry_after:
        return None
    try:
        delay = float(retry_after)
    except ValueError:
        return None
    return delay if delay >= 0 else None


def positive_int_env(name: str, *, default: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        return default
    return value if value > 0 else default


def positive_float_env(name: str, *, default: float) -> float:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = float(raw)
    except ValueError:
        return default
    return value if value >= 0 else default


def langfuse_retry_attempts() -> int:
    return positive_int_env("EVALUATOR_HARNESS_LANGFUSE_RETRY_ATTEMPTS", default=5)


def langfuse_retry_initial_delay() -> float:
    return positive_float_env(
        "EVALUATOR_HARNESS_LANGFUSE_RETRY_INITIAL_DELAY",
        default=1.0,
    )


def langfuse_retry_max_delay() -> float:
    return positive_float_env(
        "EVALUATOR_HARNESS_LANGFUSE_RETRY_MAX_DELAY",
        default=15.0,
    )


def redact_langfuse_message(message: str) -> str:
    redacted = message
    for pattern in _SECRET_PATTERNS:
        redacted = pattern.sub("[REDACTED]", redacted)
    redacted = re.sub(
        r"(authorization['\"\s:=]+)(bearer\s+)?[^,\s}]+",
        r"\1[REDACTED]",
        redacted,
        flags=re.IGNORECASE,
    )
    for word in _SECRET_WORDS:
        redacted = re.sub(
            rf"({re.escape(word)}['\"\s:=]+)([^,\s}}]+)",
            r"\1[REDACTED]",
            redacted,
            flags=re.IGNORECASE,
        )
    return redacted


def with_langfuse_retries(
    operation: str,
    callback: Callable[[], T],
    *,
    attempts: int,
    sleep: Callable[[float], object],
    default_delay: float,
) -> T:
    for attempt in range(1, attempts + 1):
        try:
            return callback()
        except Exception as exc:
            if attempt >= attempts or not is_retryable_langfuse_error(exc):
                message = redact_langfuse_message(str(exc))
                raise LangfuseError(
                    f"Unable to execute Langfuse operation: {operation}: {message}"
                ) from exc
            sleep(retry_after_seconds(exc) or default_delay)
    raise LangfuseError(f"Unable to execute Langfuse operation: {operation}")


def with_logged_langfuse_retries(
    owner: Any,
    *,
    operation: str,
    callback: Callable[[], T],
) -> T:
    attempts = langfuse_retry_attempts()
    initial_delay = langfuse_retry_initial_delay()
    max_delay = langfuse_retry_max_delay()
    last_exc: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return callback()
        except Exception as exc:
            last_exc = exc
            if attempt >= attempts or not is_retryable_langfuse_error(exc):
                raise
            delay = retry_after_seconds(exc)
            if delay is None:
                delay = min(max_delay, initial_delay * (2 ** (attempt - 1)))
            owner.calls.append(
                (
                    "langfuse_retry",
                    {
                        "operation": operation,
                        "attempt": attempt,
                        "next_attempt": attempt + 1,
                        "delay_seconds": delay,
                        "error": str(exc),
                    },
                )
            )
            owner.retry_sleep(delay)
    if last_exc is not None:
        raise last_exc
    raise LangfuseError(f"Unable to execute Langfuse operation: {operation}")
