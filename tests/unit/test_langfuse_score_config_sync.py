from __future__ import annotations

import pytest

from evaluator_harness.config import load_project_config
from evaluator_harness.errors import ConfigError
from evaluator_harness.langfuse_client import LangfuseClient


def test_score_config_sync_creates_missing_managed_config() -> None:
    config = load_project_config("configs/projects/rewrite_quality.yaml")
    client = LangfuseClient()

    results = client.sync_score_configs(config)

    assert results[0].name == "eh_rewrite_quality_clarity"
    assert results[0].status == "created"
    assert "eh_rewrite_quality_clarity" in client.score_configs


def test_score_config_sync_reuses_compatible_config() -> None:
    config = load_project_config("configs/projects/rewrite_quality.yaml")
    client = LangfuseClient()

    client.sync_score_configs(config)
    results = client.sync_score_configs(config)

    assert results[0].status == "reused"


def test_score_config_sync_reuses_existing_live_config_by_name() -> None:
    class FakeScoreConfigsApi:
        def get(self, *, limit):
            return type(
                "Page",
                (),
                {
                    "data": [
                        {
                            "id": "live-score-config-1",
                            "name": "eh_rewrite_quality_clarity",
                            "data_type": "NUMERIC",
                            "min_value": 0,
                            "max_value": 1,
                            "categories": None,
                            "is_archived": False,
                        }
                    ]
                },
            )()

        def create(self, **kwargs):
            raise AssertionError("score config should be reused instead of created")

    client = LangfuseClient(
        client=type("FakeClient", (), {"api": type("Api", (), {"score_configs": FakeScoreConfigsApi()})()})()
    )
    config = load_project_config("configs/projects/rewrite_quality.yaml")

    results = client.sync_score_configs(config)

    assert results[0].status == "reused"
    assert results[0].score_config_id == "live-score-config-1"


def test_score_config_sync_normalizes_live_camel_case_schema() -> None:
    class FakeScoreConfigsApi:
        def get(self, *, limit):
            return type(
                "Page",
                (),
                {
                    "data": [
                        {
                            "id": "live-score-config-1",
                            "name": "eh_rewrite_quality_clarity",
                            "dataType": "NUMERIC",
                            "minValue": 0.0,
                            "maxValue": 1.0,
                            "categories": None,
                            "isArchived": False,
                        }
                    ]
                },
            )()

    client = LangfuseClient(
        client=type("FakeClient", (), {"api": type("Api", (), {"score_configs": FakeScoreConfigsApi()})()})()
    )
    config = load_project_config("configs/projects/rewrite_quality.yaml")

    results = client.sync_score_configs(config)

    assert results[0].status == "reused"


def test_score_config_sync_validates_user_owned_reference() -> None:
    config = load_project_config("configs/projects/rewrite_quality.yaml")
    config.evaluators[0].score.managed_by_harness = False
    config.evaluators[0].score.langfuse_score_config_id = "score-config-123"
    client = LangfuseClient()

    results = client.sync_score_configs(config)

    assert results[0].status == "user_owned"


def test_score_config_sync_fails_incompatible_schema() -> None:
    config = load_project_config("configs/projects/rewrite_quality.yaml")
    client = LangfuseClient()
    client.score_configs["eh_rewrite_quality_clarity"] = {
        "id": "existing",
        "name": "eh_rewrite_quality_clarity",
        "data_type": "CATEGORICAL",
        "archived": False,
    }

    with pytest.raises(ConfigError, match="incompatible"):
        client.sync_score_configs(config)


def test_score_config_sync_fails_archived_same_name() -> None:
    config = load_project_config("configs/projects/rewrite_quality.yaml")
    client = LangfuseClient()
    client.score_configs["eh_rewrite_quality_clarity"] = {
        "id": "existing",
        "name": "eh_rewrite_quality_clarity",
        "data_type": "NUMERIC",
        "min_value": 0,
        "max_value": 1,
        "archived": True,
    }

    with pytest.raises(ConfigError, match="archived"):
        client.sync_score_configs(config)
