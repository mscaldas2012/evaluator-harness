from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal

from evaluator_harness.langfuse_retry import redact_langfuse_message

JsonDict = dict[str, Any]
LangfuseOutcomeStatus = Literal[
    "success",
    "expected_not_found",
    "partial_success",
    "failure",
]
LangfuseOutcomeSeverity = Literal["info", "warning", "error"]


@dataclass(frozen=True)
class DatasetRecord:
    id: str
    name: str
    version: str | None = None
    metadata: JsonDict = field(default_factory=dict)


@dataclass(frozen=True)
class DatasetSyncResult:
    name: str
    version: str
    compatibility_version: str
    item_count: int
    status: str
    rejected_count: int = 0


@dataclass(frozen=True)
class DatasetItemRecord:
    id: str
    dataset_name: str
    item_id: str | None = None
    input: Any = None
    expected_output: Any = None
    metadata: JsonDict = field(default_factory=dict)


@dataclass(frozen=True)
class RunRecord:
    id: str
    name: str
    dataset_name: str | None = None
    metadata: JsonDict = field(default_factory=dict)
    created_at: datetime | None = None


@dataclass(frozen=True)
class TraceRecord:
    id: str
    run_id: str
    name: str | None = None
    input: Any = None
    output: Any = None
    error: Any = None
    metadata: JsonDict = field(default_factory=dict)
    timestamp: str = ""


@dataclass(frozen=True)
class ScoreRecord:
    id: str | None = None
    name: str | None = None
    value: Any = None
    trace_id: str | None = None
    observation_id: str | None = None
    dataset_run_id: str | None = None
    comment: str | None = None
    source: str | None = None
    metadata: JsonDict = field(default_factory=dict)


@dataclass(frozen=True)
class ScoreConfigRecord:
    id: str | None
    name: str
    data_type: str | None = None
    min_value: float | int | None = None
    max_value: float | int | None = None
    categories: list[str] | None = None
    description: str | None = None
    archived: bool = False
    metadata: JsonDict = field(default_factory=dict)


@dataclass(frozen=True)
class ScoreConfigSyncResult:
    evaluator_name: str
    name: str
    score_config_id: str
    status: str
    ownership: str


@dataclass(frozen=True)
class PromptRecord:
    name: str
    version: int | None = None
    prompt: Any = None
    type: str | None = None
    config: JsonDict = field(default_factory=dict)
    labels: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    commit_message: str | None = None


@dataclass(frozen=True)
class EvaluatorRecord:
    id: str | None
    name: str
    display_name: str | None = None
    active: bool | None = None
    filters: JsonDict = field(default_factory=dict)
    variables: dict[str, str] = field(default_factory=dict)
    score_config_id: str | None = None
    sampling_percent: int | None = None
    target: str | None = None
    metadata: JsonDict = field(default_factory=dict)


@dataclass(frozen=True)
class AnnotationQueueRecord:
    id: str
    name: str | None = None
    description: str | None = None
    score_config_ids: list[str] = field(default_factory=list)
    object_id: str | None = None
    object_type: str | None = None
    status: str | None = None
    metadata: JsonDict = field(default_factory=dict)


@dataclass(frozen=True)
class AnnotationRoutingResult:
    queue_id: str
    queued_count: int
    skipped_duplicate_count: int


@dataclass(frozen=True)
class OperationFailure:
    operation: str
    message: str
    exception_type: str | None = None
    retryable: bool = False
    context: JsonDict = field(default_factory=dict)


@dataclass(frozen=True)
class LangfuseOperationOutcome:
    operation: str
    status: LangfuseOutcomeStatus
    severity: LangfuseOutcomeSeverity
    message: str
    affected_count: int = 1
    examples: tuple[str, ...] = ()
    details: JsonDict = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_non_empty_string(self.operation, field_name="operation")
        require_non_empty_string(self.message, field_name="message")
        if self.affected_count < 0:
            raise ValueError("affected_count must be non-negative")
        if self.status in {"partial_success", "failure"} and self.severity == "info":
            raise ValueError(
                "partial_success and failure outcomes require warning or error severity"
            )
        if self.status == "expected_not_found" and self.severity != "info":
            raise ValueError("expected_not_found outcomes must use info severity")
        object.__setattr__(self, "examples", bounded_examples(self.examples))
        object.__setattr__(self, "details", redact_details(self.details))


@dataclass(frozen=True)
class LangfuseWarning:
    code: str
    operation: str
    message: str
    severity: LangfuseOutcomeSeverity = "warning"
    affected_count: int = 1
    examples: tuple[str, ...] = ()
    details: JsonDict = field(default_factory=dict)

    def __post_init__(self) -> None:
        require_non_empty_string(self.code, field_name="code")
        require_non_empty_string(self.operation, field_name="operation")
        require_non_empty_string(self.message, field_name="message")
        if self.severity == "info":
            raise ValueError("warnings require warning or error severity")
        if self.affected_count < 1:
            raise ValueError("affected_count must be positive")
        object.__setattr__(self, "examples", bounded_examples(self.examples))
        object.__setattr__(self, "details", redact_details(self.details))


def require_non_empty_string(value: Any, *, field_name: str) -> str:
    if value is None:
        raise ValueError(f"{field_name} is required")
    text = str(value)
    if not text:
        raise ValueError(f"{field_name} is required")
    return text


def safe_metadata(value: Any) -> JsonDict:
    return dict(value) if isinstance(value, dict) else {}


def bounded_examples(
    examples: Sequence[Any],
    *,
    max_examples: int = 3,
) -> tuple[str, ...]:
    bounded: list[str] = []
    for example in examples:
        text = redact_langfuse_message(str(example))
        if text and text not in bounded:
            bounded.append(text)
        if len(bounded) >= max_examples:
            break
    return tuple(bounded)


def redact_details(value: Mapping[str, Any] | None) -> JsonDict:
    if value is None:
        return {}
    redacted: JsonDict = {}
    for key, item in value.items():
        text_key = str(key)
        if isinstance(item, Mapping):
            redacted[text_key] = redact_details(item)
        elif isinstance(item, list | tuple):
            redacted[text_key] = [redact_langfuse_message(str(entry)) for entry in item]
        elif item is None or isinstance(item, bool | int | float):
            redacted[text_key] = item
        else:
            redacted[text_key] = redact_langfuse_message(str(item))
    return redacted


def warning_from_outcome(
    outcome: LangfuseOperationOutcome,
    *,
    code: str | None = None,
) -> LangfuseWarning | None:
    if outcome.severity == "info" or outcome.status in {
        "success",
        "expected_not_found",
    }:
        return None
    return LangfuseWarning(
        code=code or outcome.operation,
        operation=outcome.operation,
        message=outcome.message,
        severity=outcome.severity,
        affected_count=max(1, outcome.affected_count),
        examples=outcome.examples,
        details=outcome.details,
    )


def aggregate_langfuse_warnings(
    warnings: Sequence[LangfuseWarning],
    *,
    max_examples: int = 3,
) -> tuple[LangfuseWarning, ...]:
    grouped: dict[tuple[str, str, str, LangfuseOutcomeSeverity], LangfuseWarning] = {}
    for warning in warnings:
        key = (warning.code, warning.operation, warning.message, warning.severity)
        existing = grouped.get(key)
        if existing is None:
            grouped[key] = warning
            continue
        grouped[key] = LangfuseWarning(
            code=existing.code,
            operation=existing.operation,
            message=existing.message,
            severity=existing.severity,
            affected_count=existing.affected_count + warning.affected_count,
            examples=bounded_examples(
                (*existing.examples, *warning.examples),
                max_examples=max_examples,
            ),
            details={**existing.details, **warning.details},
        )
    return tuple(grouped.values())


def format_langfuse_warning(warning: LangfuseWarning) -> str:
    suffix = ""
    if warning.examples:
        suffix = f" examples: {', '.join(warning.examples)}"
    return (
        f"{warning.message} "
        f"(operation={warning.operation}, affected={warning.affected_count}){suffix}"
    )
