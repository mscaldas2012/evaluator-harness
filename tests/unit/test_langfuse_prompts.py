from __future__ import annotations

from types import SimpleNamespace

from evaluator_harness.langfuse_prompts import (
    _prompt_versions_from_page,
    _resolved_prompt_versions,
    prompt_has_label,
)


def test_prompt_has_label_checks_labels_and_artifact_version() -> None:
    assert prompt_has_label({"labels": ["production"]}, "production")
    assert prompt_has_label(
        {"labels": [], "config": {"artifact_version": "candidate-v1"}},
        "candidate-v1",
    )
    assert not prompt_has_label({"labels": [], "config": {}}, "missing")


def test_resolved_prompt_versions_ignores_versions_that_cannot_be_loaded() -> None:
    def get_prompt(name: str, *, version: int, resolve: bool) -> object:
        if version == 2:
            raise RuntimeError("missing")
        return SimpleNamespace(name=name, version=version, labels=["v1"])

    versions = _resolved_prompt_versions(get_prompt, "judge", [1, 2])

    assert versions[0]["name"] == "judge"
    assert versions[0]["version"] == 1
    assert versions[0]["labels"] == ["v1"]
    assert len(versions) == 1


def test_prompt_versions_from_page_expands_version_numbers() -> None:
    page = SimpleNamespace(
        data=[
            SimpleNamespace(name="judge", versions=[1, {"version": 2}]),
        ],
    )

    versions = _prompt_versions_from_page(
        page,
        "judge",
        lambda name, *, version, resolve: SimpleNamespace(
            name=name,
            version=version,
            labels=[f"v{version}"],
        ),
    )

    assert [version["version"] for version in versions] == [1, 2]
