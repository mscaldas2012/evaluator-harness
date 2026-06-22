from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from evaluator_harness.baseline_registry import (
    BaselineFingerprint,
    BaselineRegistry,
)
from evaluator_harness.config import (
    BaselineReference,
    ModelConfig,
    ProjectConfig,
)
from evaluator_harness.errors import ConfigError
from evaluator_harness.langfuse_gateways import LangfuseGateway
from evaluator_harness.langfuse_records import DatasetSyncResult
from evaluator_harness.run_context_common import (
    base_run_metadata,
    build_run_fingerprint,
)
from evaluator_harness.run_metadata import (
    _parameter_hash,
    generation_parameter_hash,
    parameter_identity,
    prompt_identity_for_model,
    variant_identity,
)


@dataclass(frozen=True)
class CandidateRunContext:
    candidate: ModelConfig
    fingerprint: BaselineFingerprint
    baseline_reference: BaselineReference
    baseline_run_id: str
    run_id: str
    run_name: str
    parameter_hash: str
    baseline_prompt_identity: dict[str, str]
    candidate_prompt_identity: dict[str, str]
    candidate_parameter_identity: dict[str, object]
    candidate_generation_parameter_hash: str
    candidate_variant_identity: dict[str, object]
    run_metadata: dict[str, object]


def build_candidate_run_context(
    *,
    config: ProjectConfig,
    dataset_sync: DatasetSyncResult,
    candidate_name: str,
    baseline_selector: str,
    langfuse_gateway: LangfuseGateway,
    baseline_registry: BaselineRegistry | None,
    warning_messages: tuple[str, ...],
) -> CandidateRunContext:
    candidate = candidate_by_name(config, candidate_name)
    fingerprint = build_run_fingerprint(config=config, dataset_sync=dataset_sync)
    try:
        baseline_reference = resolve_candidate_baseline_reference(
            baseline_selector=baseline_selector,
            fingerprint=fingerprint,
            langfuse_gateway=langfuse_gateway,
            baseline_registry=baseline_registry,
        )
    except ConfigError as exc:
        message = str(exc)
        if warning_messages:
            message = f"{message}. {warning_messages[0]}"
        raise ConfigError(message) from exc
    baseline_run_id = baseline_reference.baseline_run_id
    run_id = f"candidate-{uuid4().hex[:12]}"
    run_name = (
        f"{config.project.name}-{config.project.version}-{candidate.name}-{run_id}"
    )
    parameter_hash = _parameter_hash(candidate)
    baseline_prompt_identity = prompt_identity_for_model(config, config.baseline)
    candidate_prompt_identity = prompt_identity_for_model(config, candidate)
    candidate_parameter_identity = parameter_identity(candidate)
    candidate_generation_parameter_hash = generation_parameter_hash(candidate)
    candidate_variant_identity = variant_identity(config, candidate)
    return CandidateRunContext(
        candidate=candidate,
        fingerprint=fingerprint,
        baseline_reference=baseline_reference,
        baseline_run_id=baseline_run_id,
        run_id=run_id,
        run_name=run_name,
        parameter_hash=parameter_hash,
        baseline_prompt_identity=baseline_prompt_identity,
        candidate_prompt_identity=candidate_prompt_identity,
        candidate_parameter_identity=candidate_parameter_identity,
        candidate_generation_parameter_hash=candidate_generation_parameter_hash,
        candidate_variant_identity=candidate_variant_identity,
        run_metadata={
            **base_run_metadata(config=config, fingerprint=fingerprint),
            "candidate": candidate.name,
            "parameter_hash": parameter_hash,
            "parameter_identity": candidate_parameter_identity,
            "generation_parameter_hash": candidate_generation_parameter_hash,
            "variant_identity": candidate_variant_identity,
            "prompt_identity": candidate_prompt_identity,
            "baseline_prompt_identity": baseline_prompt_identity,
            "candidate_prompt_identity": candidate_prompt_identity,
        },
    )


def resolve_candidate_baseline_reference(
    *,
    baseline_selector: str,
    fingerprint: BaselineFingerprint,
    langfuse_gateway: LangfuseGateway,
    baseline_registry: BaselineRegistry | None,
) -> BaselineReference:
    baseline_reference = langfuse_gateway.lookup_baseline(
        selector=baseline_selector,
        fingerprint=fingerprint,
    )
    if baseline_reference is not None:
        return baseline_reference
    if baseline_registry is not None:
        try:
            baseline_run_id = baseline_registry.resolve(baseline_selector, fingerprint)
        except ConfigError:
            baseline_run_id = ""
        else:
            baseline_reference = baseline_registry.reference_for(
                baseline_run_id
            ) or langfuse_gateway.baseline_references.get(baseline_run_id)
            if baseline_reference is not None:
                return baseline_reference
    raise ConfigError(f"No baseline reference found for {baseline_selector}")


def candidate_by_name(config: ProjectConfig, candidate_name: str) -> ModelConfig:
    for candidate in config.candidates:
        if candidate.name == candidate_name:
            return candidate
    raise ConfigError(f"Candidate model config not found: {candidate_name}")
