from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

JsonDict = dict[str, Any]


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


def require_non_empty_string(value: Any, *, field_name: str) -> str:
    if value is None:
        raise ValueError(f"{field_name} is required")
    text = str(value)
    if not text:
        raise ValueError(f"{field_name} is required")
    return text


def safe_metadata(value: Any) -> JsonDict:
    return dict(value) if isinstance(value, dict) else {}
