from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from evaluator_harness.config import EvaluatorSourceType, ProjectConfig
from evaluator_harness.errors import ConfigError
from evaluator_harness.progress import NullProgressReporter, ProgressReporter
from evaluator_harness.prompts import PromptDefinition, parse_prompt_file


PromptArtifactType = Literal["task", "evaluator"]
PromptShape = Literal["text", "chat"]
PromptSyncMode = Literal["dry-run", "apply"]

MANAGED_PROMPT_PATTERN = re.compile(r"^[A-Za-z0-9_/-]+$")
SECRET_FIELD_MARKERS = ("secret", "api_key", "token", "password", "credential")


@dataclass(frozen=True)
class PromptArtifact:
    project: str
    project_version: str
    artifact_type: PromptArtifactType
    artifact_name: str
    artifact_version: str
    local_path: Path
    prompt_shape: PromptShape
    roles: list[str]
    content_identity: str
    managed_name: str
    labels: list[str]
    tags: list[str]
    definition: PromptDefinition

    @property
    def key(self) -> tuple[str, str, str, str, str]:
        return (
            self.project,
            self.project_version,
            self.artifact_type,
            self.artifact_name,
            self.artifact_version,
        )

    def langfuse_prompt_payload(self) -> dict[str, Any]:
        config = {
            "managed_by": "evaluator_harness",
            "project": self.project,
            "project_version": self.project_version,
            "artifact_type": self.artifact_type,
            "artifact_name": self.artifact_name,
            "artifact_version": self.artifact_version,
            "local_path": self.local_path.as_posix(),
            "prompt_shape": self.prompt_shape,
            "roles": self.roles,
            "content_identity": self.content_identity,
        }
        if self.prompt_shape == "chat":
            prompt: Any = [
                {"role": message.role, "content": message.content}
                for message in self.definition.messages
            ]
            prompt_type = "chat"
        else:
            prompt = self.definition.text
            prompt_type = "text"
        return {
            "name": self.managed_name,
            "type": prompt_type,
            "prompt": prompt,
            "labels": self.labels,
            "tags": self.tags,
            "config": config,
            "commit_message": (
                f"Sync {self.artifact_type} prompt {self.artifact_name} "
                f"{self.artifact_version} ({self.content_identity})"
            ),
        }


class PromptBindingRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    project: str
    project_version: str
    artifact_type: PromptArtifactType
    artifact_name: str
    artifact_version: str
    managed_name: str
    content_identity: str
    prompt_shape: PromptShape
    active: bool = True
    last_synced_at: str
    langfuse_prompt_version: int | None = None
    langfuse_labels: list[str] = Field(default_factory=list)
    roles: list[str] = Field(default_factory=list)

    @property
    def key(self) -> tuple[str, str, str, str, str]:
        return (
            self.project,
            self.project_version,
            self.artifact_type,
            self.artifact_name,
            self.artifact_version,
        )


class PromptBindingStore(BaseModel):
    bindings: list[PromptBindingRecord] = Field(default_factory=list)

    def find(self, artifact: PromptArtifact) -> PromptBindingRecord | None:
        for binding in self.bindings:
            if binding.active and binding.key == artifact.key:
                return binding
        return None

    def upsert(self, record: PromptBindingRecord) -> None:
        self.bindings = [
            binding for binding in self.bindings if binding.key != record.key
        ]
        self.bindings.append(record)


@dataclass(frozen=True)
class PromptSyncStatus:
    artifact: PromptArtifact
    operation: str
    status: str
    managed_name: str
    content_identity: str
    langfuse_prompt_version: int | None = None
    message: str = ""
    remediation: str | None = None


@dataclass(frozen=True)
class PromptSyncReport:
    project: str
    project_version: str
    mode: PromptSyncMode
    binding_path: Path
    items: list[PromptSyncStatus]

    @property
    def total_count(self) -> int:
        return len(self.items)

    @property
    def created_count(self) -> int:
        return sum(1 for item in self.items if item.status == "created")

    @property
    def reused_count(self) -> int:
        return sum(1 for item in self.items if item.status == "reused")

    @property
    def conflict_count(self) -> int:
        return sum(1 for item in self.items if item.status == "conflict")

    @property
    def failed_count(self) -> int:
        return sum(1 for item in self.items if item.status == "failed")

    @property
    def overall_status(self) -> str:
        return "success" if self.conflict_count == 0 and self.failed_count == 0 else "failure"


def discover_prompt_artifacts(config: ProjectConfig) -> list[PromptArtifact]:
    artifacts = [
        _artifact_from_prompt_ref(
            config,
            artifact_type="task",
            artifact_name="task_prompt",
            path=config.task_prompt.path,
            version=config.task_prompt.version,
        )
    ]
    seen = {artifacts[0].key}
    for evaluator in config.evaluators:
        if (
            evaluator.type != "llm_as_judge"
            or evaluator.source_type != EvaluatorSourceType.CUSTOM
            or evaluator.prompt_path is None
        ):
            continue
        artifact = _artifact_from_prompt_ref(
            config,
            artifact_type="evaluator",
            artifact_name=evaluator.name,
            path=evaluator.prompt_path,
            version=str(evaluator.prompt_version or evaluator.version),
        )
        if artifact.key in seen:
            raise ConfigError(f"Duplicate prompt artifact: {artifact.key}")
        seen.add(artifact.key)
        artifacts.append(artifact)
    _assert_unique_managed_names(artifacts)
    return artifacts


def sync_project_prompts(
    config: ProjectConfig,
    langfuse_client: Any,
    *,
    dry_run: bool = False,
    progress: ProgressReporter | None = None,
    binding_path: Path | None = None,
) -> PromptSyncReport:
    mode: PromptSyncMode = "dry-run" if dry_run else "apply"
    path = binding_path or default_prompt_binding_path(config)
    store = load_prompt_bindings(path)
    artifacts = discover_prompt_artifacts(config)
    items: list[PromptSyncStatus] = []
    reporter = progress or NullProgressReporter()
    with reporter.task(
        "Checking prompts" if dry_run else "Syncing prompts",
        total=len(artifacts),
    ) as task:
        for artifact in artifacts:
            try:
                status = _sync_one_prompt(
                    artifact,
                    langfuse_client,
                    store=store,
                    dry_run=dry_run,
                )
            except Exception as exc:
                status = PromptSyncStatus(
                    artifact=artifact,
                    operation="fail",
                    status="failed",
                    managed_name=artifact.managed_name,
                    content_identity=artifact.content_identity,
                    message=str(exc),
                    remediation="Resolve the prompt sync error and rerun.",
                )
            items.append(status)
            task.advance()
    if not dry_run:
        successful = [item for item in items if item.status in {"created", "reused"}]
        for item in successful:
            store.upsert(_binding_from_status(item))
        save_prompt_bindings(path, store)
    return PromptSyncReport(
        project=config.project.name,
        project_version=config.project.version,
        mode=mode,
        binding_path=path,
        items=items,
    )


def prompt_provenance_metadata(
    config: ProjectConfig,
    *,
    artifact_type: PromptArtifactType = "task",
    artifact_name: str = "task_prompt",
    prompt_ref: Any | None = None,
    binding_path: Path | None = None,
) -> dict[str, Any]:
    if artifact_type == "task":
        ref = prompt_ref or config.task_prompt
        artifact = _artifact_from_prompt_ref(
            config,
            artifact_type="task",
            artifact_name=artifact_name,
            path=ref.path,
            version=ref.version,
        )
    else:
        evaluator = next(
            (candidate for candidate in config.evaluators if candidate.name == artifact_name),
            None,
        )
        if evaluator is None or evaluator.prompt_path is None:
            return {}
        artifact = _artifact_from_prompt_ref(
            config,
            artifact_type="evaluator",
            artifact_name=evaluator.name,
            path=evaluator.prompt_path,
            version=str(evaluator.prompt_version or evaluator.version),
        )
    metadata: dict[str, Any] = {
        "prompt_artifact_type": artifact.artifact_type,
        "prompt_artifact_name": artifact.artifact_name,
        "prompt_local_path": artifact.local_path.as_posix(),
        "prompt_content_identity": artifact.content_identity,
        "prompt_managed_name": artifact.managed_name,
    }
    binding = load_prompt_bindings(binding_path or default_prompt_binding_path(config)).find(artifact)
    if binding and binding.content_identity == artifact.content_identity:
        metadata.update(
            {
                "langfuse_prompt_name": binding.managed_name,
                "langfuse_prompt_version": binding.langfuse_prompt_version,
                "langfuse_prompt_labels": binding.langfuse_labels,
            }
        )
    return metadata


def default_prompt_binding_path(config: ProjectConfig) -> Path:
    return Path("configs/langfuse/prompt_bindings") / f"{config.project.name}.yaml"


def load_prompt_bindings(path: Path | str) -> PromptBindingStore:
    binding_path = Path(path)
    if not binding_path.exists():
        return PromptBindingStore()
    try:
        raw = yaml.safe_load(binding_path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid prompt binding YAML: {exc}") from exc
    if not isinstance(raw, dict):
        raise ConfigError("Prompt binding file must be a YAML mapping")
    _reject_secret_fields(raw)
    try:
        return PromptBindingStore.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(str(exc)) from exc


def save_prompt_bindings(path: Path | str, store: PromptBindingStore) -> None:
    binding_path = Path(path)
    binding_path.parent.mkdir(parents=True, exist_ok=True)
    payload = store.model_dump(mode="json", exclude_none=False)
    _reject_secret_fields(payload)
    binding_path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")


def _sync_one_prompt(
    artifact: PromptArtifact,
    langfuse_client: Any,
    *,
    store: PromptBindingStore,
    dry_run: bool,
) -> PromptSyncStatus:
    existing = langfuse_client.find_prompt_version(
        artifact.managed_name,
        label=artifact.artifact_version,
    )
    binding = store.find(artifact)
    if existing is not None:
        if not _is_harness_managed(existing):
            return _conflict(
                artifact,
                "Remote prompt exists without harness ownership metadata.",
                "Rename the remote prompt or treat it as user-owned outside this sync.",
                existing,
            )
        remote_identity = _remote_content_identity(existing)
        if remote_identity == artifact.content_identity:
            return PromptSyncStatus(
                artifact=artifact,
                operation="reuse",
                status="reused",
                managed_name=artifact.managed_name,
                content_identity=artifact.content_identity,
                langfuse_prompt_version=_remote_prompt_version(existing),
                message="Matching Langfuse prompt version already exists.",
            )
        return _conflict(
            artifact,
            "Prompt content changed under an already-synced prompt_version.",
            "Bump the configured prompt_version before publishing changed content.",
            existing,
        )
    if binding and binding.content_identity != artifact.content_identity:
        return _conflict(
            artifact,
            "Local binding has the same prompt version with different content.",
            "Bump the configured prompt_version before publishing changed content.",
            None,
        )
    if dry_run:
        return PromptSyncStatus(
            artifact=artifact,
            operation="create",
            status="changed" if binding else "skipped",
            managed_name=artifact.managed_name,
            content_identity=artifact.content_identity,
            message="Prompt version would be created.",
        )
    created = langfuse_client.create_prompt_version(artifact.langfuse_prompt_payload())
    return PromptSyncStatus(
        artifact=artifact,
        operation="create",
        status="created",
        managed_name=artifact.managed_name,
        content_identity=artifact.content_identity,
        langfuse_prompt_version=_remote_prompt_version(created),
        message="Created Langfuse prompt version.",
    )


def _artifact_from_prompt_ref(
    config: ProjectConfig,
    *,
    artifact_type: PromptArtifactType,
    artifact_name: str,
    path: Path,
    version: str,
) -> PromptArtifact:
    definition = parse_prompt_file(path, version=version)
    shape: PromptShape = "chat" if definition.shape == "messages" else "text"
    roles = [message.role for message in definition.messages]
    managed_name = managed_prompt_name(
        project=config.project.name,
        project_version=config.project.version,
        artifact_type=artifact_type,
        artifact_name=artifact_name,
        artifact_version=version,
    )
    return PromptArtifact(
        project=config.project.name,
        project_version=config.project.version,
        artifact_type=artifact_type,
        artifact_name=artifact_name,
        artifact_version=version,
        local_path=Path(path),
        prompt_shape=shape,
        roles=roles,
        content_identity=content_identity(definition),
        managed_name=managed_name,
        labels=[
            config.project.name,
            config.project.version,
            artifact_type,
            f"prompt-{version}",
        ],
        tags=[
            "evaluator-harness",
            config.project.name,
            config.project.version,
            artifact_type,
        ],
        definition=definition,
    )


def managed_prompt_name(
    *,
    project: str,
    project_version: str,
    artifact_type: str,
    artifact_name: str,
    artifact_version: str,
) -> str:
    name = (
        f"EH_{_slug(project)}_{_slug(project_version)}_prompt_"
        f"{_slug(artifact_type)}_{_slug(artifact_name)}_{_slug(artifact_version)}"
    )
    if not MANAGED_PROMPT_PATTERN.fullmatch(name):
        raise ConfigError(f"Managed prompt name is not slug-safe: {name}")
    return name


def content_identity(definition: PromptDefinition) -> str:
    payload = {
        "shape": "chat" if definition.shape == "messages" else "text",
        "text": definition.text if definition.shape == "text" else None,
        "messages": [
            {"role": message.role, "content": message.content}
            for message in definition.messages
        ],
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"sha256:{digest}"


def _binding_from_status(status: PromptSyncStatus) -> PromptBindingRecord:
    artifact = status.artifact
    return PromptBindingRecord(
        project=artifact.project,
        project_version=artifact.project_version,
        artifact_type=artifact.artifact_type,
        artifact_name=artifact.artifact_name,
        artifact_version=artifact.artifact_version,
        managed_name=artifact.managed_name,
        langfuse_prompt_version=status.langfuse_prompt_version,
        langfuse_labels=artifact.labels,
        content_identity=artifact.content_identity,
        prompt_shape=artifact.prompt_shape,
        roles=artifact.roles,
        active=True,
        last_synced_at=datetime.now(UTC).isoformat(),
    )


def _conflict(
    artifact: PromptArtifact,
    message: str,
    remediation: str,
    remote: dict[str, Any] | None,
) -> PromptSyncStatus:
    return PromptSyncStatus(
        artifact=artifact,
        operation="conflict",
        status="conflict",
        managed_name=artifact.managed_name,
        content_identity=artifact.content_identity,
        langfuse_prompt_version=_remote_prompt_version(remote),
        message=message,
        remediation=remediation,
    )


def _assert_unique_managed_names(artifacts: list[PromptArtifact]) -> None:
    names: set[str] = set()
    for artifact in artifacts:
        if artifact.managed_name in names:
            raise ConfigError(f"Duplicate managed prompt name: {artifact.managed_name}")
        names.add(artifact.managed_name)


def _is_harness_managed(prompt: dict[str, Any]) -> bool:
    config = prompt.get("config") or {}
    return isinstance(config, dict) and config.get("managed_by") == "evaluator_harness"


def _remote_content_identity(prompt: dict[str, Any]) -> str | None:
    config = prompt.get("config") or {}
    return str(config.get("content_identity")) if isinstance(config, dict) and config.get("content_identity") else None


def _remote_prompt_version(prompt: dict[str, Any] | None) -> int | None:
    if not prompt:
        return None
    value = prompt.get("version") or prompt.get("langfuse_prompt_version")
    return int(value) if value is not None else None


def _slug(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9]+", "_", value).strip("_")
    return slug or "unnamed"


def _reject_secret_fields(value: Any, *, path: str = "") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            lowered = str(key).lower()
            if any(marker in lowered for marker in SECRET_FIELD_MARKERS):
                raise ConfigError(f"Prompt binding contains secret field: {path}{key}")
            _reject_secret_fields(child, path=f"{path}{key}.")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _reject_secret_fields(child, path=f"{path}{index}.")
