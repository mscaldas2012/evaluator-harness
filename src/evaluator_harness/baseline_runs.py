from __future__ import annotations

from dataclasses import dataclass
from uuid import uuid4

from evaluator_harness.baseline_registry import (
    BaselineFingerprint,
    fingerprint_metadata,
)
from evaluator_harness.config import BaselineReference, ProjectConfig
from evaluator_harness.langfuse_records import DatasetSyncResult
from evaluator_harness.run_context_common import (
    base_run_metadata,
    build_run_fingerprint,
)
from evaluator_harness.run_metadata import _utc_now


@dataclass(frozen=True)
class BaselineRunContext:
    fingerprint: BaselineFingerprint
    reference: BaselineReference
    run_id: str
    run_name: str
    created_at: str
    run_metadata: dict[str, object]


def build_baseline_run_context(
    *,
    config: ProjectConfig,
    dataset_sync: DatasetSyncResult,
) -> BaselineRunContext:
    run_id = f"baseline-{uuid4().hex[:12]}"
    run_name = f"{config.project.name}-{config.project.version}-{run_id}"
    created_at = _utc_now()
    fingerprint = build_run_fingerprint(config=config, dataset_sync=dataset_sync)
    reference = BaselineReference(
        baseline_run_id=run_id,
        langfuse_run_name=run_name,
        created_at=created_at,
        **fingerprint_metadata(fingerprint),
    )
    return BaselineRunContext(
        fingerprint=fingerprint,
        reference=reference,
        run_id=run_id,
        run_name=run_name,
        created_at=created_at,
        run_metadata={
            **base_run_metadata(config=config, fingerprint=fingerprint),
            "baseline_run_id": run_id,
            "created_at": created_at,
        },
    )
