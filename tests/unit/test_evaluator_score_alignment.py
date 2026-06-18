from __future__ import annotations

from evaluator_harness.evaluators import managed_score_name, score_source_mapping
from evaluator_harness.config import ScoreSource, load_project_config
from evaluator_harness.langfuse_default_gateway import DefaultLangfuseGateway


def test_score_source_mapping_uses_langfuse_native_sources() -> None:
    assert score_source_mapping() == {
        "llm_judge": "EVAL",
        "human_annotation": "ANNOTATION",
        "api": "API",
    }


def test_evaluator_and_human_review_share_score_config_name() -> None:
    config = load_project_config("configs/projects/rewrite_quality.yaml")
    evaluator = config.evaluators[0]

    assert managed_score_name(config, evaluator.score) == "eh_rewrite_quality_clarity"
    assert ScoreSource.LLM_JUDGE in evaluator.score.allowed_score_sources
    assert ScoreSource.HUMAN_ANNOTATION in evaluator.score.allowed_score_sources


def test_sync_score_configs_reuses_single_score_for_judge_and_queue() -> None:
    config = load_project_config("configs/projects/rewrite_quality.yaml")
    client = DefaultLangfuseGateway()

    results = client.sync_score_configs(config)
    queue = client.create_annotation_queue(
        name="EH_rewrite-quality_v1_review_default",
        score_config_ids=[results[0].score_config_id],
    )

    assert results[0].name == "eh_rewrite_quality_clarity"
    assert queue["score_config_ids"] == [results[0].score_config_id]
