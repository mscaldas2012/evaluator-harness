from __future__ import annotations

import pytest

from evaluator_harness.config import ScoreSource, load_project_config
from evaluator_harness.errors import ConfigError
from evaluator_harness.langfuse_default_gateway import ScoreConfigSyncResult
from evaluator_harness.langfuse_evaluator_setup import resolve_score_target


def test_resolves_synced_score_config_for_evaluator_dimension() -> None:
    config = load_project_config("tests/fixtures/projects/valid_rewrite_quality.yaml")

    target = resolve_score_target(
        config.evaluators[0],
        [
            ScoreConfigSyncResult(
                evaluator_name="clarity",
                name="eh_rewrite_quality_clarity",
                score_config_id="score-config-1",
                status="reused",
                ownership="managed_by_harness",
            )
        ],
    )

    assert target.score_config_id == "score-config-1"
    assert target.name == "eh_rewrite_quality_clarity"


def test_requires_score_config_shared_with_human_annotation() -> None:
    evaluator = load_project_config("tests/fixtures/projects/valid_rewrite_quality.yaml").evaluators[0]
    evaluator.score.allowed_score_sources = [ScoreSource.LLM_JUDGE]

    with pytest.raises(ConfigError, match="Human Annotation"):
        resolve_score_target(evaluator, [])
