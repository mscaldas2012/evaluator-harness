from __future__ import annotations

from evaluator_harness.langfuse_default_gateway import DefaultLangfuseGateway


def fake_evaluator_client_with_managed_clarity() -> DefaultLangfuseGateway:
    client = DefaultLangfuseGateway()
    client.evaluators["eval-1"] = {
        "id": "eval-1",
        "display_name": "EH_rewrite-quality_v1_judge_clarity_v1_custom_observation",
        "source_type": "custom",
        "target": "observation",
        "filters": {
            "project": "rewrite-quality",
            "project_version": "v1",
            "evaluator_set_id": "clarity:v1",
            "observation_role": "model_output",
        },
        "variables": {
            "input": "observation.input",
            "output": "observation.output",
            "baseline_output": "trace.metadata.baseline_output",
        },
        "score_config_id": "score-config-1",
        "sampling_percent": 100,
        "active": True,
    }
    return client
