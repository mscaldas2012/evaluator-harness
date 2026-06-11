from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass


MAX_LANGFUSE_SESSION_ID_LENGTH = 199
TRUNCATION_HASH_LENGTH = 12


@dataclass(frozen=True)
class SessionIdentityInputs:
    project: str
    project_version: str
    dataset_name: str
    dataset_version: str
    baseline_anchor: str
    dataset_item_id: str
    source_row: int | None = None

    def metadata(self) -> dict[str, str]:
        return asdict(self)


def item_comparison_session_id(inputs: SessionIdentityInputs) -> str:
    session_id = "-".join(
        [
            _slug(inputs.project),
            _slug(inputs.project_version),
            _slug(inputs.baseline_anchor),
            _slug(_row_component(inputs.source_row)),
        ]
    )
    if len(session_id) > MAX_LANGFUSE_SESSION_ID_LENGTH:
        session_id = _truncate_with_hash(session_id, inputs)
    session_id.encode("ascii")
    if len(session_id) > MAX_LANGFUSE_SESSION_ID_LENGTH:
        raise ValueError("computed Langfuse session ID exceeds 200 characters")
    return session_id


def _slug(value: str) -> str:
    ascii_value = value.lower().encode("ascii", "ignore").decode("ascii")
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value)
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "unknown"


def _row_component(source_row: int | None) -> str:
    if source_row is None:
        return "row-unknown"
    return f"row-{source_row}"


def _truncate_with_hash(session_id: str, inputs: SessionIdentityInputs) -> str:
    payload = json.dumps(
        inputs.metadata(),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    )
    digest = hashlib.sha256(payload.encode("ascii")).hexdigest()[:TRUNCATION_HASH_LENGTH]
    max_prefix_length = MAX_LANGFUSE_SESSION_ID_LENGTH - len(digest) - 1
    prefix = session_id[:max_prefix_length].rstrip("-")
    return f"{prefix}-{digest}"
