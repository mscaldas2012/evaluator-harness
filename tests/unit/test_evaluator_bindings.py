from __future__ import annotations

from pathlib import Path

import pytest

from evaluator_harness.evaluator_bindings import (
    EvaluatorBindingRecord,
    EvaluatorBindingStore,
    load_evaluator_bindings,
    save_evaluator_bindings,
    validate_binding_path,
)
from evaluator_harness.errors import ConfigError


def _record() -> EvaluatorBindingRecord:
    return EvaluatorBindingRecord(
        project="rewrite-quality",
        project_version="v1",
        evaluator_name="clarity",
        evaluator_version="v1",
        source_type="custom",
        target="observation",
        langfuse_evaluator_id="eval-1",
        langfuse_display_name="EH_rewrite-quality_v1_judge_clarity_v1_custom_observation",
        score_config_id="score-config-1",
        score_config_name="eh_rewrite_quality_clarity",
        judge_model="gpt-4.1",
        sampling_percent=100,
        historical_backfill=False,
        active=True,
        last_synced_at="2026-05-27T00:00:00Z",
    )


def test_binding_round_trip_and_lookup(tmp_path: Path) -> None:
    path = tmp_path / "bindings.yaml"
    save_evaluator_bindings(path, EvaluatorBindingStore(bindings=[_record()]))

    store = load_evaluator_bindings(path)

    assert store.find(
        project="rewrite-quality",
        project_version="v1",
        evaluator_name="clarity",
        evaluator_version="v1",
        source_type="custom",
        target="observation",
    ).langfuse_evaluator_id == "eval-1"


def test_binding_rejects_secret_fields(tmp_path: Path) -> None:
    path = tmp_path / "bindings.yaml"
    path.write_text(
        "bindings:\n"
        "  - project: rewrite-quality\n"
        "    project_version: v1\n"
        "    evaluator_name: clarity\n"
        "    evaluator_version: v1\n"
        "    source_type: custom\n"
        "    target: observation\n"
        "    langfuse_evaluator_id: eval-1\n"
        "    langfuse_display_name: name\n"
        "    score_config_id: score-config-1\n"
        "    score_config_name: clarity\n"
        "    api_key: sk-secret\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="secret"):
        load_evaluator_bindings(path)


def test_binding_path_must_stay_repo_local(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="repo-local"):
        validate_binding_path((Path.cwd().parent / "outside.yaml"), repo_root=Path.cwd())


def test_display_name_alone_is_not_binding_proof() -> None:
    store = EvaluatorBindingStore()

    assert store.find_by_display_name(
        "EH_rewrite-quality_v1_judge_clarity_v1_custom_observation"
    ) is None
