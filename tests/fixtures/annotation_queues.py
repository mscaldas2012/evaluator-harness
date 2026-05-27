from __future__ import annotations


MANAGED_QUEUE_REFERENCE = {
    "schema_version": "1",
    "project_name": "rewrite-quality",
    "project_version": "v1",
    "review_policy_version": "default",
    "queue_id": "queue-managed-1",
    "queue_name": "EH_rewrite-quality_v1_review_default",
    "ownership": "managed_by_harness",
    "score_config_ids": ["score-config-1"],
    "status": "created",
    "synced_at": "2026-05-26T00:00:00+00:00",
}


USER_OWNED_QUEUE_REFERENCE = {
    "schema_version": "1",
    "project_name": "rewrite-quality",
    "project_version": "v1",
    "review_policy_version": "default",
    "queue_id": "queue-user-owned-1",
    "queue_name": "shared-review-queue",
    "ownership": "user_owned",
    "score_config_ids": ["score-config-1"],
    "status": "user_owned",
    "synced_at": "2026-05-26T00:00:00+00:00",
}
