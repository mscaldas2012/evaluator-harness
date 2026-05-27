from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

from evaluator_harness.config import DatasetItem
from evaluator_harness.errors import ConfigError


def load_dataset(path: Path) -> list[DatasetItem]:
    if not path.exists():
        raise ConfigError(f"Dataset not found: {path}")
    suffix = path.suffix.lower()
    if suffix == ".csv":
        rows = _load_csv(path)
    elif suffix == ".json":
        rows = _load_json(path)
    else:
        raise ConfigError(f"Unsupported dataset format: {path.suffix}")
    return _rows_to_items(rows)


def dataset_compatibility_version(items: list[DatasetItem]) -> str:
    payload = [
        {
            "item_id": item.item_id,
            "input_hash": item.input_hash
            or hashlib.sha256(item.input.encode("utf-8")).hexdigest(),
        }
        for item in sorted(items, key=lambda candidate: candidate.item_id)
    ]
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return f"sha256:{digest}"


def _load_csv(path: Path) -> list[dict[str, Any]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def _load_json(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list) or not all(isinstance(item, dict) for item in data):
        raise ConfigError("JSON datasets must be a list of objects")
    return data


def _rows_to_items(rows: list[dict[str, Any]]) -> list[DatasetItem]:
    items: list[DatasetItem] = []
    explicit_ids: set[str] = set()
    for index, row in enumerate(rows, start=1):
        input_value = str(row.get("input") or "").strip()
        if not input_value:
            raise ConfigError(f"Dataset row {index} has blank input")

        raw_id = str(row.get("id") or "").strip()
        if raw_id:
            item_id = raw_id
            if item_id in explicit_ids:
                raise ConfigError(f"Duplicate dataset item id: {item_id}")
            explicit_ids.add(item_id)
        else:
            digest = hashlib.sha256(input_value.encode("utf-8")).hexdigest()[:12]
            item_id = f"row-{index}-{digest}"

        metadata = {
            key: value
            for key, value in row.items()
            if key not in {"id", "input", "ground_truth", "reference_output"}
            and value not in (None, "")
        }
        items.append(
            DatasetItem(
                item_id=item_id,
                input=input_value,
                metadata=metadata,
                reference_output=_optional_str(row.get("reference_output")),
                ground_truth=_optional_str(row.get("ground_truth")),
                source_row=index,
                input_hash=hashlib.sha256(input_value.encode("utf-8")).hexdigest(),
            )
        )
    return items


def _optional_str(value: Any) -> str | None:
    if value in (None, ""):
        return None
    return str(value)
