from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from typing import Any

from evaluator_harness.config import LiveSettings
from evaluator_harness.langfuse_gateways import (
    LangfuseGateway,
    build_langfuse_gateway_from_env,
)

VALID_LANGFUSE_TRACE_ID = re.compile(r"^[0-9a-f]{32}$")


@dataclass(frozen=True)
class InvalidQueueItem:
    queue_id: str
    item_id: str
    object_id: str
    object_type: str


def find_invalid_trace_queue_items(
    client: LangfuseGateway,
    queue_id: str,
) -> list[InvalidQueueItem]:
    annotation_queues = _sdk_client(client).api.annotation_queues
    invalid: list[InvalidQueueItem] = []
    page = 1
    while True:
        response = annotation_queues.list_queue_items(queue_id, page=page, limit=100)
        for item in getattr(response, "data", []):
            raw = _queue_item_dict(item)
            object_type = str(raw.get("object_type") or raw.get("objectType") or "")
            object_id = str(raw.get("object_id") or raw.get("objectId") or "")
            if object_type.endswith(
                "TRACE"
            ) and not VALID_LANGFUSE_TRACE_ID.fullmatch(object_id):
                invalid.append(
                    InvalidQueueItem(
                        queue_id=queue_id,
                        item_id=str(raw["id"]),
                        object_id=object_id,
                        object_type=object_type,
                    )
                )
        meta = getattr(response, "meta", None)
        total_pages = int(getattr(meta, "total_pages", page) or page)
        if page >= total_pages:
            return invalid
        page += 1


def delete_queue_items(client: LangfuseGateway, items: list[InvalidQueueItem]) -> None:
    annotation_queues = _sdk_client(client).api.annotation_queues
    for item in items:
        annotation_queues.delete_queue_item(item.queue_id, item.item_id)


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Delete annotation queue items that point to invalid Langfuse trace IDs."
        )
    )
    parser.add_argument(
        "--queue-id",
        default=None,
        help=(
            "Annotation queue ID. Defaults to the first queue in the Langfuse project."
        ),
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help=(
            "Delete invalid queue items. Without this flag the script only prints "
            "the plan."
        ),
    )
    args = parser.parse_args()

    LiveSettings.from_env().require_langfuse()
    client = build_langfuse_gateway_from_env()
    queue_id = args.queue_id or _sdk_client(client).api.annotation_queues.list_queues(
        limit=100
    ).data[0].id

    invalid = find_invalid_trace_queue_items(client, queue_id)
    if not invalid:
        print("No invalid trace annotation queue items found.")
        return 0

    print("Invalid trace annotation queue items:")
    for item in invalid:
        print(f"- {item.item_id}: {item.object_id}")

    if not args.apply:
        print("\nDry run only. Re-run with --apply to delete invalid queue items.")
        return 0

    delete_queue_items(client, invalid)
    print(f"\nDeleted {len(invalid)} invalid annotation queue items.")
    return 0


def _queue_item_dict(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if hasattr(value, "dict"):
        return value.dict()
    return dict(value)


def _sdk_client(client: LangfuseGateway) -> Any:
    if client.client is None:
        raise RuntimeError("A live Langfuse SDK client is required.")
    return client.client


if __name__ == "__main__":
    raise SystemExit(main())
