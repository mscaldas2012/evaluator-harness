from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from evaluator_harness.errors import ConfigError


SECRET_FIELD_MARKERS = ("secret", "api_key", "token", "password", "credential")


class EvaluatorBindingRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project: str
    project_version: str
    evaluator_name: str
    evaluator_version: str
    source_type: str
    target: str
    langfuse_evaluator_id: str
    langfuse_display_name: str
    score_config_id: str
    score_config_name: str
    judge_model: str | None = None
    llm_connection: str | None = None
    sampling_percent: int = 100
    historical_backfill: bool = False
    active: bool = True
    last_synced_at: str

    @property
    def key(self) -> tuple[str, str, str, str, str, str]:
        return (
            self.project,
            self.project_version,
            self.evaluator_name,
            self.evaluator_version,
            self.source_type,
            self.target,
        )


class EvaluatorBindingStore(BaseModel):
    bindings: list[EvaluatorBindingRecord] = Field(default_factory=list)

    def find(
        self,
        *,
        project: str,
        project_version: str,
        evaluator_name: str,
        evaluator_version: str,
        source_type: str,
        target: str,
    ) -> EvaluatorBindingRecord | None:
        key = (
            project,
            project_version,
            evaluator_name,
            evaluator_version,
            source_type,
            target,
        )
        for binding in self.bindings:
            if binding.key == key:
                return binding
        return None

    def find_by_display_name(self, display_name: str) -> EvaluatorBindingRecord | None:
        for binding in self.bindings:
            if binding.langfuse_display_name == display_name:
                return binding
        return None

    def upsert(self, record: EvaluatorBindingRecord) -> None:
        self.bindings = [
            existing for existing in self.bindings if existing.key != record.key
        ]
        self.bindings.append(record)


def validate_binding_path(path: Path | str, *, repo_root: Path | None = None) -> Path:
    root = (repo_root or Path.cwd()).resolve()
    candidate = Path(path)
    resolved = (root / candidate).resolve() if not candidate.is_absolute() else candidate.resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ConfigError(f"Evaluator binding path must be repo-local: {path}") from exc
    return resolved


def load_evaluator_bindings(path: Path | str) -> EvaluatorBindingStore:
    binding_path = Path(path)
    if not binding_path.exists():
        return EvaluatorBindingStore()
    try:
        raw = yaml.safe_load(binding_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid evaluator binding YAML: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError("Evaluator binding file must be a YAML mapping")
    _reject_secret_fields(raw)
    try:
        return EvaluatorBindingStore.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(str(exc)) from exc


def save_evaluator_bindings(path: Path | str, store: EvaluatorBindingStore) -> None:
    binding_path = Path(path)
    binding_path.parent.mkdir(parents=True, exist_ok=True)
    payload = store.model_dump(mode="json", exclude_none=False)
    _reject_secret_fields(payload)
    binding_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _reject_secret_fields(value: Any, *, path: str = "") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            if any(marker in lowered for marker in SECRET_FIELD_MARKERS):
                raise ConfigError(f"Evaluator binding contains secret field: {path}{key}")
            _reject_secret_fields(child, path=f"{path}{key}.")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_secret_fields(child, path=f"{path}{index}.")
