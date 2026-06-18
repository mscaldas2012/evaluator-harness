from __future__ import annotations

import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

Runner = Callable[[list[str], Path], subprocess.CompletedProcess[str]]


@dataclass(frozen=True)
class QualityCheck:
    name: str
    command: list[str]
    output_file: str
    required: bool = True


QUALITY_CHECKS = (
    QualityCheck(
        name="ruff check",
        command=["ruff", "check", "."],
        output_file="ruff-check.txt",
    ),
    QualityCheck(
        name="ruff format",
        command=["ruff", "format", "--check", "."],
        output_file="ruff-format.txt",
    ),
    QualityCheck(
        name="pyright",
        command=["pyright"],
        output_file="pyright.txt",
    ),
    QualityCheck(
        name="architecture boundaries",
        command=["lint-imports", "--config", ".importlinter"],
        output_file="import-linter.txt",
    ),
    QualityCheck(
        name="radon complexity",
        command=["radon", "cc", "src", "scripts", "-s", "-a"],
        output_file="radon-complexity.txt",
    ),
    QualityCheck(
        name="radon maintainability",
        command=["radon", "mi", "src", "scripts", "-s"],
        output_file="radon-maintainability.txt",
    ),
    QualityCheck(
        name="pytest",
        command=[
            "pytest",
            "-m",
            "not live",
            "--junitxml",
            "reports/quality/pytest.xml",
            "--cov-report",
            "xml:reports/quality/coverage.xml",
            "--cov-report",
            "html:reports/quality/htmlcov",
        ],
        output_file="pytest.txt",
    ),
    QualityCheck(
        name="coverage summary",
        command=["coverage", "report", "--format=markdown"],
        output_file="coverage-summary.md",
    ),
    QualityCheck(
        name="vulture",
        command=["vulture", "src", "tests", "scripts", "--min-confidence", "80"],
        output_file="vulture.txt",
        required=False,
    ),
)


def run_command(
    command: list[str], stdout_path: Path
) -> subprocess.CompletedProcess[str]:
    with stdout_path.open("w", encoding="utf-8") as output:
        return subprocess.run(
            command,
            check=False,
            stderr=subprocess.STDOUT,
            stdout=output,
            text=True,
        )


def run_quality_report(project_root: Path, runner: Runner = run_command) -> int:
    reports_dir = project_root / "reports" / "quality"
    reports_dir.mkdir(parents=True, exist_ok=True)

    failures: list[tuple[QualityCheck, Path]] = []
    for check in QUALITY_CHECKS:
        output_path = reports_dir / check.output_file
        result = runner(check.command, output_path)
        status = (
            "PASS"
            if result.returncode == 0
            else "FAIL"
            if check.required
            else "WARN"
        )
        print(f"{status} {check.name}: {output_path.relative_to(project_root)}")
        if result.returncode != 0 and check.required:
            failures.append((check, output_path))

    if failures:
        print("\nquality report failed")
        for check, output_path in failures:
            print(f"- {check.name}: see {output_path.relative_to(project_root)}")
        return 1

    print("\nquality report passed")
    print(f"reports written to {reports_dir.relative_to(project_root)}")
    return 0


def main() -> int:
    return run_quality_report(project_root=Path.cwd())


if __name__ == "__main__":
    sys.exit(main())
