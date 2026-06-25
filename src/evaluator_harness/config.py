from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import csv
import json
import os
from pathlib import Path
from typing import Any, Literal
import re

import yaml
from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from evaluator_harness.errors import ConfigError
from evaluator_harness.environment import EnvironmentResolver, ResolvedEnvironment, EnvironmentScope


ENV_NAME_PATTERN = re.compile(r"^[A-Z_][A-Z0-9_]*$")
SCORE_PREFIX_PATTERN = re.compile(r"^[A-Za-z0-9_-]+[_-]$")
SHARED_EVALUATION_ALLOWED_SECTIONS = frozenset(
    {"evaluators", "judge_setup", "human_review"}
)
SHARED_EVALUATION_CONFLICT_SECTIONS = SHARED_EVALUATION_ALLOWED_SECTIONS


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
    SINGLE_OUTPUT = "single_output"
    BASELINE_COMPARISON = "baseline_comparison"


class EvaluatorRunType(str, Enum):
    BASELINE = "baseline"
    CANDIDATE = "candidate"


class EvaluatorTarget(str, Enum):
    OBSERVATION = "observation"
    TRACE = "trace"
    EXPERIMENT = "experiment"


class ScoreSource(str, Enum):
    LLM_JUDGE = "llm_judge"
    HUMAN_ANNOTATION = "human_annotation"
    API = "api"


class EvaluatorSourceType(str, Enum):
    CATALOG = "catalog"
    CUSTOM = "custom"
    USER_OWNED = "user_owned"


class HistoricalBackfillPolicy(str, Enum):
    DISABLED = "disabled"
    ENABLED = "enabled"


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


class AzureApiKeyCredentialRefs(BaseModel):
    api_key_env: str
    endpoint_env: str
    api_version_env: str
    subscription_key_env: str | None = None

    @field_validator("*")
    @classmethod
    def env_names_only(cls, value: str | None) -> str | None:
        if value is None:
            return value
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
    exclude_from_campaign: bool = Field(default=False, alias="exclude-from-campaign")
    task_prompt: PromptRef | None = None
    endpoint: str | None = None
    azure: AzureCredentialRefs | None = None
    azure_api_key: AzureApiKeyCredentialRefs | None = None
    parameters: ModelParameters
    metadata: dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_auth_requirements(self) -> ModelConfig:
        if self.provider == ProviderName.DRY_RUN and self.auth_mode != AuthMode.NONE:
            raise ValueError("dry_run provider requires auth_mode none")
        if self.auth_mode == AuthMode.AZURE_CLIENT_CREDENTIALS:
            if self.azure is None:
                raise ValueError(
                    f"Model {self.name} azure credential env references are required"
                )
            if self.azure_api_key is not None:
                raise ValueError(
                    f"Model {self.name} must not include azure_api_key credential refs "
                    "when auth_mode is azure_client_credentials"
                )
        if self.auth_mode == AuthMode.API_KEY:
            if self.azure_api_key is None:
                raise ValueError(
                    f"Model {self.name} azure_api_key credential env references are required"
                )
            if self.azure is not None:
                raise ValueError(
                    f"Model {self.name} must not include azure credential refs "
                    "when auth_mode is api_key"
                )
        if self.auth_mode == AuthMode.NONE:
            if self.azure is not None or self.azure_api_key is not None:
                raise ValueError(
                    f"Model {self.name} must not include credential refs when auth_mode is none"
                )
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
    allowed_score_sources: list[ScoreSource] = Field(
        default_factory=lambda: [
            ScoreSource.LLM_JUDGE,
            ScoreSource.HUMAN_ANNOTATION,
        ]
    )

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


class ScoreFieldSchema(BaseModel):
    type: Literal["number"] = "number"
    minimum: float = 0
    maximum: float = 1

    @model_validator(mode="after")
    def validate_range(self) -> ScoreFieldSchema:
        if self.minimum >= self.maximum:
            raise ValueError("score minimum must be less than maximum")
        return self


class ConfidenceFieldSchema(BaseModel):
    type: Literal["number"] = "number"
    minimum: float = 0
    maximum: float = 1

    @model_validator(mode="after")
    def validate_range(self) -> ConfidenceFieldSchema:
        if self.minimum >= self.maximum:
            raise ValueError("confidence minimum must be less than maximum")
        return self


class JudgeResultSchema(BaseModel):
    reasoning: Literal["string"] = "string"
    score: ScoreFieldSchema = Field(default_factory=ScoreFieldSchema)
    confidence: ConfidenceFieldSchema = Field(default_factory=ConfidenceFieldSchema)


class EvaluatorFilterProfile(BaseModel):
    target: EvaluatorTarget = EvaluatorTarget.OBSERVATION
    observation_role: str = "model_output"
    observation_name: str | None = None
    project: str | None = None
    project_version: str | None = None
    evaluator_set_id: str | None = None
    environment: str | None = None
    run_types: list[EvaluatorRunType] = Field(default_factory=list)


class JudgeSetupDefaults(BaseModel):
    default_judge_model: str | None = None
    default_llm_connection: str | None = None
    binding_path: Path | None = None
    default_sampling_percent: int | None = None
    historical_backfill: HistoricalBackfillPolicy = HistoricalBackfillPolicy.DISABLED

    @field_validator("default_sampling_percent")
    @classmethod
    def validate_sampling_percent(cls, value: int | None) -> int | None:
        if value is not None and not 0 < value <= 100:
            raise ValueError("default_sampling_percent must be between 1 and 100")
        return value


class EvaluatorDefinition(BaseModel):
    name: str
    type: Literal["llm_as_judge", "deterministic"]
    version: str
    dimension: str | None = None
    source_type: EvaluatorSourceType = EvaluatorSourceType.CUSTOM
    catalog_ref: str | None = None
    remote_evaluator_id: str | None = None
    target: EvaluatorTarget | None = None
    target_observation_role: str = "model_output"
    target_observation_name: str | None = Field(
        default=None,
        description=(
            "Optional explicit Langfuse observation name for providers that cannot "
            "mark exactly one final output with target_observation_role."
        ),
    )
    run_types: list[EvaluatorRunType] | None = None
    mode: EvaluatorMode | None = None
    prompt_path: Path | None = None
    prompt_version: str | None = None
    judge_model: str | None = None
    llm_connection: str | None = None
    sampling_percent: int | None = None
    historical_backfill: HistoricalBackfillPolicy | None = None
    managed_display_name: str | None = None
    score: ScoreConfigRef
    blind: bool = True
    non_blind_reason: str | None = None
    modes: list[EvaluatorRunType] | None = None
    variables: list[str] = Field(default_factory=list)
    required_inputs: list[str] = Field(default_factory=list)
    output_schema: JudgeResultSchema | None = None
    filter_profile: EvaluatorFilterProfile | None = None

    @field_validator("sampling_percent")
    @classmethod
    def validate_sampling_percent(cls, value: int | None) -> int | None:
        if value is not None and not 0 < value <= 100:
            raise ValueError("sampling_percent must be between 1 and 100")
        return value

    @model_validator(mode="after")
    def normalize_evaluator_fields(self) -> EvaluatorDefinition:
        legacy_definition = (
            self.target is None
            and self.output_schema is None
            and self.filter_profile is None
            and self.modes is not None
        )
        if self.run_types is None and self.modes is not None:
            self.run_types = list(self.modes)
        if self.modes is None and self.run_types is not None:
            self.modes = list(self.run_types)
        if legacy_definition:
            self.target = EvaluatorTarget.OBSERVATION
            self.output_schema = JudgeResultSchema()
        if self.mode is None:
            self.mode = (
                EvaluatorMode.BASELINE_COMPARISON
                if self.run_types and EvaluatorRunType.CANDIDATE in self.run_types
                else EvaluatorMode.SINGLE_OUTPUT
            )
        if self.dimension is None:
            self.dimension = self.name
        if not self.required_inputs and self.variables:
            self.required_inputs = list(self.variables)
        if self.prompt_version is None:
            self.prompt_version = self.version
        if not self.blind and not (self.non_blind_reason or "").strip():
            raise ValueError("non_blind_reason is required when blind=false")
        return self


class HumanReviewPolicy(BaseModel):
    enabled: bool = True
    queue_ownership: Literal["managed_by_harness", "user_owned"] = "managed_by_harness"
    queue_name: str | None = None
    minimum_sample_percent: int = 5
    minimum_sample_count: int = Field(default=1, ge=0)
    sample_strategy: Literal["stable", "random"] = "stable"
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


class ConfigRefs(BaseModel):
    evaluation: Path | None = None


class ScenarioIdentity(BaseModel):
    group: str
    name: str
    display_name: str

    @field_validator("*")
    @classmethod
    def values_must_not_be_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("scenario fields must not be blank")
        return value


class ProjectConfig(BaseModel):
    project: EvaluationProject
    config_refs: ConfigRefs | None = None
    scenario: ScenarioIdentity | None = None
    dataset: DatasetSource
    task_prompt: PromptRef
    baseline: ModelConfig
    candidates: list[ModelConfig]
    evaluators: list[EvaluatorDefinition]
    judge_setup: JudgeSetupDefaults = Field(default_factory=JudgeSetupDefaults)
    human_review: HumanReviewPolicy = Field(default_factory=HumanReviewPolicy)

    @model_validator(mode="after")
    def validate_required_collections(self) -> ProjectConfig:
        if not self.candidates:
            raise ValueError("at least one candidate is required")
        candidate_names = [candidate.name for candidate in self.candidates]
        if len(candidate_names) != len(set(candidate_names)):
            raise ValueError("Candidate names must be unique within a project")
        if not self.evaluators:
            raise ValueError("at least one evaluator is required")
        return self


def scenario_metadata(config: ProjectConfig) -> dict[str, str]:
    if config.scenario is None:
        return {}
    return {
        "scenario_group": config.scenario.group,
        "scenario_name": config.scenario.name,
        "scenario_display_name": config.scenario.display_name,
    }


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
    selection_reason: Literal[
        "failure",
        "low_confidence",
        "disputed",
        "sample",
        "annotated_queue_item",
    ]
    selection_bucket: Literal[
        "stable_calibration",
        "run_risk",
        "completed_annotation",
    ] = "stable_calibration"
    annotation_queue_id: str | None = None
    queued: bool = False


class LiveSettings(BaseModel):
    langfuse_public_key: str | None = None
    langfuse_secret_key: str | None = None
    langfuse_host: str | None = None
    annotation_queue_id: str | None = None

    @staticmethod
    def _env_value(env: dict[str, str] | ResolvedEnvironment | None, name: str) -> str | None:
        if env is None:
            return os.getenv(name)
        return env.get(name)

    @classmethod
    def from_env(
        cls,
        *,
        env_file: Path | str = ".env",
        project_env_file: Path | str | None = None,
        load_file: bool = True,
        env_mapping: dict[str, str] | ResolvedEnvironment | None = None,
    ) -> LiveSettings:
        if env_mapping is None and load_file:
            env_mapping = resolve_environment(
                env_file=env_file,
                project_env_file=project_env_file,
            )
        return cls(
            langfuse_public_key=cls._env_value(env_mapping, "LANGFUSE_PUBLIC_KEY"),
            langfuse_secret_key=cls._env_value(env_mapping, "LANGFUSE_SECRET_KEY"),
            langfuse_host=cls._env_value(env_mapping, "LANGFUSE_HOST")
            or cls._env_value(env_mapping, "LANGFUSE_BASE_URL"),
            annotation_queue_id=cls._env_value(env_mapping, "LANGFUSE_ANNOTATION_QUEUE_ID"),
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


@dataclass(frozen=True)
class EnvLoadResult:
    loaded_files: tuple[Path, ...]
    loaded_keys: tuple[str, ...]
    ignored_files: tuple[Path, ...] = ()
    ignored_keys: tuple[str, ...] = ()


@dataclass(frozen=True)
class _ManagedEnvValue:
    value: str
    source: str


_MANAGED_ENV_VALUES: dict[str, _ManagedEnvValue] = {}


def resolve_environment(
    *,
    env_file: Path | str = ".env",
    project_env_file: Path | str | None = None,
    defaults: dict[str, str] | None = None,
) -> ResolvedEnvironment:
    shell_vars = dict(os.environ)
    root_vars = _read_env_file_values(env_file)
    project_vars = _read_env_file_values(project_env_file) if project_env_file is not None else {}
    resolved = EnvironmentResolver.resolve(root_vars, project_vars, shell_vars, defaults)
    return ResolvedEnvironment(resolved)


def environment_scope(
    *,
    env_file: Path | str = ".env",
    project_env_file: Path | str | None = None,
    defaults: dict[str, str] | None = None,
    apply_to_os_environ: bool = False,
) -> EnvironmentScope:
    return EnvironmentScope(
        resolve_environment(
            env_file=env_file,
            project_env_file=project_env_file,
            defaults=defaults,
        ),
        apply_to_os_environ=apply_to_os_environ,
    )


def load_env_file(path: Path | str = ".env") -> None:
    _load_env_file(path, override_managed=False, source=str(path))
    _normalize_langfuse_host_alias()


def load_layered_env_files(
    *,
    root_env_file: Path | str = ".env",
    project_env_file: Path | str | None = None,
) -> EnvLoadResult:
    loaded_files: list[Path] = []
    loaded_keys: set[str] = set()
    ignored_files: list[Path] = []
    ignored_keys: set[str] = set()

    root_result = _load_env_file(
        root_env_file,
        override_managed=False,
        source="root_env",
        normalize_alias=False,
    )
    loaded_files.extend(root_result.loaded_files)
    loaded_keys.update(root_result.loaded_keys)
    ignored_files.extend(root_result.ignored_files)
    ignored_keys.update(root_result.ignored_keys)

    if project_env_file is not None:
        project_result = _load_env_file(
            project_env_file,
            override_managed=True,
            source="project_env",
            normalize_alias=False,
        )
        loaded_files.extend(project_result.loaded_files)
        loaded_keys.update(project_result.loaded_keys)
        ignored_files.extend(project_result.ignored_files)
        ignored_keys.update(project_result.ignored_keys)

    _normalize_langfuse_host_alias()
    return EnvLoadResult(
        loaded_files=tuple(loaded_files),
        loaded_keys=tuple(sorted(loaded_keys)),
        ignored_files=tuple(ignored_files),
        ignored_keys=tuple(sorted(ignored_keys)),
    )


def project_env_file_path(project_name: str, *, base_dir: Path | str = ".") -> Path:
    return Path(base_dir) / f".env.{project_name}"


def _load_env_file(
    path: Path | str,
    *,
    override_managed: bool,
    source: str,
    normalize_alias: bool = True,
) -> EnvLoadResult:
    env_path = Path(path)
    if not env_path.exists():
        return EnvLoadResult(loaded_files=(), loaded_keys=(), ignored_files=(env_path,))
    _, ignored_keys, values = _parse_env_file(env_path)
    loaded_keys: set[str] = set()
    for key, value in values.items():
        managed_value = _MANAGED_ENV_VALUES.get(key)
        env_value = os.environ.get(key)
        is_shell_value = env_value is not None and (
            managed_value is None or managed_value.value != env_value
        )
        if key not in os.environ or (override_managed and not is_shell_value):
            os.environ[key] = value
            _MANAGED_ENV_VALUES[key] = _ManagedEnvValue(value=value, source=source)
            loaded_keys.add(key)
    if normalize_alias:
        _normalize_langfuse_host_alias()
    return EnvLoadResult(
        loaded_files=(env_path,),
        loaded_keys=tuple(sorted(loaded_keys)),
        ignored_keys=tuple(sorted(ignored_keys)),
    )


def _read_env_file_values(path: Path | str | None) -> dict[str, str]:
    if path is None:
        return {}
    env_path = Path(path)
    if not env_path.exists():
        return {}
    _, _, values = _parse_env_file(env_path)
    return values


def _parse_env_file(path: Path) -> tuple[set[str], set[str], dict[str, str]]:
    loaded_keys: set[str] = set()
    ignored_keys: set[str] = set()
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not ENV_NAME_PATTERN.fullmatch(key):
            ignored_keys.add(key)
            continue
        value = value.strip().strip('"').strip("'")
        loaded_keys.add(key)
        values[key] = value
    return loaded_keys, ignored_keys, values


def _normalize_langfuse_host_alias() -> None:
    base_url = os.getenv("LANGFUSE_BASE_URL")
    if base_url and not os.getenv("LANGFUSE_HOST"):
        os.environ["LANGFUSE_HOST"] = base_url


def load_project_config(path: Path | str) -> ProjectConfig:
    project_path = Path(path)
    try:
        raw = _read_yaml_mapping(project_path, label="Project config")
        raw = _resolve_config_refs(raw, project_path=project_path)
        return ProjectConfig.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(str(exc)) from exc


def _read_yaml_mapping(path: Path, *, label: str) -> dict[str, Any]:
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"{label} not found: {path}") from exc
    except OSError as exc:
        raise ConfigError(f"{label} could not be read: {path}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"Invalid YAML in {label}: {exc}") from exc
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ConfigError(f"{label} must be a YAML mapping")
    return raw


def _resolve_config_refs(
    raw: dict[str, Any],
    *,
    project_path: Path,
) -> dict[str, Any]:
    config_refs = raw.get("config_refs")
    if config_refs is None:
        return raw
    if not isinstance(config_refs, dict):
        raise ConfigError("config_refs must be a YAML mapping")

    unknown_refs = sorted(set(config_refs) - {"evaluation"})
    if unknown_refs:
        raise ConfigError(
            "config_refs supports only evaluation; unsupported keys: "
            + ", ".join(unknown_refs)
        )

    evaluation_ref = config_refs.get("evaluation")
    if evaluation_ref in (None, ""):
        return raw
    if not isinstance(evaluation_ref, str | Path):
        raise ConfigError("config_refs.evaluation must be a path string")

    shared_path = _resolve_shared_config_path(Path(evaluation_ref), project_path=project_path)
    shared = _read_yaml_mapping(shared_path, label="config_refs.evaluation")
    _validate_shared_evaluation_sections(shared, shared_path=shared_path)
    _validate_shared_evaluation_conflicts(raw, shared)

    merged = dict(raw)
    for section in SHARED_EVALUATION_ALLOWED_SECTIONS:
        if section in shared:
            merged[section] = shared[section]
    return merged


def _resolve_shared_config_path(ref: Path, *, project_path: Path) -> Path:
    if ref.is_absolute():
        if ref.exists():
            return ref
        raise ConfigError(f"config_refs.evaluation not found: {ref}")

    project_relative = (project_path.parent / ref).resolve()
    if project_relative.exists():
        return project_relative

    repo_relative = (Path.cwd() / ref).resolve()
    if repo_relative.exists():
        return repo_relative

    raise ConfigError(
        "config_refs.evaluation not found: "
        f"{ref} (checked {project_relative} and {repo_relative})"
    )


def _validate_shared_evaluation_sections(
    shared: dict[str, Any],
    *,
    shared_path: Path,
) -> None:
    disallowed = sorted(set(shared) - SHARED_EVALUATION_ALLOWED_SECTIONS)
    if disallowed:
        raise ConfigError(
            "config_refs.evaluation contains disallowed sections in "
            f"{shared_path}: {', '.join(disallowed)}"
        )


def _validate_shared_evaluation_conflicts(
    raw: dict[str, Any],
    shared: dict[str, Any],
) -> None:
    conflicts = sorted(
        section
        for section in SHARED_EVALUATION_CONFLICT_SECTIONS
        if section in raw and section in shared
    )
    if conflicts:
        raise ConfigError(
            "config_refs.evaluation conflict with local project sections: "
            + ", ".join(conflicts)
        )


def validate_project_config(config: ProjectConfig, *, base_dir: Path | None = None) -> None:
    base = base_dir or Path.cwd()
    dataset_columns = _dataset_columns(config, base=base)
    project_prompt = _validate_prompt_ref(
        config.task_prompt,
        base=base,
        required_variables=["input"],
        dataset_columns=dataset_columns,
    )
    _validate_model_prompt_roles(config.baseline, project_prompt)
    for candidate in config.candidates:
        if candidate.task_prompt is not None:
            candidate_prompt = _validate_prompt_ref(
                candidate.task_prompt,
                base=base,
                required_variables=["input"],
                dataset_columns=dataset_columns,
            )
        else:
            candidate_prompt = project_prompt
        _validate_model_prompt_roles(candidate, candidate_prompt)
    from evaluator_harness.evaluators import validate_evaluators

    validate_evaluators(config, base=base)
    _validate_judge_setup(config, base=base)

    for evaluator in config.evaluators:
        managed_name = f"{config.project.score_config_prefix}{evaluator.score.name}"
        if len(managed_name) > 128:
            raise ConfigError(
                f"Managed score config name is too long for evaluator {evaluator.name}"
            )


def _validate_judge_setup(config: ProjectConfig, *, base: Path) -> None:
    from evaluator_harness.evaluator_bindings import validate_binding_path

    binding_path = config.judge_setup.binding_path or Path(
        "configs/langfuse/evaluator_bindings"
    ) / f"{config.project.name}.yaml"
    validate_binding_path(binding_path, repo_root=base)
    for evaluator in config.evaluators:
        if evaluator.type != "llm_as_judge":
            continue
        if not (
            evaluator.judge_model
            or evaluator.llm_connection
            or config.judge_setup.default_judge_model
            or config.judge_setup.default_llm_connection
        ):
            raise ConfigError(
                f"Evaluator {evaluator.name} requires a judge model or LLM connection"
            )
        if evaluator.source_type == EvaluatorSourceType.CATALOG and not evaluator.catalog_ref:
            raise ConfigError(f"Evaluator {evaluator.name} requires catalog_ref")
        if evaluator.source_type == EvaluatorSourceType.CUSTOM:
            if evaluator.prompt_path is None:
                raise ConfigError(f"Evaluator {evaluator.name} requires prompt_path")
            if not evaluator.prompt_version:
                raise ConfigError(f"Evaluator {evaluator.name} requires prompt_version")
            if evaluator.output_schema is None:
                raise ConfigError(f"Evaluator {evaluator.name} requires output_schema")
        if evaluator.source_type == EvaluatorSourceType.USER_OWNED and not evaluator.remote_evaluator_id:
            raise ConfigError(
                f"Evaluator {evaluator.name} user_owned setup requires remote_evaluator_id"
            )


def _validate_prompt_ref(
    prompt_ref: PromptRef,
    *,
    base: Path,
    required_variables: list[str],
    dataset_columns: set[str] | None = None,
) -> Any:
    if not prompt_ref.version:
        raise ConfigError(f"Prompt {prompt_ref.path} requires a version")
    prompt_text = _validate_prompt_file(prompt_ref.path, base=base)
    from evaluator_harness.prompts import parse_prompt_text, validate_dataset_variables

    prompt = parse_prompt_text(prompt_text, path=prompt_ref.path, version=prompt_ref.version)
    if prompt.variable_references:
        declared = set(prompt_ref.template_variables)
        missing_declarations = [
            ref.name for ref in prompt.variable_references if ref.name not in declared
        ]
        if missing_declarations:
            raise ConfigError(
                f"Prompt {prompt_ref.path} must declare variables: "
                + ", ".join(missing_declarations)
            )
        if dataset_columns is not None:
            validate_dataset_variables(prompt, dataset_columns)
        return prompt
    for variable in required_variables:
        if variable not in prompt_ref.template_variables:
            raise ConfigError(f"Prompt {prompt_ref.path} must declare variable {variable}")
        if "{{" + variable + "}}" not in prompt_text:
            raise ConfigError(f"Prompt {prompt_ref.path} must include {{{{{variable}}}}}")
    return prompt


def _validate_model_prompt_roles(model_config: ModelConfig, prompt: Any) -> None:
    if getattr(prompt, "shape", None) != "messages":
        return
    from evaluator_harness.providers.base import validate_provider_roles

    validate_provider_roles(
        model_config.provider,
        [message.role for message in prompt.messages],
    )


def _validate_prompt_file(path: Path, *, base: Path) -> str:
    prompt_path = path if path.is_absolute() else base / path
    if not prompt_path.exists():
        raise ConfigError(f"Prompt file not found: {path}")
    text = prompt_path.read_text(encoding="utf-8")
    if not text.strip():
        raise ConfigError(f"Prompt file is empty: {path}")
    return text


def _dataset_columns(config: ProjectConfig, *, base: Path) -> set[str] | None:
    if config.dataset.kind == DatasetKind.LANGFUSE or config.dataset.path is None:
        return None
    path = config.dataset.path if config.dataset.path.is_absolute() else base / config.dataset.path
    if not path.exists():
        return None
    if path.suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf-8-sig") as handle:
            return set(csv.DictReader(handle).fieldnames or [])
    if path.suffix.lower() == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, list):
            columns: set[str] = set()
            for row in data:
                if isinstance(row, dict):
                    columns.update(str(key) for key in row.keys())
            return columns
    return None


def _require_variables(evaluator: EvaluatorDefinition, variables: list[str]) -> None:
    missing = [variable for variable in variables if variable not in evaluator.variables]
    if missing:
        raise ConfigError(
            f"Evaluator {evaluator.name} missing variables: {', '.join(missing)}"
        )
