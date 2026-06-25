from __future__ import annotations

import os
from pathlib import Path

from evaluator_harness.config import environment_scope, resolve_environment
from evaluator_harness.environment import ResolvedEnvironment


def _write_env_file(path: str, lines: list[str]) -> None:
    with open(path, "w", encoding="utf-8") as file_handle:
        file_handle.write("\n".join(lines))
        file_handle.write("\n")


def test_resolve_environment_does_not_mutate_os_environ(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("SHARED_VAR", "shell")
    monkeypatch.delenv("ROOT_ONLY", raising=False)
    monkeypatch.delenv("PROJECT_ONLY", raising=False)

    original_environ = os.environ.copy()

    root_file = tmp_path / ".env"
    project_file = tmp_path / ".env.project"
    _write_env_file(str(root_file), ["ROOT_ONLY=root", "SHARED_VAR=root"])
    _write_env_file(str(project_file), ["PROJECT_ONLY=project", "SHARED_VAR=project"])

    resolved = resolve_environment(env_file=root_file, project_env_file=project_file)

    assert dict(os.environ) == original_environ
    assert resolved["SHARED_VAR"] == "shell"
    assert resolved["ROOT_ONLY"] == "root"
    assert resolved["PROJECT_ONLY"] == "project"


def test_resolved_environment_is_immutable():
    env = ResolvedEnvironment({"API_KEY": "value", "HOST": "localhost"})

    assert env.get("API_KEY") == "value"
    assert env["HOST"] == "localhost"

    for statement in (
        "env['API_KEY'] = 'new'",
        "del env['API_KEY']",
    ):
        try:
            exec(statement, {"env": env})
        except TypeError:
            pass
        else:
            raise AssertionError("ResolvedEnvironment should be immutable")


def test_independent_resolved_environments(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("SHARED_VAR", "shell")

    root_one = tmp_path / "one.env"
    root_two = tmp_path / "two.env"
    _write_env_file(str(root_one), ["ROOT_ONLY=one"])
    _write_env_file(str(root_two), ["ROOT_ONLY=two"])

    env_one = resolve_environment(env_file=root_one)
    env_two = resolve_environment(env_file=root_two)

    assert env_one["ROOT_ONLY"] == "one"
    assert env_two["ROOT_ONLY"] == "two"
    assert env_one["SHARED_VAR"] == "shell"
    assert env_two["SHARED_VAR"] == "shell"


def test_environment_scope_restores_original_state(
    monkeypatch,
    tmp_path: Path,
) -> None:
    original_environ = os.environ.copy()

    env_file = tmp_path / ".env"
    _write_env_file(str(env_file), ["TEMP_KEY=temp"])

    with environment_scope(env_file=env_file, apply_to_os_environ=True) as scoped_env:
        assert isinstance(scoped_env, ResolvedEnvironment)
        assert os.getenv("TEMP_KEY") == "temp"

    assert dict(os.environ) == original_environ


def test_repeated_environment_resolution_leaves_os_environ_unchanged(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setenv("SHARED_VAR", "shell")
    original_environ = os.environ.copy()

    root_file = tmp_path / ".env"
    project_file = tmp_path / ".env.project"
    _write_env_file(str(root_file), ["ROOT_ONLY=root", "SHARED_VAR=root"])
    _write_env_file(str(project_file), ["PROJECT_ONLY=project", "SHARED_VAR=project"])

    for _ in range(10):
        resolved = resolve_environment(env_file=root_file, project_env_file=project_file)
        assert resolved["SHARED_VAR"] == "shell"
        assert resolved["ROOT_ONLY"] == "root"
        assert resolved["PROJECT_ONLY"] == "project"

    assert dict(os.environ) == original_environ
