from __future__ import annotations

import string

from evaluator_harness.session_identity import (
    SessionIdentityInputs,
    item_comparison_session_id,
)


def _inputs(**overrides: str) -> SessionIdentityInputs:
    values = {
        "project": "rewrite-quality",
        "project_version": "v1",
        "dataset_name": "rewrite-quality/v1",
        "dataset_version": "sha256:dataset",
        "baseline_anchor": "baseline-123",
        "dataset_item_id": "item-1",
        "source_row": 1,
    }
    values.update(overrides)
    return SessionIdentityInputs(**values)


def test_item_comparison_session_id_is_deterministic() -> None:
    inputs = _inputs()

    assert item_comparison_session_id(inputs) == item_comparison_session_id(inputs)


def test_item_comparison_session_id_uses_readable_baseline_linking_format() -> None:
    session_id = item_comparison_session_id(
        _inputs(
            project="GSO",
            project_version="v1",
            baseline_anchor="baseline-6f75db0f7489",
            dataset_item_id="MUC 2026/04/27",
            source_row=42,
        )
    )

    assert session_id == "gso-v1-baseline-6f75db0f7489-row-42"


def test_item_comparison_session_id_is_ascii_and_under_langfuse_limit() -> None:
    session_id = item_comparison_session_id(
        _inputs(
            project="unicode project \u2603",
            dataset_name="dataset/" + ("x" * 500),
            dataset_item_id="item with spaces and punctuation !@#$%^&*()",
        )
    )

    assert len(session_id) < 200
    assert all(character in string.printable for character in session_id)
    session_id.encode("ascii")


def test_item_comparison_session_id_changes_when_identity_inputs_change() -> None:
    base = item_comparison_session_id(_inputs())

    assert item_comparison_session_id(_inputs(project="other")) != base
    assert item_comparison_session_id(_inputs(baseline_anchor="baseline-456")) != base
    assert item_comparison_session_id(_inputs(dataset_item_id="item-2")) == base
    assert item_comparison_session_id(_inputs(source_row=2)) != base
