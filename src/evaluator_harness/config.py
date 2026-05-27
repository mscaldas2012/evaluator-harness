from __future__ import annotations

from enum import Enum
import os
from pathlib import Path
from typing import Any, Literal
import re

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from evaluator_harness.errors import ConfigError


ENV_NAME_PATTERN = re.compile(r"^[A-Z_][A-Z0-9_]*$")
SCORE_PREFIX_PATTERN = re.compile(r"^[A-Za-z0-9_-]+[_-]$")


class DatasetKind(str, Enum):
    LOCAL_CSV = "local_csv"
    LOCAL_JSON = "local_json"
    LANGFUSE = "langfuse"


class ProviderName(str, Enum):
    OPENAI_COMPATIBLE = "openai_compatible"
    OLLAMA = "ollama"
    DRY_RUN = "dry_run"


class AuthMode(str, Enum):
    AZURE_CLIENT_CREDENTIALS = "azure_client_credentials"
    API_KEY = "api_key"
    NONE = "none"


class ScoreDataType(str, Enum):
    NUMERIC = "NUMERIC"
    CATEGORICAL = "CATEGORICAL"
    BOOLEAN = "BOOLEAN"
    TEXT = "TEXT"


class EvaluatorMode(str, Enum):
    BASELINE = "baseline"
    CANDIDATE = "candidate"


class DatasetSource(BaseModel):
    kind: DatasetKind = DatasetKind.LOCAL_CSV
    path: Path | None = None
    langfuse_dataset_name: str | None = None
    langfuse_dataset_id: str | None = None
    langfuse_dataset_version: str | None = None
    item_id_strategy: Literal["explicit_or_hash"] = "explicit_or_hash"
    metadata: dict[str, Any] = Field(default_factory=dict)


class PromptRef(BaseModel):
    path: Path
    version: str
    template_variables: list[str] = Field(default_factory=lambda: ["input"])
    metadata: dict[str, Any] = Field(default_factory=dict)


class AzureCredentialRefs(BaseModel):
    tenant_id_env: str
    client_id_env: str
    client_secret_env: str
    scope_env: str
    subscription_key_env: str
    api_version_env: str
    endpoint_env: str

    @field_validator("*")
    @classmethod
    def env_names_only(cls, value: str) -> str:
        if not ENV_NAME_PATTERN.fullmatch(value):
            raise ValueError(
                "provider credential references must be environment variable names"
            )
        return value


class ModelParameters(BaseModel):
    temperature: float
    top_p: float | None = None
    max_tokens: int | None = None
    token_limit_parameter: Literal["max_tokens", "max_completion_tokens"] = "max_tokens"
    seed: int | None = None


class ModelConfig(BaseModel):
    name: str
    provider: ProviderName
    auth_mode: AuthMode
    model: str
    endpoint: str | None = None
    azure: AzureCredentialRefs | None = None
    parameters: ModelParameters
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_auth_requirements(self) -> ModelConfig:
        if self.auth_mode == AuthMode.AZURE_CLIENT_CREDENTIALS and self.azure is None:
            raise ValueError("azure credential env references are required")
        if self.provider == ProviderName.DRY_RUN and self.auth_mode != AuthMode.NONE:
            raise ValueError("dry_run provider requires auth_mode none")
        return self


class ScoreConfigRef(BaseModel):
    name: str
    managed_by_harness: bool = True
    data_type: ScoreDataType
    min_value: float | None = None
    max_value: float | None = None
    categories: list[str] | None = None
    description: str | None = None
    langfuse_score_config_id: str | None = None

    @model_validator(mode="after")
    def validate_score_contract(self) -> ScoreConfigRef:
        if self.data_type == ScoreDataType.NUMERIC:
            if self.min_value is None or self.max_value is None:
                raise ValueError("Numeric score configs require min_value and max_value")
            if self.min_value >= self.max_value:
                raise ValueError("Numeric score min_value must be less than max_value")
        if self.data_type == ScoreDataType.CATEGORICAL and not self.categories:
            raise ValueError("Categorical score configs require categories")
        if not self.managed_by_harness and not self.langfuse_score_config_id:
            raise ValueError(
                "user-owned score configs require langfuse_score_config_id"
            )
        return self


class EvaluatorDefinition(BaseModel):
    name: str
    type: Literal["llm_as_judge", "deterministic"]
    version: str
    prompt_path: Path | None = None
    score: ScoreConfigRef
    blind: bool = True
    modes: list[EvaluatorMode]
    variables: list[str]


class HumanReviewPolicy(BaseModel):
    enabled: bool = True
    queue_ownership: Literal["managed_by_harness", "user_owned"] = "managed_by_harness"
    queue_name: str | None = None
    minimum_sample_percent: int = 5
    prioritize: list[str] = Field(
        default_factory=lambda: ["failures", "low_confidence", "disputed"]
    )
    annotation_queue_id: str | None = None
    review_policy_version: str | None = None
    fallback_to_env: bool = True

    @field_validator("queue_name")
    @classmethod
    def queue_names_are_slug_safe(cls, value: str | None) -> str | None:
        if value is None:
            return value
        from evaluator_harness.annotation_queues import validate_queue_name

        return validate_queue_name(value)

    @model_validator(mode="after")
    def validate_queue_policy(self) -> HumanReviewPolicy:
        if self.enabled and self.queue_ownership == "user_owned" and not self.annotation_queue_id:
            raise ValueError("user_owned human review requires annotation_queue_id")
        return self


class EvaluationProject(BaseModel):
    name: str
    description: str | None = None
    version: str
    score_config_prefix: str
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("score_config_prefix")
    @classmethod
    def validate_score_config_prefix(cls, value: str) -> str:
        if len(value) > 64 or not SCORE_PREFIX_PATTERN.fullmatch(value):
            raise ValueError(
                "score_config_prefix must be slug-safe, <=64 chars, and end with _ or -"
            )
        return value


class ProjectConfig(BaseModel):
    project: EvaluationProject
    dataset: DatasetSource
    task_prompt: PromptRef
    baseline: ModelConfig
    candidates: list[ModelConfig]
    evaluators: list[EvaluatorDefinition]
    human_review: HumanReviewPolicy = Field(default_factory=HumanReviewPolicy)

    @model_validator(mode="after")
    def validate_required_collections(self) -> ProjectConfig:
        if not self.candidates:
            raise ValueError("at least one candidate is required")
        if not self.evaluators:
            raise ValueError("at least one evaluator is required")
        return self


class DatasetItem(BaseModel):
    item_id: str
    input: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    reference_output: str | None = None
    ground_truth: str | None = None
    source_row: int | None = None
    input_hash: str | None = None


class BaselineReference(BaseModel):
    baseline_run_id: str
    langfuse_run_name: str
    project_name: str
    project_version: str
    dataset_name: str
    dataset_version: str
    prompt_version: str
    evaluator_set_id: str
    baseline_model: str
    baseline_parameters_hash: str
    created_at: str


class OutputRecord(BaseModel):
    run_id: str
    item_id: str
    trace_id: str
    observation_id: str | None = None
    output: str | None = None
    provider: str
    model: str
    parameters: dict[str, Any]
    latency_ms: int | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None
    timestamp: str
    baseline_reference: BaselineReference | None = None
    error: str | None = None


class HumanReviewSelection(BaseModel):
    item_id: str
    run_id: str
    trace_id: str
    selection_reason: Literal["failure", "low_confidence", "disputed", "sample"]
    selection_bucket: Literal["stable_calibration", "run_risk"] = "stable_calibration"
    annotation_queue_id: str | None = None
    queued: bool = False


class LiveSettings(BaseModel):
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str | None = None
    annotation_queue_id: str | None = None

    @classmethod
    def from_env(cls, *, env_file: Path | str = ".env", load_file: bool = True) -> LiveSettings:
        if load_file:
            load_env_file(env_file)
        _normalize_langfuse_host_alias()
        return cls(
            langfuse_public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            langfuse_secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            langfuse_host=os.getenv("LANGFUSE_HOST") or os.getenv("LANGFUSE_BASE_URL"),
            annotation_queue_id=os.getenv("LANGFUSE_ANNOTATION_QUEUE_ID"),
        )

    def require_langfuse(self) -> None:
        missing = [
            name
            for name, value in {
                "LANGFUSE_PUBLIC_KEY": self.langfuse_public_key,
                "LANGFUSE_SECRET_KEY": self.langfuse_secret_key,
                "LANGFUSE_HOST": self.langfuse_host,
            }.items()
            if not value
        ]
        if missing:
            raise ConfigError(
                "Missing Langfuse environment variables: " + ", ".join(missing)
            )


def load_env_file(path: Path | str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not ENV_NAME_PATTERN.fullmatch(key):
            continue
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)
    _normalize_langfuse_host_alias()


def _normalize_langfuse_host_alias() -> None:
    base_url = os.getenv("LANGFUSE_BASE_URL")
    if base_url and not os.getenv("LANGFUSE_HOST"):
        os.environ["LANGFUSE_HOST"] = base_url


def load_project_config(path: Path | str) -> ProjectConfig:
    project_path = Path(path)
    try:
        raw = yaml.safe_load(project_path.read_text(encoding="utf-8"))
        if not isinstance(raw, dict):
            raise ConfigError("Project config must be a YAML mapping")
        return ProjectConfig.model_validate(raw)
    except FileNotFoundError as exc:
        raise ConfigError(f"Project config not found: {project_path}") from exc
    except ValidationError as exc:
        raise ConfigError(str(exc)) from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in project config: {exc}") from exc


def validate_project_config(config: ProjectConfig, *, base_dir: Path | None = None) -> None:
    base = base_dir or Path.cwd()
    _validate_prompt_ref(config.task_prompt, base=base, required_variables=["input"])

    for evaluator in config.evaluators:
        if evaluator.type == "llm_as_judge":
            if evaluator.prompt_path is None:
                raise ConfigError(f"Evaluator {evaluator.name} requires prompt_path")
            _validate_prompt_file(evaluator.prompt_path, base=base)
        if EvaluatorMode.BASELINE in evaluator.modes:
            _require_variables(evaluator, ["input", "output"])
        if EvaluatorMode.CANDIDATE in evaluator.modes:
            _require_variables(evaluator, ["input", "output", "baseline_output"])

        managed_name = f"{config.project.score_config_prefix}{evaluator.score.name}"
        if len(managed_name) > 128:
            raise ConfigError(
                f"Managed score config name is too long for evaluator {evaluator.name}"
            )


def _validate_prompt_ref(prompt_ref: PromptRef, *, base: Path, required_variables: list[str]) -> None:
    if not prompt_ref.version:
        raise ConfigError(f"Prompt {prompt_ref.path} requires a version")
    prompt_text = _validate_prompt_file(prompt_ref.path, base=base)
    for variable in required_variables:
        if variable not in prompt_ref.template_variables:
            raise ConfigError(f"Prompt {prompt_ref.path} must declare variable {variable}")
        if "{{" + variable + "}}" not in prompt_text:
            raise ConfigError(f"Prompt {prompt_ref.path} must include {{{{{variable}}}}}")


def _validate_prompt_file(path: Path, *, base: Path) -> str:
    prompt_path = path if path.is_absolute() else base / path
    if not prompt_path.exists():
        raise ConfigError(f"Prompt file not found: {path}")
    text = prompt_path.read_text(encoding="utf-8")
    if not text.strip():
        raise ConfigError(f"Prompt file is empty: {path}")
    return text


def _require_variables(evaluator: EvaluatorDefinition, variables: list[str]) -> None:
    missing = [variable for variable in variables if variable not in evaluator.variables]
    if missing:
        raise ConfigError(
            f"Evaluator {evaluator.name} missing variables: {', '.join(missing)}"
        )
