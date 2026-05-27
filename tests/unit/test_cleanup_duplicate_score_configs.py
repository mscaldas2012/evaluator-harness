from __future__ import annotations

from scripts.cleanup_duplicate_score_configs import build_cleanup_plan, build_rename_archived_plan


def test_cleanup_plan_keeps_newest_active_score_config_and_archives_duplicates() -> None:
    plans = build_cleanup_plan(
        [
            {
                "id": "old",
                "name": "eh_rewrite_quality_clarity",
                "archived": False,
                "created_at": "2026-05-26T21:31:10Z",
            },
            {
                "id": "new",
                "name": "eh_rewrite_quality_clarity",
                "archived": False,
                "created_at": "2026-05-26T21:31:13Z",
            },
            {
                "id": "archived",
                "name": "eh_rewrite_quality_clarity",
                "archived": True,
                "created_at": "2026-05-26T21:31:14Z",
            },
            {
                "id": "other",
                "name": "manual_score",
                "archived": False,
                "created_at": "2026-05-26T21:31:15Z",
            },
        ],
        prefix="eh_rewrite_quality_",
    )

    assert len(plans) == 1
    assert plans[0].name == "eh_rewrite_quality_clarity"
    assert plans[0].keep_id == "new"
    assert plans[0].archive_ids == ["old"]


def test_rename_archived_plan_renames_only_archived_prefixed_configs() -> None:
    plans = build_rename_archived_plan(
        [
            {
                "id": "archived123",
                "name": "eh_rewrite_quality_clarity",
                "archived": True,
            },
            {
                "id": "active123",
                "name": "eh_rewrite_quality_clarity",
                "archived": False,
            },
            {
                "id": "already123",
                "name": "eh_rewrite_quality_clarity_archived_already",
                "archived": True,
            },
            {
                "id": "manual123",
                "name": "manual_score",
                "archived": True,
            },
        ],
        prefix="eh_rewrite_quality_",
    )

    assert len(plans) == 1
    assert plans[0].config_id == "archived123"
    assert plans[0].new_name == "eh_rewrite_quality_cl_arch_archived"
    assert len(plans[0].new_name) <= 35
