from __future__ import annotations

import pytest

from evaluator_harness.config import DatasetKind, DatasetSource
from evaluator_harness.config import DatasetItem
from evaluator_harness.errors import LangfuseError
from evaluator_harness.langfuse_client import LangfuseClient


def test_sync_dataset_creates_or_updates_dataset_with_items() -> None:
    client = LangfuseClient()
    items = [DatasetItem(item_id="1", input="Rewrite", ground_truth="Expected")]

    result = client.sync_dataset(
        DatasetSource(kind=DatasetKind.LOCAL_CSV, langfuse_dataset_name="rewrite/v1"),
        items,
    )

    assert result.name == "rewrite/v1"
    assert result.item_count == 1
    assert result.version
    assert client.datasets["rewrite/v1"][0]["input"] == "Rewrite"


def test_sync_dataset_resolves_langfuse_dataset_without_local_items() -> None:
    client = LangfuseClient()

    result = client.sync_dataset(
        DatasetSource(kind=DatasetKind.LANGFUSE, langfuse_dataset_name="remote/v1"),
        [],
    )

    assert result.name == "remote/v1"
    assert result.item_count == 0


def test_langfuse_unreachable_fails_fast() -> None:
    client = LangfuseClient(reachable=False)

    with pytest.raises(LangfuseError, match="unreachable"):
        client.check_reachable(operation="sync-dataset", dataset_item_id="1")
