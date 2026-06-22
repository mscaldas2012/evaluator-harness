from __future__ import annotations

from evaluator_harness.baseline_registry import (
    BaselineFingerprint,
    build_baseline_fingerprint,
    fingerprint_metadata,
)
from evaluator_harness.config import ProjectConfig, scenario_metadata
from evaluator_harness.langfuse_records import DatasetSyncResult


def build_run_fingerprint(
    *,
    config: ProjectConfig,
    dataset_sync: DatasetSyncResult,
) -> BaselineFingerprint:
    return build_baseline_fingerprint(
        config,
        dataset_name=dataset_sync.name,
        dataset_version=dataset_sync.compatibility_version,
    )


def base_run_metadata(
    *,
    config: ProjectConfig,
    fingerprint: BaselineFingerprint,
) -> dict[str, object]:
    return {
        **fingerprint_metadata(fingerprint),
        **scenario_metadata(config),
    }
