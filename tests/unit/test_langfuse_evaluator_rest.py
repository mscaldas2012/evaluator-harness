from __future__ import annotations

import base64
import json
from typing import Any

import httpx

from evaluator_harness.config import LiveSettings
from evaluator_harness.langfuse_client import LangfuseClient


def _settings() -> LiveSettings:
    return LiveSettings(
        langfuse_public_key="pk-test",
        langfuse_secret_key="sk-test",
        langfuse_host="https://langfuse.test",
    )


def _client_without_sdk_evaluators(
    handler: httpx.MockTransport,
) -> LangfuseClient:
    return LangfuseClient(
        client=type("FakeClient", (), {"api": type("Api", (), {})()})(),
        settings=_settings(),
        http_transport=handler,
    )


def _json(request: httpx.Request) -> dict[str, Any]:
    return json.loads(request.content.decode("utf-8"))


def _assert_basic_auth(request: httpx.Request) -> None:
    expected = base64.b64encode(b"pk-test:sk-test").decode("ascii")
    assert request.headers["authorization"] == f"Basic {expected}"


def test_evaluator_list_falls_back_to_unstable_rest_api_when_sdk_resource_missing() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/api/public/unstable/evaluation-rules"
        _assert_basic_auth(request)
        return httpx.Response(
            200,
            json={
                "data": [
                    {
                        "evaluationRuleId": "rule-1",
                        "name": "EH_rewrite_quality_v1_judge_clarity_v1_custom_observation",
                        "enabled": True,
                        "sampling": 1,
                        "filter": [
                            {
                                "column": "name",
                                "operator": "any of",
                                "value": ["OpenAI-generation"],
                                "type": "stringOptions",
                            }
                        ],
                        "mapping": [
                            {"variable": "input", "source": "input"},
                            {"variable": "output", "source": "output"},
                            {
                                "variable": "ground_truth",
                                "source": "metadata",
                                "jsonPath": "$.ground_truth",
                            },
                        ],
                        "scoreConfigId": "score-1",
                        "samplingPercent": 100,
                    }
                ]
            },
        )

    client = _client_without_sdk_evaluators(httpx.MockTransport(handler))

    evaluators = client.list_evaluators()

    assert evaluators == [
        {
            "evaluationRuleId": "rule-1",
            "id": "rule-1",
            "name": "EH_rewrite_quality_v1_judge_clarity_v1_custom_observation",
            "enabled": True,
            "active": True,
            "sampling": 1,
            "filter": [
                {
                    "column": "name",
                    "operator": "any of",
                    "value": ["OpenAI-generation"],
                    "type": "stringOptions",
                }
            ],
            "filters": {"_has_top_level_name_filter": True},
            "mapping": [
                {"variable": "input", "source": "input"},
                {"variable": "output", "source": "output"},
                {
                    "variable": "ground_truth",
                    "source": "metadata",
                    "jsonPath": "$.ground_truth",
                },
            ],
            "variables": {
                "input": "observation.input",
                "output": "observation.output",
                "ground_truth": "trace.metadata.ground_truth",
            },
            "scoreConfigId": "score-1",
            "score_config_id": "score-1",
            "samplingPercent": 100,
            "sampling_percent": 100,
        }
    ]


def test_custom_evaluator_create_posts_template_then_rule_with_required_shape() -> None:
    seen: list[tuple[str, str, dict[str, Any]]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        _assert_basic_auth(request)
        body = _json(request)
        seen.append((request.method, request.url.path, body))
        if request.url.path == "/api/public/unstable/evaluators":
            assert body == {
                "name": "EH_rewrite_quality_v1_judge_clarity_v1_custom_observation",
                "prompt": "Judge {{input}} and {{output}}.",
                "outputDefinition": {
                    "dataType": "NUMERIC",
                    "reasoning": {"description": "Explain the score."},
                    "score": {"description": "Clarity score from 0.0 to 1.0."},
                },
            }
            return httpx.Response(
                200,
                json={
                    "id": "evaltmpl-1",
                    "name": body["name"],
                    "scope": "project",
                    "variables": ["input", "output"],
                },
            )
        if request.url.path == "/api/public/unstable/evaluation-rules":
            assert body == {
                "name": "EH_rewrite_quality_v1_judge_clarity_v1_custom_observation",
                "evaluator": {
                    "name": "EH_rewrite_quality_v1_judge_clarity_v1_custom_observation",
                    "scope": "project",
                },
                "target": "observation",
                "enabled": True,
                "sampling": 1.0,
                "filter": [],
                "mapping": [
                    {"variable": "input", "source": "input"},
                    {"variable": "output", "source": "output"},
                ],
            }
            return httpx.Response(
                200,
                json={
                    "id": "rule-1",
                    "name": body["name"],
                    "evaluator": {"id": "evaltmpl-1", **body["evaluator"]},
                    "target": body["target"],
                    "enabled": body["enabled"],
                    "mapping": body["mapping"],
                },
            )
        raise AssertionError(f"unexpected path: {request.url.path}")

    client = _client_without_sdk_evaluators(httpx.MockTransport(handler))

    created = client.create_evaluator(
        {
            "display_name": "EH_rewrite_quality_v1_judge_clarity_v1_custom_observation",
            "source_type": "custom",
            "target": "observation",
            "active": True,
            "prompt": "Judge {{input}} and {{output}}.",
            "output_definition": {
                "dataType": "NUMERIC",
                "reasoning": {"description": "Explain the score."},
                "score": {"description": "Clarity score from 0.0 to 1.0."},
            },
            "filters": {"observation_name": "OpenAI-generation"},
            "variables": {
                "input": "observation.input",
                "output": "observation.output",
            },
            "sampling_percent": 100,
        }
    )

    assert created["id"] == "rule-1"
    assert created["active"] is True
    assert [item[:2] for item in seen] == [
        ("POST", "/api/public/unstable/evaluators"),
        ("POST", "/api/public/unstable/evaluation-rules"),
    ]


def test_evaluator_create_does_not_emit_provider_specific_top_level_filters() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        _assert_basic_auth(request)
        body = _json(request)
        if request.url.path == "/api/public/unstable/evaluators":
            return httpx.Response(
                200,
                json={"id": "evaltmpl-1", "name": body["name"], "scope": "project"},
            )
        if request.url.path == "/api/public/unstable/evaluation-rules":
            assert all(item["column"] != "environment" for item in body["filter"])
            assert all(item["column"] != "name" for item in body["filter"])
            assert all(item["column"] != "type" for item in body["filter"])
            return httpx.Response(200, json={"id": "rule-1", **body})
        raise AssertionError(f"unexpected path: {request.url.path}")

    client = _client_without_sdk_evaluators(httpx.MockTransport(handler))

    client.create_evaluator(
        {
            "display_name": "EH_rewrite_quality_v1_judge_clarity_v1_custom_observation",
            "source_type": "custom",
            "target": "observation",
            "active": True,
            "prompt": "Judge {{input}} and {{output}}.",
            "filters": {
                "environment": "local",
                "observation_name": "OpenAI-generation",
            },
            "variables": {"input": "observation.input", "output": "observation.output"},
        }
    )


def test_evaluator_update_falls_back_to_unstable_rest_patch_not_delete() -> None:
    seen_methods: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen_methods.append(request.method)
        assert request.method == "PATCH"
        assert request.url.path == "/api/public/unstable/evaluation-rules/rule-1"
        _assert_basic_auth(request)
        body = _json(request)
        assert body["enabled"] is False
        assert "active" not in body
        assert "comment" not in body
        return httpx.Response(
            200,
            json={"id": "rule-1", "name": "old-rule", "enabled": False},
        )

    client = _client_without_sdk_evaluators(httpx.MockTransport(handler))

    updated = client.inactivate_evaluator(
        "rule-1",
        comment="superseded by clarity v2",
    )

    assert updated["active"] is False
    assert seen_methods == ["PATCH"]


def test_evaluator_filter_update_includes_target_for_langfuse_validation() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "PATCH"
        body = _json(request)
        assert body["target"] == "observation"
        assert body["filter"] == []
        return httpx.Response(200, json={"id": "rule-1", "enabled": True})

    client = _client_without_sdk_evaluators(httpx.MockTransport(handler))

    client.update_evaluator(
        "rule-1",
        {
            "filters": {
                "target": "observation",
                "observation_name": "OpenAI-generation",
                "environment": "local",
            }
        },
    )


def test_sdk_evaluator_resource_is_preferred_over_rest_fallback() -> None:
    class FakeEvaluatorsApi:
        def list(self, *, limit: int):
            assert limit == 100
            return type("Page", (), {"data": [{"id": "sdk-rule", "name": "from-sdk"}]})()

    class FakeClient:
        api = type("Api", (), {"evaluators": FakeEvaluatorsApi()})()

    def handler(request: httpx.Request) -> httpx.Response:
        raise AssertionError("REST fallback should not be used when SDK evaluator API exists")

    client = LangfuseClient(
        client=FakeClient(),
        settings=_settings(),
        http_transport=httpx.MockTransport(handler),
    )

    assert client.list_evaluators() == [{"id": "sdk-rule", "name": "from-sdk"}]
