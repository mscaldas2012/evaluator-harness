from __future__ import annotations

from pathlib import Path

import pytest

from evaluator_harness.errors import ConfigError
from evaluator_harness.prompt_sync import (
    PromptBindingRecord,
    PromptBindingStore,
    load_prompt_bindings,
    save_prompt_bindings,
)


def _record() -> PromptBindingRecord:
    return PromptBindingRecord(
        project="prompt-sync",
        project_version="v1",
        artifact_type="task",
        artifact_name="task_prompt",
        artifact_version="v1",
        managed_name="EH_prompt_sync_v1_prompt_task_task_prompt_v1",
        langfuse_prompt_version=1,
        langfuse_labels=["prompt-sync", "v1", "task", "prompt-v1"],
        content_identity="sha256:abc",
        prompt_shape="chat",
        roles=["system", "user"],
        active=True,
        last_synced_at="2026-06-01T00:00:00+00:00",
    )


def test_prompt_bindings_round_trip(tmp_path: Path) -> None:
    path = tmp_path / "bindings.yaml"
    store = PromptBindingStore(bindings=[_record()])

    save_prompt_bindings(path, store)
    loaded = load_prompt_bindings(path)

    assert loaded.bindings[0].managed_name == "EH_prompt_sync_v1_prompt_task_task_prompt_v1"
    assert loaded.bindings[0].roles == ["system", "user"]


def test_missing_prompt_binding_file_returns_empty_store(tmp_path: Path) -> None:
    assert load_prompt_bindings(tmp_path / "missing.yaml").bindings == []


def test_prompt_binding_rejects_secret_fields(tmp_path: Path) -> None:
    path = tmp_path / "bindings.yaml"
    path.write_text(
        "bindings:\n- project: p\n  project_version: v1\n  api_key: secret\n",
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="secret field"):
        load_prompt_bindings(path)
