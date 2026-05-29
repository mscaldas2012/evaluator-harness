from __future__ import annotations

from types import SimpleNamespace

import pytest

from evaluator_harness.config import DatasetKind, DatasetSource
from evaluator_harness.config import DatasetItem
from evaluator_harness.errors import LangfuseError
from evaluator_harness.langfuse_client import DatasetSyncResult, LangfuseClient


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


def test_records_live_dataset_run_item_with_stable_dataset_item_id() -> None:
    sdk = FakeLangfuseSdk()
    client = LangfuseClient(client=sdk)
    dataset_sync = client.sync_dataset(
        DatasetSource(kind=DatasetKind.LOCAL_CSV, langfuse_dataset_name="rewrite/v1"),
        [DatasetItem(item_id="1", input="Rewrite")],
    )

    client.record_dataset_run_item(
        dataset_sync=dataset_sync,
        item_id="1",
        run_name="baseline-123",
        trace_id="trace-123",
        observation_id="obs-123",
        metadata={"baseline_run_id": "baseline-123", "run_type": "baseline"},
    )

    assert sdk.created_items[0]["id"] == "rewrite/v1:1"
    assert sdk.created_run_items[0]["dataset_item_id"] == "rewrite/v1:1"
    assert sdk.created_run_items[0]["run_name"] == "baseline-123"
    assert sdk.created_run_items[0]["trace_id"] == "trace-123"
    assert sdk.created_run_items[0]["observation_id"] == "obs-123"


def test_records_live_dataset_run_item_with_existing_langfuse_item_id_fallback() -> None:
    sdk = FakeLangfuseSdk(
        existing_dataset_items=[
            SimpleNamespace(
                id="langfuse-generated-item-1",
                metadata={"item_id": "1"},
            )
        ],
        fail_run_item_ids={"rewrite/v1:1"},
    )
    client = LangfuseClient(client=sdk)
    dataset_sync = DatasetSyncResult(
        name="rewrite/v1",
        version="latest",
        compatibility_version="compat",
        item_count=1,
        status="synced",
    )

    client.record_dataset_run_item(
        dataset_sync=dataset_sync,
        item_id="1",
        run_name="baseline-123",
        trace_id="trace-123",
        observation_id="obs-123",
        metadata={"baseline_run_id": "baseline-123", "run_type": "baseline"},
    )

    assert [item["dataset_item_id"] for item in sdk.created_run_items] == [
        "langfuse-generated-item-1",
    ]


def test_live_baseline_lookup_uses_dataset_run_item_metadata_when_run_metadata_missing() -> None:
    fingerprint = SimpleNamespace(
        project_name="rewrite-quality",
        project_version="v1",
        dataset_name="rewrite-quality/v1",
        dataset_version="latest",
        prompt_version="v1",
        evaluator_set_id="clarity:v1",
        baseline_model="gpt5.2-dgw-default",
        baseline_parameters_hash="hash-1",
    )
    metadata = {
        **fingerprint.__dict__,
        "baseline_run_id": "baseline-123",
        "created_at": "2026-05-28T00:00:00+00:00",
        "run_type": "baseline",
    }
    sdk = FakeLangfuseSdk(
        dataset_runs=[SimpleNamespace(name="baseline-123", metadata={})],
        dataset_run_items=[
            SimpleNamespace(metadata=metadata),
        ],
    )
    client = LangfuseClient(client=sdk)

    reference = client.lookup_baseline(
        selector="latest-compatible",
        fingerprint=fingerprint,
    )

    assert reference is not None
    assert reference.baseline_run_id == "baseline-123"


def test_live_baseline_lookup_uses_item_metadata_when_run_metadata_is_incomplete() -> None:
    fingerprint = SimpleNamespace(
        project_name="rewrite-quality",
        project_version="v1",
        dataset_name="rewrite-quality/v1",
        dataset_version="latest",
        prompt_version="v1",
        evaluator_set_id="clarity:v1",
        baseline_model="gpt5.2-dgw-default",
        baseline_parameters_hash="hash-1",
    )
    item_metadata = {
        **fingerprint.__dict__,
        "baseline_run_id": "baseline-123",
        "created_at": "2026-05-28T00:00:00+00:00",
        "run_type": "baseline",
    }
    sdk = FakeLangfuseSdk(
        dataset_runs=[
            SimpleNamespace(
                name="baseline-123",
                metadata={"project": "rewrite-quality", "run_type": "baseline"},
            )
        ],
        dataset_run_items=[SimpleNamespace(metadata=item_metadata)],
    )
    client = LangfuseClient(client=sdk)

    reference = client.lookup_baseline(
        selector="baseline-123",
        fingerprint=fingerprint,
    )

    assert reference is not None
    assert reference.baseline_run_id == "baseline-123"


def test_live_baseline_lookup_matches_dataset_compatibility_version_metadata() -> None:
    fingerprint = SimpleNamespace(
        project_name="rewrite-quality",
        project_version="v1",
        dataset_name="rewrite-quality/v1",
        dataset_version="sha256:compat",
        prompt_version="v1",
        evaluator_set_id="clarity:v1",
        baseline_model="gpt5.2-dgw-default",
        baseline_parameters_hash="hash-1",
    )
    metadata = {
        **fingerprint.__dict__,
        "dataset_version": "latest",
        "dataset_compatibility_version": "sha256:compat",
        "baseline_run_id": "baseline-123",
        "created_at": "2026-05-28T00:00:00+00:00",
        "run_type": "baseline",
    }
    sdk = FakeLangfuseSdk(
        dataset_runs=[
            SimpleNamespace(name="baseline-123", metadata=metadata),
        ],
    )
    client = LangfuseClient(client=sdk)

    reference = client.lookup_baseline(
        selector="baseline-123",
        fingerprint=fingerprint,
    )

    assert reference is not None
    assert reference.baseline_run_id == "baseline-123"
    assert reference.dataset_version == "sha256:compat"


def test_live_traces_for_run_falls_back_to_dataset_run_metadata() -> None:
    metadata = {
        "run_id": "candidate-123",
        "run_type": "candidate",
        "trace_id": "trace-123",
        "dataset_item_id": "1",
        "dataset_name": "rewrite-quality/v1",
        "model_name": "azure-mistral-large-3",
        "baseline_reference": {"baseline_run_id": "baseline-123"},
    }
    sdk = FakeLangfuseSdk(
        dataset_runs=[
            SimpleNamespace(name="candidate-123", metadata=metadata),
        ],
    )
    client = LangfuseClient(client=sdk)

    traces = client.traces_for_run("candidate-123")

    assert len(traces) == 1
    assert traces[0]["trace_id"] == "trace-123"
    assert traces[0]["run_id"] == "candidate-123"
    assert traces[0]["metadata"]["model_name"] == "azure-mistral-large-3"


def test_live_traces_for_run_uses_project_dataset_name_for_fallback() -> None:
    metadata = {
        "run_id": "candidate-dfe",
        "run_type": "candidate",
        "trace_id": "trace-dfe",
        "dataset_item_id": "1",
        "dataset_name": "dfe/v1",
        "model_name": "azure-mistral-large-3",
    }
    sdk = FakeLangfuseSdk(
        dataset_runs_by_name={
            "rewrite-quality/v1": [],
            "dfe/v1": [SimpleNamespace(name="candidate-dfe", metadata=metadata)],
        },
    )
    client = LangfuseClient(client=sdk)

    traces = client.traces_for_run("candidate-dfe", dataset_names=["dfe/v1"])

    assert len(traces) == 1
    assert traces[0]["trace_id"] == "trace-dfe"
    assert sdk.requested_dataset_names == ["dfe/v1"]


def test_live_traces_for_run_fallback_reads_dataset_run_item_metadata() -> None:
    metadata = {
        "run_id": "candidate-dfe",
        "run_type": "candidate",
        "trace_id": "trace-dfe-item",
        "dataset_item_id": "1",
        "dataset_name": "dfe/v1",
        "model_name": "azure-mistral-large-3",
    }
    sdk = FakeLangfuseSdk(
        dataset_runs_by_name={
            "dfe/v1": [SimpleNamespace(name="candidate-dfe", metadata={})],
        },
        dataset_run_items_by_name={
            ("dfe/v1", "candidate-dfe"): [SimpleNamespace(metadata=metadata)],
        },
    )
    client = LangfuseClient(client=sdk)

    traces = client.traces_for_run("candidate-dfe", dataset_names=["dfe/v1"])

    assert len(traces) == 1
    assert traces[0]["trace_id"] == "trace-dfe-item"
    assert traces[0]["metadata"]["dataset_item_id"] == "1"


def test_live_traces_for_run_prefers_all_dataset_run_items_over_run_metadata() -> None:
    run_metadata = {
        "run_id": "baseline-dfe",
        "run_type": "baseline",
        "trace_id": "trace-row-1",
        "dataset_item_id": "row-1",
        "dataset_name": "dfe/v1",
    }
    item_metadata = [
        {
            **run_metadata,
            "trace_id": f"trace-row-{index}",
            "dataset_item_id": f"row-{index}",
        }
        for index in range(1, 13)
    ]
    sdk = FakeLangfuseSdk(
        dataset_runs_by_name={
            "dfe/v1": [SimpleNamespace(name="baseline-dfe", metadata=run_metadata)],
        },
        dataset_run_items_by_name={
            ("dfe/v1", "baseline-dfe"): [
                SimpleNamespace(metadata=metadata) for metadata in item_metadata
            ],
        },
    )
    client = LangfuseClient(client=sdk)

    traces = client.traces_for_run("baseline-dfe", dataset_names=["dfe/v1"])

    assert len(traces) == 12
    assert {trace["metadata"]["dataset_item_id"] for trace in traces} == {
        f"row-{index}" for index in range(1, 13)
    }


def test_live_traces_for_run_merges_partial_trace_api_with_dataset_run_items() -> None:
    run_metadata = {
        "run_id": "baseline-dfe",
        "run_type": "baseline",
        "dataset_name": "dfe/v1",
    }
    item_metadata = [
        {
            **run_metadata,
            "trace_id": f"trace-row-{index}",
            "dataset_item_id": f"row-{index}",
        }
        for index in range(1, 13)
    ]
    sdk = FakeLangfuseSdk(
        live_traces=[
            SimpleNamespace(
                id="trace-row-1",
                metadata=item_metadata[0],
                name="dfe/baseline",
                input="source 1",
                output="output 1",
                timestamp="2026-05-29T00:00:00+00:00",
            )
        ],
        dataset_runs_by_name={
            "dfe/v1": [SimpleNamespace(name="baseline-dfe", metadata=run_metadata)],
        },
        dataset_run_items_by_name={
            ("dfe/v1", "baseline-dfe"): [
                SimpleNamespace(metadata=metadata) for metadata in item_metadata
            ],
        },
    )
    client = LangfuseClient(client=sdk)

    traces = client.traces_for_run("baseline-dfe", dataset_names=["dfe/v1"])

    assert len(traces) == 12
    assert traces[0]["trace_id"] == "trace-row-1"
    assert traces[0]["input"] == "source 1"
    assert {trace["metadata"]["dataset_item_id"] for trace in traces} == {
        f"row-{index}" for index in range(1, 13)
    }


class FakeDatasetRunItemsClient:
    def __init__(self, sdk: FakeLangfuseSdk) -> None:
        self.sdk = sdk

    def create(self, **kwargs):
        if kwargs["dataset_item_id"] in self.sdk.fail_run_item_ids:
            raise RuntimeError("dataset item not found")
        self.sdk.created_run_items.append(kwargs)


class FakeApi:
    def __init__(self, sdk: FakeLangfuseSdk) -> None:
        self.dataset_items = FakeDatasetItemsClient(sdk)
        self.dataset_run_items = FakeDatasetRunItemsClient(sdk)
        self.trace = FakeTraceClient(sdk)


class FakeLangfuseSdk:
    def __init__(
        self,
        *,
        dataset_runs: list[object] | None = None,
        dataset_runs_by_name: dict[str, list[object]] | None = None,
        dataset_run_items: list[object] | None = None,
        dataset_run_items_by_name: dict[tuple[str, str], list[object]] | None = None,
        live_traces: list[object] | None = None,
        existing_dataset_items: list[object] | None = None,
        fail_run_item_ids: set[str] | None = None,
    ) -> None:
        self.created_items: list[dict[str, object]] = []
        self.created_run_items: list[dict[str, object]] = []
        self.dataset_runs = dataset_runs or []
        self.dataset_runs_by_name = dataset_runs_by_name or {}
        self.requested_dataset_names: list[str] = []
        self.dataset_run_items = dataset_run_items or []
        self.dataset_run_items_by_name = dataset_run_items_by_name or {}
        self.live_traces = live_traces or []
        self.existing_dataset_items = existing_dataset_items or []
        self.fail_run_item_ids = fail_run_item_ids or set()
        self.api = FakeApi(self)

    def auth_check(self) -> bool:
        return True

    def create_dataset(self, **_kwargs):
        return None

    def create_dataset_item(self, **kwargs):
        self.created_items.append(kwargs)

    def get_dataset_runs(self, **kwargs):
        dataset_name = str(kwargs.get("dataset_name") or "")
        self.requested_dataset_names.append(dataset_name)
        return SimpleNamespace(data=self.dataset_runs_by_name.get(dataset_name, self.dataset_runs))

    def get_dataset_run(self, **kwargs):
        key = (str(kwargs.get("dataset_name") or ""), str(kwargs.get("run_name") or ""))
        return SimpleNamespace(items=self.dataset_run_items_by_name.get(key, self.dataset_run_items))


class FakeDatasetItemsClient:
    def __init__(self, sdk: FakeLangfuseSdk) -> None:
        self.sdk = sdk

    def list(self, **_kwargs):
        return SimpleNamespace(data=self.sdk.existing_dataset_items)


class FakeTraceClient:
    def __init__(self, sdk: FakeLangfuseSdk) -> None:
        self.sdk = sdk

    def list(self, **_kwargs):
        return SimpleNamespace(data=self.sdk.live_traces)
