from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace

from evaluator_harness.config import BaselineReference
from evaluator_harness.langfuse_baselines import (
    baseline_reference_sort_key,
    metadata_matches,
    parse_datetime,
    reference_matches,
)
from evaluator_harness.langfuse_default_gateway import DefaultLangfuseGateway


def _fingerprint(**overrides: str) -> SimpleNamespace:
    values = {
        "project_name": "rewrite-quality",
        "project_version": "v1",
        "dataset_name": "rewrite-quality/v1",
        "dataset_version": "v1",
        "prompt_version": "candidate-v1",
        "evaluator_set_id": "default",
        "baseline_model": "gpt-5-mini",
        "baseline_parameters_hash": "abc123",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_reference_matches_fingerprint_fields() -> None:
    fingerprint = _fingerprint()
    reference = BaselineReference(
        baseline_run_id="baseline-run",
        langfuse_run_name="baseline-run",
        created_at="2026-06-18T10:00:00Z",
        **fingerprint.__dict__,
    )

    assert reference_matches(reference, fingerprint)
    assert not reference_matches(reference, _fingerprint(dataset_version="v2"))


def test_metadata_matches_accepts_dataset_compatibility_version_alias() -> None:
    fingerprint = _fingerprint(dataset_version="compat-v1")
    metadata = {
        **fingerprint.__dict__,
        "dataset_version": "raw-v1",
        "dataset_compatibility_version": "compat-v1",
    }

    assert metadata_matches(metadata, fingerprint)


def test_baseline_sort_key_prefers_parseable_created_at_then_index() -> None:
    older = SimpleNamespace(created_at="2026-06-18T10:00:00Z")
    newer_metadata = {"created_at": "2026-06-18T11:00:00+00:00"}

    assert baseline_reference_sort_key(older, {}, 1) < baseline_reference_sort_key(
        older,
        newer_metadata,
        0,
    )
    assert baseline_reference_sort_key(SimpleNamespace(), {}, 2) == (
        datetime.min.replace(tzinfo=UTC),
        2,
    )


def test_parse_datetime_normalizes_zulu_and_naive_values() -> None:
    assert parse_datetime("2026-06-18T10:00:00Z") == datetime(
        2026,
        6,
        18,
        10,
        tzinfo=UTC,
    )
    assert parse_datetime("2026-06-18T10:00:00").tzinfo == UTC
    assert parse_datetime("not-a-date") is None


def test_live_baseline_expected_not_found_does_not_warn() -> None:
    client = SimpleNamespace(
        get_dataset_runs=lambda **_kwargs: SimpleNamespace(data=[])
    )
    gateway = DefaultLangfuseGateway(client=client)

    assert gateway.lookup_baseline(
        selector="latest-compatible",
        fingerprint=_fingerprint(),
    ) is None
    assert gateway.current_langfuse_warnings() == ()


def test_live_baseline_lookup_failure_warns() -> None:
    def get_dataset_runs(**_kwargs):
        raise RuntimeError("authorization: sk-secret123")

    gateway = DefaultLangfuseGateway(
        client=SimpleNamespace(get_dataset_runs=get_dataset_runs)
    )

    assert gateway.lookup_baseline(
        selector="latest-compatible",
        fingerprint=_fingerprint(),
    ) is None

    warnings = gateway.current_langfuse_warnings()
    assert len(warnings) == 1
    assert warnings[0].operation == "baseline_lookup"
    assert warnings[0].details["error"] == "authorization: [REDACTED]"
