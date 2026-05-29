from __future__ import annotations

from pathlib import Path

import pytest

from evaluator_harness.errors import ConfigError
from evaluator_harness.prompts import (
    parse_prompt_file,
    prompt_identity,
    render_prompt,
    validate_dataset_variables,
)


def test_parses_legacy_single_text_prompt() -> None:
    prompt = parse_prompt_file(Path("prompts/rewrite_quality/task_prompt.md"))

    assert prompt.shape == "text"
    assert prompt.text
    assert prompt.messages == []


def test_parses_role_based_prompt_sections_in_order() -> None:
    prompt = parse_prompt_file(Path("tests/fixtures/prompts/role_based_task_prompt.md"))

    assert prompt.shape == "messages"
    assert [message.role for message in prompt.messages] == [
        "system",
        "user",
        "reviewer-note",
    ]
    assert "{dataset.input}" in prompt.messages[1].content


@pytest.mark.parametrize(
    ("path", "message"),
    [
        ("tests/fixtures/prompts/invalid_role_unassigned_content.md", "unassigned"),
        ("tests/fixtures/prompts/invalid_role_empty_heading.md", "role heading"),
    ],
)
def test_rejects_malformed_role_prompt_files(path: str, message: str) -> None:
    with pytest.raises(ConfigError, match=message):
        parse_prompt_file(Path(path))


def test_extracts_dataset_placeholders_and_rejects_unmatched_braces() -> None:
    prompt = parse_prompt_file(Path("tests/fixtures/prompts/role_based_task_prompt.md"))

    assert [ref.raw for ref in prompt.variable_references] == [
        "{dataset.input}",
        "{dataset.ground_truth}",
    ]
    with pytest.raises(ConfigError, match="Malformed placeholder"):
        parse_prompt_file(Path("tests/fixtures/prompts/invalid_placeholder_unmatched_brace.md"))


def test_validates_dataset_placeholders_against_columns() -> None:
    prompt = parse_prompt_file(Path("tests/fixtures/prompts/role_based_task_prompt.md"))

    validate_dataset_variables(prompt, {"input", "ground_truth"})

    with pytest.raises(ConfigError, match="dataset.ground_truth"):
        validate_dataset_variables(prompt, {"input"})


def test_renders_dataset_values_in_role_messages() -> None:
    prompt = parse_prompt_file(Path("tests/fixtures/prompts/role_based_task_prompt.md"))

    rendered = render_prompt(
        prompt,
        {
            "input": "Rewrite this text",
            "ground_truth": "Expected rewrite",
        },
    )

    assert rendered.shape == "messages"
    assert rendered.messages[1].content.count("Rewrite this text") == 1
    assert "Expected rewrite" in rendered.messages[1].content


def test_renders_empty_row_values_as_empty_strings() -> None:
    prompt = parse_prompt_file(Path("tests/fixtures/prompts/role_based_task_prompt_empty.md"))

    rendered = render_prompt(prompt, {"input": "Input", "optional_note": None})

    assert "Optional context: " in rendered.display_text
    assert "None" not in rendered.display_text


def test_treats_braces_inside_dataset_values_as_literal_data() -> None:
    prompt = parse_prompt_file(Path("tests/fixtures/prompts/role_based_task_prompt.md"))

    rendered = render_prompt(
        prompt,
        {"input": "Value with {literal} braces", "ground_truth": ""},
    )

    assert "Value with {literal} braces" in rendered.display_text


def test_prompt_identity_includes_shape_roles_and_variables() -> None:
    identity = prompt_identity(Path("tests/fixtures/prompts/role_based_task_prompt.md"), "v1")

    assert identity["shape"] == "messages"
    assert identity["roles"] == ["system", "user", "reviewer-note"]
    assert identity["variable_references"] == ["dataset.input", "dataset.ground_truth"]
    assert identity["content_hash"]
