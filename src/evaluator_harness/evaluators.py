from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

from evaluator_harness.config import (
    EvaluatorDefinition,
    EvaluatorFilterProfile,
    EvaluatorMode,
    EvaluatorRunType,
    EvaluatorSourceType,
    EvaluatorTarget,
    ProjectConfig,
    ScoreConfigRef,
    ScoreSource,
)
from evaluator_harness.errors import ConfigError


PROVIDER_IDENTITY_PLACEHOLDERS = {
    "provider",
    "model",
    "model_name",
    "vendor",
    "run_label",
    "run_name",
}

QUALITY_DIMENSION_WORDS = {
    "clarity",
    "tone",
    "factual",
    "factuality",
    "consistency",
    "brevity",
    "toxicity",
    "grammar",
    "hallucination",
    "brand",
}

SCORE_SOURCE_MAPPING = {
    ScoreSource.LLM_JUDGE: "EVAL",
    ScoreSource.HUMAN_ANNOTATION: "ANNOTATION",
    ScoreSource.API: "API",
}


@dataclass(frozen=True)
class JudgePrompt:
    path: Path
    text: str


def load_judge_prompt(path: Path | str, *, base: Path | None = None) -> JudgePrompt:
    prompt_path = Path(path)
    if not prompt_path.is_absolute():
        prompt_path = (base or Path.cwd()) / prompt_path
    if not prompt_path.exists():
        raise ConfigError(f"Judge prompt file not found: {path}")
    text = prompt_path.read_text(encoding="utf-8")
    if not text.strip():
        raise ConfigError(f"Judge prompt file is empty: {path}")
    return JudgePrompt(path=prompt_path, text=text)


def prompt_placeholders(text: str) -> set[str]:
    return set(re.findall(r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}", text))


def assert_prompt_is_single_dimension(prompt: JudgePrompt, *, dimension: str) -> None:
    lower = prompt.text.lower()
    positive_text = "\n".join(
        line
        for line in lower.splitlines()
        if "do not" not in line and "ignore" not in line
    )
    mentioned = {
        word
        for word in QUALITY_DIMENSION_WORDS
        if word in positive_text and word not in {dimension.lower()}
    }
    if mentioned:
        raise ConfigError(
            f"Evaluator prompt for {dimension} must evaluate one dimension only"
        )


def assert_blind_prompt(prompt: JudgePrompt, evaluator: EvaluatorDefinition) -> None:
    if not evaluator.blind:
        return
    forbidden = sorted(PROVIDER_IDENTITY_PLACEHOLDERS & prompt_placeholders(prompt.text))
    if forbidden:
        raise ConfigError(
            f"Blind evaluator {evaluator.name} prompt exposes identity placeholders: "
            + ", ".join(forbidden)
        )


def build_filter_profile(
    config: ProjectConfig,
    evaluator: EvaluatorDefinition,
) -> EvaluatorFilterProfile:
    profile = evaluator.filter_profile or EvaluatorFilterProfile()
    return profile.model_copy(
        update={
            "target": profile.target or evaluator.target or EvaluatorTarget.OBSERVATION,
            "observation_role": (
                profile.observation_role
                or evaluator.target_observation_role
                or "model_output"
            ),
            "observation_name": (
                profile.observation_name or evaluator.target_observation_name
            ),
            "project": profile.project or config.project.name,
            "project_version": profile.project_version or config.project.version,
            "evaluator_set_id": profile.evaluator_set_id
            or f"{evaluator.name}:{evaluator.version}",
            "environment": profile.environment
            or config.project.metadata.get("environment"),
            "run_types": profile.run_types or evaluator.run_types or [],
        }
    )


def managed_score_name(config: ProjectConfig, score: ScoreConfigRef) -> str:
    return (
        f"{config.project.score_config_prefix}{score.name}"
        if score.managed_by_harness
        else str(score.langfuse_score_config_id)
    )


def score_source_mapping() -> dict[str, str]:
    return {source.value: langfuse_source for source, langfuse_source in SCORE_SOURCE_MAPPING.items()}


def validate_evaluators(config: ProjectConfig, *, base: Path | None = None) -> None:
    for evaluator in config.evaluators:
        _validate_evaluator(config, evaluator, base=base)


def _validate_evaluator(
    config: ProjectConfig,
    evaluator: EvaluatorDefinition,
    *,
    base: Path | None,
) -> None:
    if (
        evaluator.type == "llm_as_judge"
        and evaluator.source_type == EvaluatorSourceType.CUSTOM
        and evaluator.prompt_path is None
    ):
        raise ConfigError(f"Evaluator {evaluator.name} requires prompt_path")
    if evaluator.target is None:
        raise ConfigError(f"Evaluator {evaluator.name} requires target")
    if not evaluator.run_types:
        raise ConfigError(f"Evaluator {evaluator.name} requires run_types")
    if evaluator.mode is None:
        raise ConfigError(f"Evaluator {evaluator.name} requires mode")
    if evaluator.output_schema is None:
        raise ConfigError(f"Evaluator {evaluator.name} requires output_schema")
    if (
        evaluator.filter_profile is None
        and evaluator.target is None
        and evaluator.output_schema is None
    ):
        raise ConfigError(f"Evaluator {evaluator.name} requires filter_profile")
    if not evaluator.score:
        raise ConfigError(f"Evaluator {evaluator.name} requires score target")
    if evaluator.target == EvaluatorTarget.OBSERVATION and not evaluator.target_observation_role:
        raise ConfigError(f"Evaluator {evaluator.name} requires target_observation_role")
    if evaluator.mode == EvaluatorMode.BASELINE_COMPARISON and "baseline_output" not in evaluator.required_inputs:
        raise ConfigError(
            f"Evaluator {evaluator.name} baseline_comparison requires baseline_output"
        )

    required_by_run_type = {
        EvaluatorRunType.BASELINE: {"input", "output"},
        EvaluatorRunType.CANDIDATE: {"input", "output"},
    }
    for run_type in evaluator.run_types:
        missing = required_by_run_type[run_type] - set(evaluator.required_inputs)
        if missing:
            raise ConfigError(
                f"Evaluator {evaluator.name} missing required inputs: "
                + ", ".join(sorted(missing))
            )

    raw_profile = evaluator.filter_profile
    if raw_profile is not None and (
        not raw_profile.project
        or not raw_profile.project_version
        or not raw_profile.evaluator_set_id
    ):
        raise ConfigError(f"Evaluator {evaluator.name} filter is too broad")
    profile = build_filter_profile(config, evaluator)
    if profile.target == EvaluatorTarget.OBSERVATION and not profile.observation_role:
        raise ConfigError(f"Evaluator {evaluator.name} filter requires observation_role")
    if profile.project != config.project.name:
        raise ConfigError(f"Evaluator {evaluator.name} filter project does not match project")

    if evaluator.prompt_path is not None:
        prompt = load_judge_prompt(evaluator.prompt_path, base=base)
        assert_prompt_is_single_dimension(prompt, dimension=evaluator.dimension or evaluator.name)
        assert_blind_prompt(prompt, evaluator)


def evaluator_target_summary(evaluator: EvaluatorDefinition) -> str:
    target = evaluator.target.value if evaluator.target else "unknown"
    role = evaluator.target_observation_role or "trace"
    return f"{evaluator.name}={target}/{role}"


def evaluator_score_summary(config: ProjectConfig, evaluator: EvaluatorDefinition) -> str:
    return f"{evaluator.name}={managed_score_name(config, evaluator.score)}"


@dataclass(frozen=True)
class RenderedJudgePrompt:
    evaluator_name: str
    evaluator_version: str
    target: str
    source_type: str
    catalog_ref: str | None
    score: str
    shared_with_human_annotation_queue: bool
    score_sources: dict[str, str]
    filters: EvaluatorFilterProfile
    prompt_path: Path | None
    prompt_text: str
    judge_model: str | None = None
    llm_connection: str | None = None
    sampling_percent: int = 100
    historical_backfill: str = "disabled"
    binding_path: Path | None = None


def render_judge_prompt(config: ProjectConfig, evaluator: EvaluatorDefinition) -> RenderedJudgePrompt:
    profile = build_filter_profile(config, evaluator)
    prompt = (
        load_judge_prompt(evaluator.prompt_path).text
        if evaluator.prompt_path is not None
        else ""
    )
    judge_model = evaluator.judge_model or config.judge_setup.default_judge_model
    llm_connection = evaluator.llm_connection or config.judge_setup.default_llm_connection
    return RenderedJudgePrompt(
        evaluator_name=evaluator.name,
        evaluator_version=evaluator.version,
        target=f"{profile.target.value} role={profile.observation_role}",
        source_type=evaluator.source_type.value,
        catalog_ref=evaluator.catalog_ref,
        score=managed_score_name(config, evaluator.score),
        shared_with_human_annotation_queue=config.human_review.enabled,
        score_sources=score_source_mapping(),
        filters=profile,
        prompt_path=evaluator.prompt_path,
        prompt_text=prompt,
        judge_model=judge_model,
        llm_connection=llm_connection,
        sampling_percent=(
            evaluator.sampling_percent
            or config.judge_setup.default_sampling_percent
            or 100
        ),
        historical_backfill=(
            evaluator.historical_backfill or config.judge_setup.historical_backfill
        ).value,
        binding_path=config.judge_setup.binding_path
        or Path("configs/langfuse/evaluator_bindings") / f"{config.project.name}.yaml",
    )


def render_judge_prompts(config: ProjectConfig) -> list[RenderedJudgePrompt]:
    return [render_judge_prompt(config, evaluator) for evaluator in config.evaluators]


def sanitized_judge_input_package(
    *,
    evaluator: EvaluatorDefinition,
    input: str,
    output: str,
    baseline_output: str | None = None,
    ground_truth: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    package: dict[str, Any] = {
        "input": input,
        "output": output,
        "baseline_output": baseline_output,
        "ground_truth": ground_truth,
        "anonymous_labels": {"output": "Output A", "baseline_output": "Output B"},
        "metadata": {
            "evaluator_name": evaluator.name,
            "evaluator_version": evaluator.version,
            "dimension": evaluator.dimension,
        },
    }
    if metadata and not evaluator.blind:
        package["metadata"].update(metadata)
    return package


def validate_judge_result_contract(
    evaluator: EvaluatorDefinition,
    *,
    example: dict[str, Any] | None = None,
) -> None:
    if evaluator.output_schema is None:
        raise ConfigError(f"Evaluator {evaluator.name} requires output_schema")
    if example is None:
        return
    missing = [field for field in ("reasoning", "score", "confidence") if field not in example]
    if missing:
        raise ConfigError("Judge result example missing fields: " + ", ".join(missing))
    score = float(example["score"])
    if not evaluator.output_schema.score.minimum <= score <= evaluator.output_schema.score.maximum:
        raise ConfigError(f"Judge result score is outside configured score range")


def export_evaluator_setup(config: ProjectConfig, output_path: Path) -> Path:
    rendered = render_judge_prompts(config)
    lines = [
        f"# Evaluator Setup: {config.project.name}/{config.project.version}",
        "",
    ]
    for item in rendered:
        lines.extend(
            [
                f"## {item.evaluator_name}/{item.evaluator_version}",
                "",
                f"- source_type: {item.source_type}",
                f"- catalog_ref: {item.catalog_ref or ''}",
                f"- target: {item.target}",
                f"- score: {item.score}",
                f"- judge_model: {item.judge_model or ''}",
                f"- llm_connection: {item.llm_connection or ''}",
                f"- sampling: {item.sampling_percent}",
                f"- historical_backfill: {item.historical_backfill}",
                f"- binding_path: {item.binding_path}",
                f"- shared_with_human_annotation_queue: {str(item.shared_with_human_annotation_queue).lower()}",
                "- score_sources:",
            ]
        )
        for source, langfuse_source in item.score_sources.items():
            lines.append(f"  - {source}: {langfuse_source}")
        lines.extend(
            [
                "- filters:",
                f"  - project: {item.filters.project}",
                f"  - project_version: {item.filters.project_version}",
                f"  - evaluator_set_id: {item.filters.evaluator_set_id}",
                f"  - observation_role: {item.filters.observation_role}",
                f"- prompt: {item.prompt_path}",
                "",
            ]
        )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    return output_path
