from __future__ import annotations

import pytest

from evaluator_harness.langfuse_client import LangfuseClient
from evaluator_harness.runner import ExperimentRunner
from tests.fixtures.live_env import require_live_langfuse


@pytest.mark.live
def test_live_sync_prompts_dry_run_smoke() -> None:
    require_live_langfuse()
    runner = ExperimentRunner(langfuse_client=LangfuseClient.from_env())

    result = runner.sync_prompts(
        "tests/fixtures/projects/valid_prompt_sync.yaml",
        dry_run=True,
    )

    assert result.total_count == 2
    assert result.mode == "dry-run"
