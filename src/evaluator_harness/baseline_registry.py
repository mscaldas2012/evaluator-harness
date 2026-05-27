from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, asdict, replace
from typing import Any

from evaluator_harness.config import BaselineReference, ProjectConfig
from evaluator_harness.errors import ConfigError


@dataclass(frozen=True)
class BaselineFingerprint:
    project_name: str
    project_version: str
    dataset_name: str
    dataset_version: str
    prompt_version: str
    evaluator_set_id: str
    baseline_model: str
    baseline_parameters_hash: str

    def model_copy(self, *, update: dict[str, Any] | None = None) -> BaselineFingerprint:
        return replace(self, **(update or {}))


class BaselineRegistry:
    def __init__(self) -> None:
        self._records: dict[str, BaselineFingerprint] = {}
        self._references: dict[str, BaselineReference] = {}

    def record(
        self,
        baseline_run_id: str,
        fingerprint: BaselineFingerprint,
        reference: BaselineReference | None = None,
    ) -> None:
        self._records[baseline_run_id] = fingerprint
        if reference is not None:
            self._references[baseline_run_id] = reference

    def resolve_latest_compatible(self, fingerprint: BaselineFingerprint) -> str:
        for run_id, recorded in reversed(self._records.items()):
            if recorded == fingerprint:
                return run_id
        raise ConfigError("No compatible baseline found")

    def resolve(self, baseline: str, fingerprint: BaselineFingerprint) -> str:
        if baseline == "latest-compatible":
            return self.resolve_latest_compatible(fingerprint)

        recorded = self._records.get(baseline)
        if recorded != fingerprint:
            raise ConfigError(f"No compatible baseline found for {baseline}")
        return baseline

    def reference_for(self, baseline_run_id: str) -> BaselineReference | None:
        return self._references.get(baseline_run_id)


def build_baseline_fingerprint(
    config: ProjectConfig,
    *,
    dataset_name: str,
    dataset_version: str,
) -> BaselineFingerprint:
    evaluator_set_id = ",".join(
        f"{evaluator.name}:{evaluator.version}" for evaluator in config.evaluators
    )
    params = config.baseline.parameters.model_dump(mode="json", exclude_none=True)
    params_hash = hashlib.sha256(
        json.dumps(params, sort_keys=True).encode("utf-8")
    ).hexdigest()
    return BaselineFingerprint(
        project_name=config.project.name,
        project_version=config.project.version,
        dataset_name=dataset_name,
        dataset_version=dataset_version,
        prompt_version=config.task_prompt.version,
        evaluator_set_id=evaluator_set_id,
        baseline_model=config.baseline.model,
        baseline_parameters_hash=params_hash,
    )


def fingerprint_metadata(fingerprint: BaselineFingerprint) -> dict[str, str]:
    return asdict(fingerprint)
