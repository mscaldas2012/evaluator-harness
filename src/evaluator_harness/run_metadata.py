from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from evaluator_harness.baseline_registry import (
    BaselineFingerprint,
    fingerprint_metadata,
)
from evaluator_harness.config import (
    BaselineReference,
    DatasetItem,
    ModelConfig,
    ProjectConfig,
    scenario_metadata,
)
from evaluator_harness.langfuse_records import DatasetSyncResult
from evaluator_harness.model_output_targeting import MODEL_OUTPUT_ROLE
from evaluator_harness.prompt_sync import prompt_provenance_metadata
from evaluator_harness.prompts import RenderedPrompt
from evaluator_harness.prompts import (
    prompt_identity as prompt_file_identity,
)
from evaluator_harness.providers import provider_tracing_metadata
from evaluator_harness.session_identity import SessionIdentityInputs


def build_trace_payload(
    *,
    config: ProjectConfig,
    item: DatasetItem,
    run_id: str,
    trace_id: str,
    trace_name: str,
    response: Any | None,
    prompt: str,
    retry_count: int,
    error: str | None,
    model_config: ModelConfig | None = None,
    dataset_sync: DatasetSyncResult | None = None,
    fingerprint: BaselineFingerprint | None = None,
    baseline_reference: BaselineReference | None = None,
    parameter_hash: str | None = None,
    rendered_prompt: RenderedPrompt | None = None,
    observation_role: str = MODEL_OUTPUT_ROLE,
    session_id: str | None = None,
    session_inputs: SessionIdentityInputs | None = None,
) -> dict[str, Any]:
    active_model = model_config or config.baseline
    active_prompt_identity = prompt_identity_for_model(config, active_model)
    prompt_ref = active_model.task_prompt or config.task_prompt
    baseline_prompt_identity = prompt_identity_for_model(config, config.baseline)
    candidate_prompt_identity = (
        active_prompt_identity if baseline_reference is not None else None
    )
    metadata = {
        **(fingerprint_metadata(fingerprint) if fingerprint else {}),
        **trace_project_metadata(config, run_id, active_model, baseline_reference),
        **trace_dataset_metadata(dataset_sync, item, run_id),
        **trace_session_metadata(session_id, session_inputs, observation_role),
        **trace_prompt_metadata(
            config=config,
            prompt_ref=prompt_ref,
            active_prompt_identity=active_prompt_identity,
            baseline_prompt_identity=baseline_prompt_identity,
            candidate_prompt_identity=candidate_prompt_identity,
        ),
        **trace_model_metadata(
            config=config,
            active_model=active_model,
            fingerprint=fingerprint,
            baseline_reference=baseline_reference,
            parameter_hash=parameter_hash,
        ),
        **trace_response_metadata(response, retry_count),
    }
    return {
        "trace_id": trace_id,
        "run_id": run_id,
        "session_id": session_id,
        "name": trace_name,
        "input": item.input,
        "output": response.output if response is not None else None,
        "error": error,
        "metadata": {**metadata, "trace_id": trace_id, "trace_name": trace_name},
        "prompt": prompt,
        "rendered_prompt": (
            rendered_prompt.model_dump(mode="json") if rendered_prompt else None
        ),
        "timestamp": _utc_now(),
    }


def trace_project_metadata(
    config: ProjectConfig,
    run_id: str,
    active_model: ModelConfig,
    baseline_reference: BaselineReference | None,
) -> dict[str, Any]:
    return {
        "project": config.project.name,
        "project_version": config.project.version,
        **scenario_metadata(config),
        "run_type": "candidate" if baseline_reference is not None else "baseline",
        "test_trace": _is_test_run(),
        "environment": config.project.metadata.get("environment"),
        "project_tags": config.project.metadata.get("tags", []),
        "run_tags": [config.project.name, run_id, active_model.name],
    }


def trace_dataset_metadata(
    dataset_sync: DatasetSyncResult | None,
    item: DatasetItem,
    run_id: str,
) -> dict[str, Any]:
    if dataset_sync is None:
        return {
            "dataset_name": None,
            "dataset_version": None,
            "dataset_compatibility_version": None,
            "dataset_item_id": item.item_id,
            "ground_truth": item.ground_truth,
            "langfuse_dataset_item_id": None,
            "dataset_run_item_id": None,
        }
    return {
        "dataset_name": dataset_sync.name,
        "dataset_version": dataset_sync.version,
        "dataset_compatibility_version": dataset_sync.compatibility_version,
        "dataset_item_id": item.item_id,
        "ground_truth": item.ground_truth,
        "langfuse_dataset_item_id": f"{dataset_sync.name}:{item.item_id}",
        "dataset_run_item_id": f"{run_id}:{item.item_id}",
    }


def trace_session_metadata(
    session_id: str | None,
    session_inputs: SessionIdentityInputs | None,
    observation_role: str,
) -> dict[str, Any]:
    return {
        "item_comparison_session_id": session_id,
        "item_comparison_session_inputs": (
            session_inputs.metadata() if session_inputs is not None else None
        ),
        "observation_role": observation_role,
    }


def trace_prompt_metadata(
    *,
    config: ProjectConfig,
    prompt_ref: Any,
    active_prompt_identity: dict[str, Any],
    baseline_prompt_identity: dict[str, Any],
    candidate_prompt_identity: dict[str, Any] | None,
) -> dict[str, Any]:
    candidate_prompt_version = (
        candidate_prompt_identity["version"]
        if candidate_prompt_identity is not None
        else None
    )
    return {
        "prompt_version": active_prompt_identity["version"],
        "prompt_shape": active_prompt_identity.get("shape"),
        "prompt_roles": active_prompt_identity.get("roles", []),
        **prompt_provenance_metadata(
            config,
            artifact_type="task",
            artifact_name="task_prompt",
            prompt_ref=prompt_ref,
        ),
        "prompt_identity": active_prompt_identity,
        "baseline_prompt_version": baseline_prompt_identity["version"],
        "baseline_prompt_identity": baseline_prompt_identity,
        "candidate_prompt_version": candidate_prompt_version,
        "candidate_prompt_identity": candidate_prompt_identity,
    }


def trace_model_metadata(
    *,
    config: ProjectConfig,
    active_model: ModelConfig,
    fingerprint: BaselineFingerprint | None,
    baseline_reference: BaselineReference | None,
    parameter_hash: str | None,
) -> dict[str, Any]:
    return {
        "evaluator_set_id": fingerprint.evaluator_set_id if fingerprint else None,
        "provider": active_model.provider.value,
        "model": active_model.model,
        "model_name": active_model.name,
        "temperature": active_model.parameters.temperature,
        "parameter_hash": parameter_hash or _parameter_hash(active_model),
        "parameter_identity": parameter_identity(active_model),
        "generation_parameter_hash": generation_parameter_hash(active_model),
        "variant_identity": variant_identity(config, active_model),
        "baseline_reference": baseline_reference_metadata(baseline_reference),
        "provider_tracing_strategy": provider_tracing_metadata(active_model),
    }


def baseline_reference_metadata(
    baseline_reference: BaselineReference | None,
) -> dict[str, Any] | None:
    if baseline_reference is None:
        return None
    return baseline_reference.model_dump(mode="json")


def trace_response_metadata(
    response: Any | None,
    retry_count: int,
) -> dict[str, Any]:
    if response is None:
        return {
            "retry_count": retry_count,
            "latency_ms": None,
            "input_tokens": None,
            "output_tokens": None,
            "cost_usd": None,
            "tracing_strategy": None,
            "manual_fallback_reason": None,
        }
    return {
        "retry_count": retry_count,
        "latency_ms": response.latency_ms,
        "input_tokens": response.input_tokens,
        "output_tokens": response.output_tokens,
        "cost_usd": response.cost_usd,
        "tracing_strategy": response.raw.get("tracing_strategy"),
        "manual_fallback_reason": response.raw.get("manual_fallback_reason"),
    }


def build_request_metadata(
    *,
    config: ProjectConfig,
    model_config: ModelConfig,
    item: DatasetItem,
    run_id: str,
    run_type: str,
    trace_id: str,
    trace_name: str,
    dataset_sync: DatasetSyncResult,
    fingerprint: BaselineFingerprint,
    rendered_prompt: RenderedPrompt | None = None,
    session_id: str | None = None,
    session_inputs: SessionIdentityInputs | None = None,
) -> dict[str, Any]:
    active_prompt_identity = prompt_identity_for_model(config, model_config)
    prompt_ref = model_config.task_prompt or config.task_prompt
    baseline_prompt_identity = prompt_identity_for_model(config, config.baseline)
    candidate_prompt_identity = (
        active_prompt_identity if run_type == "candidate" else None
    )
    return {
        "project": config.project.name,
        "project_version": config.project.version,
        **scenario_metadata(config),
        "run_id": run_id,
        "run_type": run_type,
        "item_id": item.item_id,
        "dataset_item_id": item.item_id,
        "dataset_name": dataset_sync.name,
        "dataset_version": dataset_sync.version,
        "dataset_compatibility_version": dataset_sync.compatibility_version,
        "evaluator_set_id": fingerprint.evaluator_set_id,
        "trace_id": trace_id,
        "trace_name": trace_name,
        "item_comparison_session_id": session_id,
        "item_comparison_session_inputs": (
            session_inputs.metadata() if session_inputs is not None else None
        ),
        "prompt_version": active_prompt_identity["version"],
        "prompt_shape": active_prompt_identity.get("shape"),
        "prompt_roles": active_prompt_identity.get("roles", []),
        **prompt_provenance_metadata(
            config,
            artifact_type="task",
            artifact_name="task_prompt",
            prompt_ref=prompt_ref,
        ),
        "prompt_identity": active_prompt_identity,
        "baseline_prompt_version": baseline_prompt_identity["version"],
        "baseline_prompt_identity": baseline_prompt_identity,
        "candidate_prompt_version": (
            candidate_prompt_identity["version"]
            if candidate_prompt_identity is not None
            else None
        ),
        "candidate_prompt_identity": candidate_prompt_identity,
        "parameter_identity": parameter_identity(model_config),
        "generation_parameter_hash": generation_parameter_hash(model_config),
        "variant_identity": variant_identity(config, model_config),
        "observation_role": MODEL_OUTPUT_ROLE,
        "rendered_prompt": (
            rendered_prompt.model_dump(mode="json") if rendered_prompt else None
        ),
    }


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _parameter_hash(config: ModelConfig) -> str:
    payload = {
        "provider": config.provider.value,
        "model": config.model,
        "parameters": config.parameters.model_dump(mode="json", exclude_none=True),
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    ).hexdigest()


def model_identity(config: ModelConfig) -> dict[str, str]:
    return {
        "provider": config.provider.value,
        "auth_mode": config.auth_mode.value,
        "model": config.model,
    }


def prompt_identity(prompt_ref: Any) -> dict[str, Any]:
    return prompt_file_identity(Path(prompt_ref.path), prompt_ref.version)


def prompt_identity_for_model(
    config: ProjectConfig,
    model_config: ModelConfig,
) -> dict[str, str]:
    prompt_ref = model_config.task_prompt or config.task_prompt
    return prompt_identity(prompt_ref)


def generation_parameter_hash(config: ModelConfig) -> str:
    payload = config.parameters.model_dump(mode="json", exclude_none=True)
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True).encode("utf-8")
    ).hexdigest()


def parameter_identity(config: ModelConfig) -> dict[str, Any]:
    return config.parameters.model_dump(mode="json", exclude_none=True)


def variant_identity(
    config: ProjectConfig,
    model_config: ModelConfig,
) -> dict[str, Any]:
    return {
        "candidate": model_config.name,
        "model": model_identity(model_config),
        "prompt": prompt_identity_for_model(config, model_config),
        "parameters": model_config.parameters.model_dump(
            mode="json", exclude_none=True
        ),
        "generation_parameter_hash": generation_parameter_hash(model_config),
    }


def _is_test_run() -> bool:
    return bool(os.getenv("PYTEST_CURRENT_TEST"))
