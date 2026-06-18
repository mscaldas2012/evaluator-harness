from __future__ import annotations

import pytest

from evaluator_harness.config import load_project_config
from evaluator_harness.errors import ConfigError, LangfuseError
from evaluator_harness.langfuse_default_gateway import DefaultLangfuseGateway


def _fake_score_config_client(api):
    return type(
        "FakeClient",
        (),
        {"api": type("Api", (), {"score_configs": api})()},
    )()


def test_score_config_sync_creates_missing_managed_config() -> None:
    config = load_project_config("configs/projects/rewrite_quality.yaml")
    client = DefaultLangfuseGateway()

    results = client.sync_score_configs(config)

    assert results[0].name == "eh_rewrite_quality_clarity"
    assert results[0].status == "created"
    assert "eh_rewrite_quality_clarity" in client.score_configs


def test_score_config_sync_facade_uses_gateway_boundary_without_live_client() -> None:
    config = load_project_config("configs/projects/rewrite_quality.yaml")
    client = DefaultLangfuseGateway()

    results = client.sync_score_configs(config)

    assert results[0].status == "created"
    assert client._gateway.owner is client
    assert ("sync_score_configs", {"count": 1, "dry_run": False}) in client.calls


def test_score_config_sync_dry_run_reports_missing_managed_config() -> None:
    config = load_project_config("configs/projects/rewrite_quality.yaml")
    client = DefaultLangfuseGateway()

    results = client.sync_score_configs(config, dry_run=True)

    assert results[0].name == "eh_rewrite_quality_clarity"
    assert results[0].status == "planned_create"
    assert results[0].score_config_id == ""
    assert "eh_rewrite_quality_clarity" not in client.score_configs


def test_score_config_sync_reuses_compatible_config() -> None:
    config = load_project_config("configs/projects/rewrite_quality.yaml")
    client = DefaultLangfuseGateway()

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

    client = DefaultLangfuseGateway(client=_fake_score_config_client(FakeScoreConfigsApi()))
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

    client = DefaultLangfuseGateway(client=_fake_score_config_client(FakeScoreConfigsApi()))
    config = load_project_config("configs/projects/rewrite_quality.yaml")

    results = client.sync_score_configs(config)

    assert results[0].status == "reused"


def test_live_score_config_creation_requires_real_id() -> None:
    class FakeScoreConfigsApi:
        def get(self, *, limit):
            return type("Page", (), {"data": []})()

        def create(self, **kwargs):
            return type("Created", (), {})()

    client = DefaultLangfuseGateway(client=_fake_score_config_client(FakeScoreConfigsApi()))
    config = load_project_config("configs/projects/rewrite_quality.yaml")

    with pytest.raises(LangfuseError, match="missing id"):
        client.sync_score_configs(config)


def test_live_score_config_creation_returns_real_id() -> None:
    class FakeScoreConfigsApi:
        def get(self, *, limit):
            return type("Page", (), {"data": []})()

        def create(self, **kwargs):
            return type("Created", (), {"id": "live-score-config-created"})()

    client = DefaultLangfuseGateway(client=_fake_score_config_client(FakeScoreConfigsApi()))
    config = load_project_config("configs/projects/rewrite_quality.yaml")

    results = client.sync_score_configs(config)

    assert results[0].status == "created"
    assert results[0].score_config_id == "live-score-config-created"


def test_live_score_config_list_retries_rate_limits() -> None:
    class FakeScoreConfigsApi:
        def __init__(self) -> None:
            self.get_calls = 0

        def get(self, *, limit):
            self.get_calls += 1
            if self.get_calls == 1:
                raise RuntimeError("HTTP 429 rate limit")
            return type("Page", (), {"data": []})()

        def create(self, **kwargs):
            return type("Created", (), {"id": "live-score-config-created"})()

    api = FakeScoreConfigsApi()
    client = DefaultLangfuseGateway(client=_fake_score_config_client(api))
    client.retry_sleep = lambda _delay: None
    config = load_project_config("configs/projects/rewrite_quality.yaml")

    results = client.sync_score_configs(config)

    assert results[0].status == "created"
    assert api.get_calls == 2


def test_live_score_config_create_retries_rate_limits() -> None:
    class FakeScoreConfigsApi:
        def __init__(self) -> None:
            self.create_calls = 0

        def get(self, *, limit):
            return type("Page", (), {"data": []})()

        def create(self, **kwargs):
            self.create_calls += 1
            if self.create_calls == 1:
                raise RuntimeError("HTTP 429 rate limit")
            return type("Created", (), {"id": "live-score-config-created"})()

    api = FakeScoreConfigsApi()
    client = DefaultLangfuseGateway(client=_fake_score_config_client(api))
    client.retry_sleep = lambda _delay: None
    config = load_project_config("configs/projects/rewrite_quality.yaml")

    results = client.sync_score_configs(config)

    assert results[0].status == "created"
    assert api.create_calls == 2


def test_score_config_sync_validates_user_owned_reference() -> None:
    config = load_project_config("configs/projects/rewrite_quality.yaml")
    config.evaluators[0].score.managed_by_harness = False
    config.evaluators[0].score.langfuse_score_config_id = "score-config-123"
    client = DefaultLangfuseGateway()

    results = client.sync_score_configs(config)

    assert results[0].status == "user_owned"


def test_score_config_sync_fails_incompatible_schema() -> None:
    config = load_project_config("configs/projects/rewrite_quality.yaml")
    client = DefaultLangfuseGateway()
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
    client = DefaultLangfuseGateway()
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
