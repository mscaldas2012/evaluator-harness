from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from evaluator_harness.baseline_registry import BaselineFingerprint
from evaluator_harness.config import BaselineReference, DatasetItem, ModelConfig
from evaluator_harness.langfuse_evaluator_setup import EvaluatorSetupResult
from evaluator_harness.langfuse_records import DatasetSyncResult, ScoreConfigSyncResult
from evaluator_harness.prompt_sync import PromptSyncReport
from evaluator_harness.prompts import RenderedPrompt
from evaluator_harness.providers.base import ModelProvider, ModelResponse
from evaluator_harness.review_routing import ReviewSelectionResult
from evaluator_harness.annotation_queues import AnnotationQueueSyncResult


@dataclass(frozen=True)
class ValidationResult:
    project_name: str
    project_version: str
    dataset_kind: str
    item_count: int
    baseline_name: str
    candidate_names: list[str]
    evaluator_names: list[str]
    evaluator_targets: list[str]
    score_targets: list[str]
    judge_setup_status: str = "ready"
    judge_default: str | None = None
    binding_path: str | None = None


@dataclass(frozen=True)
class RunResult:
    run_id: str
    run_type: str
    completed_count: int
    failed_count: int
    baseline_reference: BaselineReference | None = None
    review_selection: ReviewSelectionResult | None = None
    model_output_targeting_status: str | None = None
    model_output_targeting_message: str | None = None
    langfuse_status: str = "complete"
    langfuse_warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class RunItemExecutionPlan:
    """Run-type context supplied to the shared per-item executor."""

    run_id: str
    run_type: str
    model_config: ModelConfig
    provider: ModelProvider
    prompt_ref: Any
    dataset_sync: DatasetSyncResult
    fingerprint: BaselineFingerprint
    baseline_anchor: str
    baseline_reference: BaselineReference | None = None
    parameter_hash: str | None = None
    request_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RunItemExecutionResult:
    """Evidence and outcome produced by executing one dataset item."""

    item: DatasetItem
    trace_id: str
    trace_name: str
    session_id: str
    rendered_prompt: RenderedPrompt
    response: ModelResponse | None
    error: str | None
    retry_count: int
    trace: dict[str, Any]
    completed: bool
    failed: bool
    dataset_run_item_recorded: bool


@dataclass(frozen=True)
class SyncAllResult:
    dataset: DatasetSyncResult
    prompts: PromptSyncReport
    score_configs: list[ScoreConfigSyncResult]
    judge_evaluators: EvaluatorSetupResult
    annotation_queue: AnnotationQueueSyncResult
