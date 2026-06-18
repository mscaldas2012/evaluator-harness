from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Any, Literal
from collections.abc import Iterable, Mapping


MODEL_OUTPUT_ROLE = "model_output"
RUN_ITEM_ROLE = "run_item"

TargetingStatus = Literal["aligned", "missing", "duplicate", "provider_specific", "unknown"]


@dataclass(frozen=True)
class ModelOutputTargetingDiagnostic:
    status: TargetingStatus
    model_output_count: int
    expected_completed_count: int | None
    message: str


def parent_observation_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    return {**metadata, "observation_role": RUN_ITEM_ROLE}


def final_output_metadata(metadata: Mapping[str, Any]) -> dict[str, Any]:
    return {**metadata, "observation_role": MODEL_OUTPUT_ROLE}


def metadata_with_observation_role(
    metadata: Mapping[str, Any],
    observation_role: str,
) -> dict[str, Any]:
    return {**metadata, "observation_role": observation_role}


def model_output_observations(
    observations: Iterable[Mapping[str, Any]],
) -> list[Mapping[str, Any]]:
    return [
        observation
        for observation in observations
        if (observation.get("metadata") or {}).get("observation_role")
        == MODEL_OUTPUT_ROLE
    ]


def diagnose_model_output_targeting(
    observations: Iterable[Mapping[str, Any]],
    *,
    expected_completed_count: int | None = None,
) -> ModelOutputTargetingDiagnostic:
    observation_list = list(observations)
    eligible = model_output_observations(observation_list)
    model_output_count = len(eligible)
    expected = expected_completed_count
    trace_counts = Counter(
        str(observation.get("trace_id") or (observation.get("metadata") or {}).get("trace_id"))
        for observation in eligible
    )
    duplicate_trace_ids = sorted(
        trace_id
        for trace_id, count in trace_counts.items()
        if trace_id and trace_id != "None" and count > 1
    )
    if duplicate_trace_ids:
        return ModelOutputTargetingDiagnostic(
            status="duplicate",
            model_output_count=model_output_count,
            expected_completed_count=expected,
            message=(
                "Duplicate model-output observations found for trace(s): "
                + ", ".join(duplicate_trace_ids)
                + ". Ensure parent/container spans use observation_role=run_item."
            ),
        )
    if expected is not None and model_output_count == expected:
        return ModelOutputTargetingDiagnostic(
            status="aligned",
            model_output_count=model_output_count,
            expected_completed_count=expected,
            message=f"{model_output_count} model-output observations aligned with completed items.",
        )
    if model_output_count == 0 and _has_provider_specific_candidates(observation_list):
        return ModelOutputTargetingDiagnostic(
            status="provider_specific",
            model_output_count=model_output_count,
            expected_completed_count=expected,
            message=(
                "No standard model-output observations were found, but provider-specific "
                "observations exist. Configure the provider to emit observation_role=model_output "
                "on exactly one final output or set an explicit target_observation_name."
            ),
        )
    if expected is not None and model_output_count != expected:
        return ModelOutputTargetingDiagnostic(
            status="missing",
            model_output_count=model_output_count,
            expected_completed_count=expected,
            message=(
                f"{model_output_count} model-output observations found for {expected} "
                "completed items. Ensure each successful item has exactly one final output "
                "observation."
            ),
        )
    return ModelOutputTargetingDiagnostic(
        status="unknown",
        model_output_count=model_output_count,
        expected_completed_count=expected,
        message=(
            f"{model_output_count} model-output observations found. Provide an expected "
            "completed item count to verify alignment."
        ),
    )


def _has_provider_specific_candidates(observations: list[Mapping[str, Any]]) -> bool:
    for observation in observations:
        metadata = observation.get("metadata") or {}
        role = metadata.get("observation_role")
        if role and role not in {MODEL_OUTPUT_ROLE, RUN_ITEM_ROLE}:
            return True
        name = str(observation.get("name") or "")
        if "provider" in name.lower():
            return True
    return False
