from __future__ import annotations

from pathlib import Path

import pytest
from typer.testing import CliRunner


@pytest.fixture
def cli_runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def temp_project_file(tmp_path: Path) -> Path:
    project = tmp_path / "project.yaml"
    project.write_text(
        """
project:
  name: temp-project
  version: v1
  score_config_prefix: eh_temp_
""".strip(),
        encoding="utf-8",
    )
    return project
