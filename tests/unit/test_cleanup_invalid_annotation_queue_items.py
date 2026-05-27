from __future__ import annotations

from scripts.cleanup_invalid_annotation_queue_items import VALID_LANGFUSE_TRACE_ID


def test_valid_langfuse_trace_id_pattern_rejects_old_run_item_ids() -> None:
    assert VALID_LANGFUSE_TRACE_ID.fullmatch("d69d1fc928361c9019c6367563b3b2cd")
    assert not VALID_LANGFUSE_TRACE_ID.fullmatch("baseline-e78684370352-1")
