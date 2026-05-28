from __future__ import annotations

from pathlib import Path

import pytest

from evaluator_harness.config import (
    EvaluatorSourceType,
    HistoricalBackfillPolicy,
    load_project_config,
    validate_project_config,
)
from evaluator_harness.errors import ConfigError
from evaluator_harness.langfuse_evaluator_setup import (
    effective_judge_model_or_connection,
    effective_sampling_percent,
)


def test_judge_setup_defaults_and_custom_source_parse() -> None:
    config = load_project_config("tests/fixtures/projects/valid_rewrite_quality.yaml")
    evaluator = config.evaluators[0]

    assert config.judge_setup.default_judge_model == "gpt-4.1"
    assert config.judge_setup.binding_path == Path(
        "configs/langfuse/evaluator_bindings/rewrite-quality.yaml"
    )
    assert evaluator.source_type == EvaluatorSourceType.CUSTOM
    assert evaluator.sampling_percent is None
    assert evaluator.historical_backfill is None
    assert effective_sampling_percent(config, evaluator) == 100
    assert effective_judge_model_or_connection(config, evaluator) == ("judge_model", "gpt-4.1")


def test_catalog_evaluator_requires_catalog_ref() -> None:
    config = load_project_config("tests/fixtures/projects/valid_catalog_judge_setup.yaml")
    evaluator = config.evaluators[0]

    assert evaluator.source_type == EvaluatorSourceType.CATALOG
    assert evaluator.catalog_ref == "langfuse/helpfulness"
    validate_project_config(config)

    evaluator.catalog_ref = None
    with pytest.raises(ConfigError, match="catalog_ref"):
        validate_project_config(config)


def test_missing_judge_connection_is_invalid_for_setup() -> None:
    config = load_project_config("tests/fixtures/projects/invalid_judge_setup_missing_connection.yaml")

    with pytest.raises(ConfigError, match="judge model or LLM connection"):
        validate_project_config(config)


def test_custom_evaluator_requires_prompt_and_result_contract(tmp_path: Path) -> None:
    project = tmp_path / "project.yaml"
    text = Path("tests/fixtures/projects/valid_rewrite_quality.yaml").read_text(
        encoding="utf-8"
    )
    text = text.replace("    prompt_path: prompts/rewrite_quality/evaluators/clarity.md\n", "")
    project.write_text(text, encoding="utf-8")

    with pytest.raises(ConfigError, match="prompt_path"):
        validate_project_config(load_project_config(project))


def test_evaluator_override_judge_connection_and_backfill_policy() -> None:
    config = load_project_config("tests/fixtures/projects/valid_catalog_judge_setup.yaml")
    evaluator = config.evaluators[0]

    assert effective_judge_model_or_connection(config, evaluator) == (
        "llm_connection",
        "lf-connection-catalog",
    )
    assert config.judge_setup.historical_backfill == HistoricalBackfillPolicy.DISABLED
