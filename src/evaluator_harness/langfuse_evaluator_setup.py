from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any

from evaluator_harness.config import (
    EvaluatorDefinition,
    EvaluatorSourceType,
    EvaluatorTarget,
    HistoricalBackfillPolicy,
    ProjectConfig,
    ScoreSource,
    validate_project_config,
)
from evaluator_harness.errors import ConfigError
from evaluator_harness.evaluator_bindings import (
    EvaluatorBindingRecord,
    EvaluatorBindingStore,
    load_evaluator_bindings,
    save_evaluator_bindings,
    validate_binding_path,
)
from evaluator_harness.evaluators import build_filter_profile, load_judge_prompt
from evaluator_harness.evaluators import prompt_placeholders
from evaluator_harness.langfuse_client import LangfuseClient, ScoreConfigSyncResult
from evaluator_harness.prompt_sync import prompt_provenance_metadata
from evaluator_harness.progress import NullProgressReporter, ProgressReporter


MANAGED_NAME_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")
SCORE_SOURCE_TERMS = ("_eval", "_annotation", "_human", "_llm_judge")
VARIABLE_PATHS = {
    "input": "observation.input",
    "output": "observation.output",
    "baseline_output": "trace.metadata.baseline_output",
    "ground_truth": "trace.metadata.ground_truth",
}
SAFE_UPDATE_FIELDS = {
    "filters",
    "sampling_percent",
    "variables",
    "catalog_ref",
    "active",
}


class EvaluatorOperation(str, Enum):
    CREATE = "create"
    REUSE = "reuse"
    UPDATE = "update"
    INACTIVATE = "inactivate"
    SKIP = "skip"
    BLOCK = "block"
    FAIL = "fail"


class BackfillStatus(str, Enum):
    DISABLED = "disabled"
    ENABLED = "enabled"
    UNSUPPORTED = "unsupported"
    NOT_APPLICABLE = "not_applicable"


@dataclass(frozen=True)
class ScoreTarget:
    name: str
    score_config_id: str


@dataclass
class EvaluatorSetupPlan:
    evaluator_name: str
    evaluator_version: str
    operation: EvaluatorOperation
    reason: str
    managed_display_name: str
    source_type: str
    target: str
    filters: dict[str, Any]
    variables: dict[str, str]
    score_target: ScoreTarget
    catalog_ref: str | None = None
    prompt: str | None = None
    prompt_version: str | None = None
    prompt_provenance: dict[str, Any] | None = None
    output_definition: dict[str, Any] | None = None
    judge_model: str | None = None
    llm_connection: str | None = None
    sampling_percent: int = 100
    backfill_status: BackfillStatus = BackfillStatus.DISABLED
    binding_status: str = "not-applicable"
    activation_state: str = "active"
    remote_evaluator_id: str | None = None
    changes: dict[str, Any] = field(default_factory=dict)
    remediation: str | None = None


@dataclass
class EvaluatorSetupResult:
    mode: str
    overall_status: str
    project: str
    project_version: str
    binding_path: Path
    evaluators: list[EvaluatorSetupPlan]
    warnings: list[str] = field(default_factory=list)


def build_managed_evaluator_name(
    *,
    project_slug: str,
    project_version: str,
    dimension: str,
    evaluator_version: str,
    source_type: str,
    target_type: str,
) -> str:
    name = (
        f"EH_{project_slug}_{project_version}_judge_"
        f"{dimension}_{evaluator_version}_{source_type}_{target_type}"
    )
    return validate_managed_evaluator_name(name)


def validate_managed_evaluator_name(name: str) -> str:
    if not MANAGED_NAME_PATTERN.fullmatch(name):
        raise ValueError("managed evaluator name must be slug-safe ASCII")
    lowered = name.lower()
    if any(lowered.endswith(term) for term in SCORE_SOURCE_TERMS):
        raise ValueError("managed evaluator name must not encode score source")
    return name


def effective_sampling_percent(config: ProjectConfig, evaluator: EvaluatorDefinition) -> int:
    return (
        evaluator.sampling_percent
        or config.judge_setup.default_sampling_percent
        or 100
    )


def effective_judge_model_or_connection(
    config: ProjectConfig,
    evaluator: EvaluatorDefinition,
) -> tuple[str, str] | tuple[None, None]:
    if evaluator.judge_model:
        return ("judge_model", evaluator.judge_model)
    if evaluator.llm_connection:
        return ("llm_connection", evaluator.llm_connection)
    if config.judge_setup.default_judge_model:
        return ("judge_model", config.judge_setup.default_judge_model)
    if config.judge_setup.default_llm_connection:
        return ("llm_connection", config.judge_setup.default_llm_connection)
    return (None, None)


def build_variable_mapping(evaluator: EvaluatorDefinition) -> dict[str, str]:
    declared = set(evaluator.variables)
    missing = [name for name in evaluator.required_inputs if name not in declared]
    if missing:
        raise ConfigError(
            f"Evaluator {evaluator.name} missing variable mappings: "
            + ", ".join(missing)
        )
    return {
        variable: VARIABLE_PATHS[variable]
        for variable in evaluator.variables
        if variable in VARIABLE_PATHS
    }


def build_prompt_variable_mapping(evaluator: EvaluatorDefinition) -> dict[str, str]:
    mapping = build_variable_mapping(evaluator)
    if evaluator.prompt_path is None:
        return mapping
    prompt = load_judge_prompt(evaluator.prompt_path)
    placeholders = prompt_placeholders(prompt.text)
    return {
        variable: path
        for variable, path in mapping.items()
        if variable in placeholders
    }


def resolve_score_target(
    evaluator: EvaluatorDefinition,
    score_results: list[ScoreConfigSyncResult],
) -> ScoreTarget:
    if ScoreSource.HUMAN_ANNOTATION not in evaluator.score.allowed_score_sources:
        raise ConfigError(
            f"Evaluator {evaluator.name} score config must be shared with Human Annotation"
        )
    for result in score_results:
        if result.evaluator_name == evaluator.name:
            return ScoreTarget(name=result.name, score_config_id=result.score_config_id)
    name = (
        str(evaluator.score.langfuse_score_config_id)
        if not evaluator.score.managed_by_harness
        else evaluator.score.name
    )
    return ScoreTarget(name=name, score_config_id=name)


def safe_update_changes(
    *,
    expected: dict[str, Any],
    remote: dict[str, Any],
) -> dict[str, Any]:
    changes: dict[str, Any] = {}
    for field_name in SAFE_UPDATE_FIELDS:
        if field_name == "filters" and _filters_compatible(
            expected.get(field_name) or {},
            remote.get(field_name) or {},
        ):
            continue
        if expected.get(field_name) != remote.get(field_name):
            changes[field_name] = expected.get(field_name)
    return changes


def _filters_compatible(expected: dict[str, Any], remote: dict[str, Any]) -> bool:
    if (
        remote.get("_has_top_level_environment_filter")
        or remote.get("_has_top_level_name_filter")
        or remote.get("_has_top_level_type_filter")
    ):
        return False
    if (
        expected.get("evaluator_set_id")
        and remote.get("_evaluator_set_id_operator") not in {None, "contains"}
    ):
        return False
    compared_keys = {
        "observation_role",
        "project",
        "project_version",
        "evaluator_set_id",
    }
    return all(expected.get(key) == remote.get(key) for key in compared_keys)


def plan_judge_evaluator_setup(
    config: ProjectConfig,
    client: LangfuseClient,
    score_results: list[ScoreConfigSyncResult],
    *,
    bindings: EvaluatorBindingStore | None = None,
    validate_config: bool = True,
    progress: ProgressReporter | None = None,
) -> EvaluatorSetupResult:
    if validate_config:
        validate_project_config(config)
    store = bindings or EvaluatorBindingStore()
    binding_path = _binding_path(config)
    judge_evaluators = [
        evaluator for evaluator in config.evaluators if evaluator.type == "llm_as_judge"
    ]
    plans = []
    reporter = progress or NullProgressReporter()
    with reporter.task("Planning judge evaluators", total=len(judge_evaluators)) as task:
        for evaluator in judge_evaluators:
            plans.append(_plan_one(config, evaluator, client, score_results, store))
            task.advance()
    for inactivation in _superseded_inactivation_plans(config, client, store, plans):
        plans.append(inactivation)
    return EvaluatorSetupResult(
        mode="preview",
        overall_status=_overall_status(plans),
        project=config.project.name,
        project_version=config.project.version,
        binding_path=binding_path,
        evaluators=plans,
    )


def apply_judge_evaluator_setup(
    config: ProjectConfig,
    client: LangfuseClient,
    score_results: list[ScoreConfigSyncResult],
    *,
    progress: ProgressReporter | None = None,
) -> EvaluatorSetupResult:
    validate_project_config(config)
    binding_path = _binding_path(config)
    store = load_evaluator_bindings(binding_path)
    result = plan_judge_evaluator_setup(
        config,
        client,
        score_results,
        bindings=store,
    )
    result.mode = "apply"
    applied: list[EvaluatorSetupPlan] = []
    reporter = progress or NullProgressReporter()
    with reporter.task("Applying judge evaluators", total=len(result.evaluators)) as task:
        for plan in result.evaluators:
            try:
                if plan.operation in {EvaluatorOperation.BLOCK, EvaluatorOperation.FAIL}:
                    applied.append(plan)
                    continue
                if plan.operation == EvaluatorOperation.CREATE:
                    created = client.create_evaluator(_payload_from_plan(plan))
                    plan.remote_evaluator_id = str(created["id"])
                    plan.binding_status = "created"
                    _upsert_binding(config, store, plan)
                    save_evaluator_bindings(binding_path, store)
                elif plan.operation == EvaluatorOperation.UPDATE:
                    updated = client.update_evaluator(str(plan.remote_evaluator_id), plan.changes)
                    plan.remote_evaluator_id = str(updated["id"])
                    plan.binding_status = "refreshed"
                    _upsert_binding(config, store, plan)
                    save_evaluator_bindings(binding_path, store)
                elif plan.operation == EvaluatorOperation.INACTIVATE:
                    client.inactivate_evaluator(
                        str(plan.remote_evaluator_id),
                        comment=f"Superseded by {plan.evaluator_name}/{plan.evaluator_version}",
                    )
                    plan.activation_state = "inactive"
                applied.append(plan)
            except (ConfigError, NotImplementedError, RuntimeError) as exc:
                plan.operation = EvaluatorOperation.FAIL
                plan.reason = str(exc)
                plan.remediation = "Resolve the reported Langfuse evaluator setup issue and rerun."
                applied.append(plan)
            finally:
                task.advance()
    result.evaluators = applied
    result.overall_status = _overall_status(applied)
    save_evaluator_bindings(binding_path, store)
    return result


def audit_judge_evaluator_setup(
    config: ProjectConfig,
    client: LangfuseClient,
    score_results: list[ScoreConfigSyncResult],
    *,
    bindings: EvaluatorBindingStore | None = None,
    progress: ProgressReporter | None = None,
) -> EvaluatorSetupResult:
    result = plan_judge_evaluator_setup(
        config,
        client,
        score_results,
        bindings=bindings or EvaluatorBindingStore(),
        progress=progress,
    )
    result.mode = "audit"
    return result


def _plan_one(
    config: ProjectConfig,
    evaluator: EvaluatorDefinition,
    client: LangfuseClient,
    score_results: list[ScoreConfigSyncResult],
    bindings: EvaluatorBindingStore,
) -> EvaluatorSetupPlan:
    target = (evaluator.target or EvaluatorTarget.OBSERVATION).value
    source_type = evaluator.source_type.value
    display_name = evaluator.managed_display_name or build_managed_evaluator_name(
        project_slug=config.project.name,
        project_version=config.project.version,
        dimension=evaluator.dimension or evaluator.name,
        evaluator_version=evaluator.version,
        source_type=source_type,
        target_type=target,
    )
    score_target = resolve_score_target(evaluator, score_results)
    try:
        filters = build_filter_profile(config, evaluator).model_dump(
            mode="json",
            exclude_none=True,
        )
    except ConfigError as exc:
        return _blocked_plan(config, evaluator, display_name, source_type, target, score_target, str(exc))
    if not filters.get("project") or not filters.get("project_version"):
        return _blocked_plan(
            config,
            evaluator,
            display_name,
            source_type,
            target,
            score_target,
            "Evaluator filter is too broad; add project and project_version filters.",
        )
    raw_profile = evaluator.filter_profile
    if raw_profile is not None and (
        not raw_profile.project
        or not raw_profile.project_version
        or not raw_profile.evaluator_set_id
    ):
        return _blocked_plan(
            config,
            evaluator,
            display_name,
            source_type,
            target,
            score_target,
            "Evaluator filter is too broad; add project, project_version, and evaluator_set_id filters.",
        )
    judge_kind, judge_value = effective_judge_model_or_connection(config, evaluator)
    if judge_kind is None:
        return _blocked_plan(
            config,
            evaluator,
            display_name,
            source_type,
            target,
            score_target,
            "Configure a judge model or LLM connection.",
        )
    backfill = _backfill_status(config, evaluator, target, client)
    if backfill == BackfillStatus.UNSUPPORTED:
        return _blocked_plan(
            config,
            evaluator,
            display_name,
            source_type,
            target,
            score_target,
            "Historical backfill is not supported for this evaluator target.",
            backfill_status=backfill,
        )
    try:
        variables = build_prompt_variable_mapping(evaluator)
    except ConfigError as exc:
        return _blocked_plan(config, evaluator, display_name, source_type, target, score_target, str(exc))
    binding = bindings.find(
        project=config.project.name,
        project_version=config.project.version,
        evaluator_name=evaluator.name,
        evaluator_version=evaluator.version,
        source_type=source_type,
        target=target,
    )
    remote = _find_remote(client, display_name, binding)
    base = EvaluatorSetupPlan(
        evaluator_name=evaluator.name,
        evaluator_version=evaluator.version,
        operation=EvaluatorOperation.CREATE,
        reason="No compatible remote evaluator found.",
        managed_display_name=display_name,
        source_type=source_type,
        target=target,
        filters=filters,
        variables=variables,
        score_target=score_target,
        catalog_ref=evaluator.catalog_ref,
        prompt=_prompt_text(evaluator),
        prompt_version=evaluator.prompt_version,
        prompt_provenance=prompt_provenance_metadata(
            config,
            artifact_type="evaluator",
            artifact_name=evaluator.name,
        ),
        output_definition=_output_definition(evaluator),
        judge_model=judge_value if judge_kind == "judge_model" else None,
        llm_connection=judge_value if judge_kind == "llm_connection" else None,
        sampling_percent=effective_sampling_percent(config, evaluator),
        backfill_status=backfill,
        binding_status="will-create",
        activation_state="active-on-apply",
        remote_evaluator_id=evaluator.remote_evaluator_id,
    )
    if evaluator.source_type == EvaluatorSourceType.USER_OWNED:
        base.operation = EvaluatorOperation.SKIP
        base.reason = "User-owned evaluator is validated without mutation."
        base.binding_status = "not-applicable"
        return base
    if remote is None:
        return base
    base.remote_evaluator_id = str(remote.get("id"))
    if binding is None:
        base.operation = EvaluatorOperation.BLOCK
        base.reason = "Remote evaluator display name exists without local binding."
        base.binding_status = "missing"
        base.remediation = (
            "Missing local binding. Treat it as user-owned or create a new "
            "harness-managed version."
        )
        return base
    expected = _payload_from_plan(base)
    changes = safe_update_changes(expected=expected, remote=remote)
    if changes:
        base.operation = EvaluatorOperation.UPDATE
        base.reason = "Harness-managed evaluator has update-safe differences."
        base.changes = changes
        base.binding_status = "present"
    else:
        base.operation = EvaluatorOperation.REUSE
        base.reason = "Compatible harness-managed evaluator already exists."
        base.binding_status = "present"
    return base


def _blocked_plan(
    config: ProjectConfig,
    evaluator: EvaluatorDefinition,
    display_name: str,
    source_type: str,
    target: str,
    score_target: ScoreTarget,
    remediation: str,
    *,
    backfill_status: BackfillStatus = BackfillStatus.DISABLED,
) -> EvaluatorSetupPlan:
    return EvaluatorSetupPlan(
        evaluator_name=evaluator.name,
        evaluator_version=evaluator.version,
        operation=EvaluatorOperation.BLOCK,
        reason=remediation,
        managed_display_name=display_name,
        source_type=source_type,
        target=target,
        filters={},
        variables={},
        score_target=score_target,
        catalog_ref=evaluator.catalog_ref,
        prompt=_prompt_text(evaluator),
        prompt_version=evaluator.prompt_version,
        output_definition=_output_definition(evaluator),
        sampling_percent=effective_sampling_percent(config, evaluator),
        backfill_status=backfill_status,
        binding_status="not-applicable",
        remediation=remediation,
    )


def _find_remote(
    client: LangfuseClient,
    display_name: str,
    binding: EvaluatorBindingRecord | None,
) -> dict[str, Any] | None:
    for evaluator in client.list_evaluators():
        if binding and evaluator.get("id") == binding.langfuse_evaluator_id:
            return evaluator
        if evaluator.get("display_name") == display_name or evaluator.get("name") == display_name:
            return evaluator
    return None


def _payload_from_plan(plan: EvaluatorSetupPlan) -> dict[str, Any]:
    return {
        "display_name": plan.managed_display_name,
        "source_type": plan.source_type,
        "target": plan.target,
        "filters": plan.filters,
        "variables": plan.variables,
        "catalog_ref": plan.catalog_ref,
        "prompt": plan.prompt,
        "prompt_version": plan.prompt_version,
        "prompt_provenance": plan.prompt_provenance,
        "output_definition": plan.output_definition,
        "score_config_id": plan.score_target.score_config_id,
        "score_config_name": plan.score_target.name,
        "judge_model": plan.judge_model,
        "llm_connection": plan.llm_connection,
        "sampling_percent": plan.sampling_percent,
        "backfill_status": plan.backfill_status.value,
        "active": True,
    }


def _prompt_text(evaluator: EvaluatorDefinition) -> str | None:
    if evaluator.source_type != EvaluatorSourceType.CUSTOM or evaluator.prompt_path is None:
        return None
    return load_judge_prompt(evaluator.prompt_path).text


def _output_definition(evaluator: EvaluatorDefinition) -> dict[str, Any] | None:
    if evaluator.source_type != EvaluatorSourceType.CUSTOM:
        return None
    data_type = evaluator.score.data_type.value
    description = evaluator.score.description or f"{evaluator.name} score."
    base: dict[str, Any] = {
        "dataType": data_type,
        "reasoning": {"description": "Explain the score."},
        "score": {
            "description": (
                f"{description} Return a value from "
                f"{evaluator.score.min_value} to {evaluator.score.max_value}."
            ),
            "minValue": evaluator.score.min_value,
            "maxValue": evaluator.score.max_value,
        },
    }
    if data_type == "CATEGORICAL":
        base["score"]["categories"] = evaluator.score.categories or []
        base["score"]["shouldAllowMultipleMatches"] = False
    return base


def _binding_path(config: ProjectConfig) -> Path:
    path = config.judge_setup.binding_path or Path(
        "configs/langfuse/evaluator_bindings"
    ) / f"{config.project.name}.yaml"
    return validate_binding_path(path)


def _backfill_status(
    config: ProjectConfig,
    evaluator: EvaluatorDefinition,
    target: str,
    client: LangfuseClient,
) -> BackfillStatus:
    requested = evaluator.historical_backfill or config.judge_setup.historical_backfill
    if requested != HistoricalBackfillPolicy.ENABLED:
        return BackfillStatus.DISABLED
    if client.supports_evaluator_backfill(target):
        return BackfillStatus.ENABLED
    return BackfillStatus.UNSUPPORTED


def _superseded_inactivation_plans(
    config: ProjectConfig,
    client: LangfuseClient,
    bindings: EvaluatorBindingStore,
    active_plans: list[EvaluatorSetupPlan],
) -> list[EvaluatorSetupPlan]:
    new_keys = {
        (
            plan.evaluator_name,
            plan.source_type,
            plan.target,
        )
        for plan in active_plans
        if plan.operation in {EvaluatorOperation.CREATE, EvaluatorOperation.UPDATE, EvaluatorOperation.REUSE}
    }
    inactivations: list[EvaluatorSetupPlan] = []
    for binding in bindings.bindings:
        if binding.project != config.project.name or binding.project_version != config.project.version:
            continue
        if not binding.active:
            continue
        key = (binding.evaluator_name, binding.source_type, binding.target)
        if key not in new_keys:
            continue
        if any(plan.evaluator_version == binding.evaluator_version for plan in active_plans):
            continue
        remote = client.get_evaluator(binding.langfuse_evaluator_id)
        if remote is None or not remote.get("active", True):
            continue
        inactivations.append(
            EvaluatorSetupPlan(
                evaluator_name=binding.evaluator_name,
                evaluator_version=binding.evaluator_version,
                operation=EvaluatorOperation.INACTIVATE,
                reason="Superseded by newer harness-managed evaluator version.",
                managed_display_name=binding.langfuse_display_name,
                source_type=binding.source_type,
                target=binding.target,
                filters=remote.get("filters", {}),
                variables=remote.get("variables", {}),
                score_target=ScoreTarget(
                    name=binding.score_config_name,
                    score_config_id=binding.score_config_id,
                ),
                judge_model=binding.judge_model,
                llm_connection=binding.llm_connection,
                sampling_percent=binding.sampling_percent,
                backfill_status=(
                    BackfillStatus.ENABLED
                    if binding.historical_backfill
                    else BackfillStatus.DISABLED
                ),
                binding_status="present",
                remote_evaluator_id=binding.langfuse_evaluator_id,
                changes={"active": False},
            )
        )
    return inactivations


def _upsert_binding(
    config: ProjectConfig,
    store: EvaluatorBindingStore,
    plan: EvaluatorSetupPlan,
) -> None:
    store.upsert(
        EvaluatorBindingRecord(
            project=config.project.name,
            project_version=config.project.version,
            evaluator_name=plan.evaluator_name,
            evaluator_version=plan.evaluator_version,
            source_type=plan.source_type,
            target=plan.target,
            langfuse_evaluator_id=str(plan.remote_evaluator_id),
            langfuse_display_name=plan.managed_display_name,
            score_config_id=plan.score_target.score_config_id,
            score_config_name=plan.score_target.name,
            judge_model=plan.judge_model,
            llm_connection=plan.llm_connection,
            sampling_percent=plan.sampling_percent,
            historical_backfill=plan.backfill_status == BackfillStatus.ENABLED,
            active=True,
            last_synced_at=datetime.now(UTC).isoformat(),
        )
    )


def _overall_status(plans: list[EvaluatorSetupPlan]) -> str:
    if not plans:
        return "success"
    failures = [
        plan for plan in plans if plan.operation in {EvaluatorOperation.BLOCK, EvaluatorOperation.FAIL}
    ]
    if not failures:
        return "success"
    if len(failures) == len(plans):
        return "failure"
    return "partial_success"
