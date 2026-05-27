from __future__ import annotations

from evaluator_harness.config import DatasetItem
from evaluator_harness.dataset_loader import dataset_compatibility_version


def test_dataset_compatibility_version_is_order_independent() -> None:
    items = [
        DatasetItem(item_id="2", input="B", input_hash="hash-b"),
        DatasetItem(item_id="1", input="A", input_hash="hash-a"),
    ]

    assert dataset_compatibility_version(items) == dataset_compatibility_version(list(reversed(items)))


def test_dataset_compatibility_version_changes_when_input_hash_changes() -> None:
    original = [DatasetItem(item_id="1", input="A", input_hash="hash-a")]
    changed = [DatasetItem(item_id="1", input="A changed", input_hash="hash-b")]

    assert dataset_compatibility_version(original) != dataset_compatibility_version(changed)
