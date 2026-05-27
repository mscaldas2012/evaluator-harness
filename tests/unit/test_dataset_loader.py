from __future__ import annotations

import json
from pathlib import Path

import pytest

from evaluator_harness.dataset_loader import load_dataset
from evaluator_harness.errors import ConfigError


def test_loads_csv_with_optional_ground_truth() -> None:
    items = load_dataset(Path("datasets/rewrite_quality.csv"))

    assert [item.item_id for item in items] == ["1", "2"]
    assert items[0].input == "Rewrite this paragraph in a professional tone."
    assert items[0].ground_truth == "A professional rewrite that preserves the original meaning."


def test_loads_minimal_json_dataset(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset.json"
    dataset.write_text(
        json.dumps([{"id": "a", "input": "Rewrite this.", "ground_truth": "Clear rewrite."}]),
        encoding="utf-8",
    )

    items = load_dataset(dataset)

    assert items[0].item_id == "a"
    assert items[0].ground_truth == "Clear rewrite."


def test_generates_stable_item_id_when_missing(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset.csv"
    dataset.write_text("input\nRewrite this.\n", encoding="utf-8")

    first = load_dataset(dataset)[0]
    second = load_dataset(dataset)[0]

    assert first.item_id == second.item_id
    assert first.item_id.startswith("row-1-")


def test_rejects_blank_input(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset.csv"
    dataset.write_text("id,input\n1,\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="blank input"):
        load_dataset(dataset)


def test_rejects_duplicate_explicit_ids(tmp_path: Path) -> None:
    dataset = tmp_path / "dataset.csv"
    dataset.write_text("id,input\n1,First\n1,Second\n", encoding="utf-8")

    with pytest.raises(ConfigError, match="Duplicate dataset item id"):
        load_dataset(dataset)
