from __future__ import annotations

import re
import uuid
from pathlib import Path

import pytest


@pytest.fixture
def tmp_path(request: pytest.FixtureRequest) -> Path:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", request.node.nodeid).strip("-")
    path = Path(".evaluator-harness") / "test-artifacts" / "tmp-paths" / f"{slug}-{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=True)
    return path
