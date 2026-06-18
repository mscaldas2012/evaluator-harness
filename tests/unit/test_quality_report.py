from __future__ import annotations

import subprocess
from pathlib import Path

import scripts.quality_report as quality_report


def test_run_quality_report_writes_tool_outputs_under_reports_quality(
    tmp_path, capsys
) -> None:
    commands: list[tuple[str, ...]] = []

    def fake_runner(
        command: list[str], stdout_path: Path
    ) -> subprocess.CompletedProcess[str]:
        commands.append(tuple(command))
        stdout_path.write_text("ok\n", encoding="utf-8")
        return subprocess.CompletedProcess(command, 0)

    exit_code = quality_report.run_quality_report(
        project_root=tmp_path,
        runner=fake_runner,
    )

    assert exit_code == 0
    assert commands == [
        ("ruff", "check", "."),
        ("ruff", "format", "--check", "."),
        ("pyright",),
        ("lint-imports", "--config", ".importlinter"),
        ("radon", "cc", "src", "scripts", "-s", "-a"),
        ("radon", "mi", "src", "scripts", "-s"),
        (
            "pytest",
            "-m",
            "not live",
            "--junitxml",
            "reports/quality/pytest.xml",
            "--cov-report",
            "xml:reports/quality/coverage.xml",
            "--cov-report",
            "html:reports/quality/htmlcov",
        ),
        ("coverage", "report", "--format=markdown"),
        ("vulture", "src", "tests", "scripts", "--min-confidence", "80"),
    ]
    assert (tmp_path / "reports" / "quality" / "ruff-check.txt").read_text(
        encoding="utf-8"
    ) == "ok\n"
    assert (tmp_path / "reports" / "quality" / "pyright.txt").read_text(
        encoding="utf-8"
    ) == "ok\n"
    assert "quality report passed" in capsys.readouterr().out


def test_run_quality_report_returns_failure_when_any_tool_fails(
    tmp_path, capsys
) -> None:
    def fake_runner(
        command: list[str], stdout_path: Path
    ) -> subprocess.CompletedProcess[str]:
        stdout_path.write_text("tool output\n", encoding="utf-8")
        return subprocess.CompletedProcess(command, 1 if command[0] == "pyright" else 0)

    exit_code = quality_report.run_quality_report(
        project_root=tmp_path,
        runner=fake_runner,
    )

    assert exit_code == 1
    output = capsys.readouterr().out
    assert "quality report failed" in output
    assert "pyright" in output
    assert (
        "reports\\quality\\pyright.txt" in output
        or "reports/quality/pyright.txt" in output
    )


def test_run_quality_report_does_not_fail_for_report_only_checks(
    tmp_path, capsys
) -> None:
    def fake_runner(
        command: list[str], stdout_path: Path
    ) -> subprocess.CompletedProcess[str]:
        stdout_path.write_text("tool output\n", encoding="utf-8")
        return subprocess.CompletedProcess(command, 1 if command[0] == "vulture" else 0)

    exit_code = quality_report.run_quality_report(
        project_root=tmp_path,
        runner=fake_runner,
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "WARN vulture" in output
    assert "quality report passed" in output
